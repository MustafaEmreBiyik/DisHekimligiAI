# DentAI — Sprint 13: Multimodal Clinical Evidence + Adaptive Engine Build

> **Theme:** Wire the existing clinical images into a multimodal AI pipeline, and build the IRT/XGBoost services that Sprint 11 designed but did not implement.
> **Status:** Plan (2026-06-17)
> **Duration:** 3 weeks (15 working days)
> **Prerequisites completed:** Sprint 11 T01 schema (IRTParameters, MasteryState, RecommendationModelVersion, RecommendationFeatureLog) — Alembic head `o0j4m2n59i76`
> **Pulls from Sprint 11 plan:** T02 (feature store), T03 (IRT calibration), T04 (BKT service), T05 (XGB trainer), T06 (engine v2), T07 (evaluator)

---

## 0. Situation Summary

### What exists today

| Area | State |
|---|---|
| Case images | 6 JPEGs in `assets/images/`; referenced by `gorsel_id` / `media` fields in `case_scenarios.json` but never passed to any AI model |
| Gemini agent | Text-only; `DentalEducationAgent.interpret_action()` sends only sanitized student text |
| MedGemma validator | Text-only; validates action text against rules, no image awareness |
| IRT / BKT / XGBoost | Schema tables exist, zero services implemented; operating on synthetic bootstrap (Sprint 11 data readiness gate: zero real responses) |
| Recommendation engine | v1 rule-based only (`ALGORITHM_VERSION = "v1_competency_based"`) |
| Frontend case viewer | No image display component; `CaseHeader.tsx` exists but no image panel |

### What this sprint delivers

**Track M — Multimodal:** Images flow through the entire AI pipeline. Students see clinical photos. Gemini interprets actions with visual context. The silent validator evaluates whether a student's finding matches what is visible in the image. Visual interactions generate new behavioral signals.

**Track A — Adaptive Engine:** The IRT, BKT, and XGBoost services from the Sprint 11 plan are actually built and wired. They operate on synthetic data until real response volume accumulates, but the infrastructure is live and begins collecting real signals from day 1 of this sprint.

**Integration seam:** Visual complexity of case images becomes an IRT case-difficulty prior. Student image interaction patterns (dwell time, whether they unlocked the image) become XGBoost features. Correct identification of a visual finding becomes a BKT observation.

---

## 1. Track M — Multimodal Clinical Evidence

### S13-M1 — Multimodal Chat Endpoint (2 days)

**Problem:** `POST /api/chat` currently accepts only text. Gemini 2.5 Flash Lite natively supports multi-part content (text + image bytes). Nothing in the pipeline uses this.

**Changes:**

`app/api/routers/chat.py`
- Accept `multipart/form-data` in addition to `application/json`. New optional field: `image` (binary, max 5 MB, MIME types: `image/jpeg`, `image/png`, `image/webp`).
- Validate MIME type and size server-side before touching the AI pipeline. Reject with 415 or 413 as appropriate.
- Pass the raw bytes and MIME type down to `DentalEducationAgent.process_student_input()` as `image_bytes: bytes | None` and `image_mime: str | None`.
- Store a flag `has_image: bool` in `ChatLog.metadata_json` for analytics.

`app/agent.py` — `DentalEducationAgent.interpret_action()`
```python
import google.generativeai as genai

def interpret_action(
    self,
    action: str,
    state: dict,
    image_bytes: bytes | None = None,
    image_mime: str = "image/jpeg",
) -> dict:
    ...
    parts: list = [genai.types.Part.from_text(user_prompt)]
    if image_bytes:
        parts.append(genai.types.Part.from_bytes(data=image_bytes, mime_type=image_mime))
    response = self.model.generate_content(parts)
```

Update `DENTAL_EDUCATOR_PROMPT` with a new section:

```
MULTIMODAL CLINICAL EVIDENCE:
If a clinical image is attached:
- Describe observable findings using clinical terminology before interpreting the student's action.
- Your "explanatory_feedback" MUST acknowledge the visual findings relevant to the student's action.
- If the student's described action contradicts what is visible (e.g., claims to see a lesion not present in the image), flag it in "safety_concerns".
- Add a field "visual_findings_observed": ["string"] to your JSON output — list what you see in the image.
```

Extend `_normalize_interpretation_payload()` to extract `visual_findings_observed` (list of strings, max 10, each ≤ 120 chars).

**Acceptance criteria:**
- `POST /api/chat` with `multipart/form-data`, `message=<text>`, `image=<jpeg>` returns 200 with `visual_findings_observed` populated.
- `POST /api/chat` with a 6 MB image returns 413 before calling any AI model.
- Existing `application/json` path unchanged (no regression).
- `has_image` flag appears in `ChatLog.metadata_json`.

**Files:**
- `app/api/routers/chat.py`
- `app/agent.py`
- `tests/api/test_chat_multimodal.py` — mock the Gemini response; assert multipart parsing, image size validation, `visual_findings_observed` extraction.

---

### S13-M2 — Visual Finding Reveal Mechanic (1.5 days)

**Problem:** Cases have `gizli_bulgular` (hidden findings), each with an optional `media` path and `gorsel_id`. Today these images are never shown to the student. The design intent — visible only after the student performs the relevant examination action — is unimplemented.

**Backend changes:**

`app/scenario_manager.py`
- Track `revealed_media: list[str]` alongside the existing `revealed_findings` in session state.
- When `update_state()` is called with a `state_updates` dict that includes `revealed_findings`, cross-reference `gizli_bulgular` in the case JSON: if a newly-revealed finding has a `media` field, add its path to `revealed_media`.

`app/api/routers/chat.py` — add `revealed_media` to the response payload alongside `updated_state`.

`app/api/routers/cases.py`
- `GET /api/cases/{case_id}/media/{filename}` — serve static case images from `assets/images/`. Require a valid JWT; no unauthenticated access. Stream with `FileResponse`. 404 if the file does not exist in the allow-listed directory (path traversal guard: resolve path and assert it is under `assets/images/`).

**Acceptance criteria:**
- After a student performs `perform_oral_exam` on `olp_001`, the response contains `revealed_media: ["assets/images/olp_clinical.jpg"]`.
- `GET /api/cases/olp_001/media/olp_clinical.jpg` returns the JPEG with `Content-Type: image/jpeg`.
- Requesting `../../../.env` through the media endpoint returns 400.
- A fresh session on a case with no performed exams has `revealed_media: []`.

**Files:**
- `app/scenario_manager.py`
- `app/api/routers/cases.py`
- `tests/api/test_case_media.py`

---

### S13-M3 — Visual Silent Validator (2 days)

**Problem:** `MedGemmaService.validate_clinical_action()` is text-only and calls the fine-tuned `betuldanismaz/dentai-gemma2-9b-oral-pathology` (text-only SFT model). It cannot evaluate whether a student correctly identified a visual finding.

**Approach:** Add a second validation path that uses **Gemini 2.5 Flash** (not Lite) as a multimodal clinical evaluator when an image is present. The fine-tuned MedGemma remains the text-only validator; Gemini takes the visual path. Both validators contribute to the merged `silent_evaluation` result in `DentalEducationAgent._silent_evaluation()`.

`app/services/visual_validator.py` — new service:

```python
class VisualClinicalValidator:
    """
    Multimodal silent validator using Gemini 2.5 Flash.
    Evaluates whether the student's described finding matches
    what is observable in the attached clinical image.
    Runs only when image_bytes is not None.
    """
    MODEL = "models/gemini-2.5-flash"
    TIMEOUT_SECONDS = 15

    def validate(
        self,
        student_text: str,
        visual_findings_observed: list[str],
        image_bytes: bytes,
        image_mime: str,
        rules: dict,
        context_summary: str,
    ) -> dict:
        ...
```

Output schema (same as `MedGemmaService` to allow identical merge logic):
```json
{
  "safety_flags": ["string"],
  "missing_critical_steps": ["string"],
  "clinical_accuracy": "high" | "medium" | "low" | null,
  "faculty_notes": "string",
  "image_finding_match": true | false | null
}
```

`image_finding_match` is the new field: `true` if the student's described visual finding is consistent with the image, `false` if they describe something that is not visible.

`app/agent.py` — `DentalEducationAgent._silent_evaluation()`:
- If `image_bytes` is present, run `VisualClinicalValidator.validate()` in addition to (or instead of) MedGemma.
- Merge flags from both validators using the existing merge logic.
- Add `image_finding_match` to the outer `silent_evaluation` dict returned to the caller.
- If `image_finding_match = false`, add `"visual_finding_mismatch"` to `safety_flags`.

`ChatLog.metadata_json` — store `image_finding_match` for analytics.

**Acceptance criteria:**
- When an image is attached and a student describes a correct finding (e.g., "Wickham striae görüyorum"), `image_finding_match: true`.
- When student describes an impossible finding (e.g., "kavite görüyorum" on an OLP case), `image_finding_match: false` and `safety_flags` contains `"visual_finding_mismatch"`.
- When no image is attached, `image_finding_match: null` and `VisualClinicalValidator` is never called.
- Fail-closed: if Gemini call fails, `image_finding_match: null` (not `false`) — absence of evidence is not evidence of absence.

**Files:**
- `app/services/visual_validator.py`
- `app/agent.py`
- `tests/unit/test_visual_validator.py`

---

### S13-M4 — Frontend: Clinical Image Viewer ✅ (2026-06-17)

**Problem:** Students see no images. The case viewer needs a clinical photo panel that reveals images progressively as the student unlocks findings.

`frontend/components/ClinicalImagePanel.tsx`
- Props: `revealedMedia: string[]`, `caseId: string`
- For each item in `revealedMedia`, render an `<img>` loaded from `GET /api/cases/{caseId}/media/{filename}` with the JWT in the `Authorization` header (use a fetch-then-blob pattern or a signed URL approach — fetch approach is simpler given current auth setup).
- Initial state (empty `revealedMedia`): render a placeholder silhouette with "Oral muayeneyi gerçekleştirin" hint.
- Image interaction: pan/zoom using CSS `transform: scale()` on pinch or scroll wheel; double-click resets.
- Unlocked image enters with a CSS fade-in (250 ms) and a brief "Yeni bulgu açıldı!" toast.

`frontend/components/ChatMessage.tsx`
- Add image attachment button in the chat input. On click, open `<input type="file" accept="image/jpeg,image/png,image/webp">`. Preview the selected image as a thumbnail before sending.
- On send, use `FormData` instead of JSON. If no image selected, fall back to JSON (no regression).

`frontend/app/stats/page.tsx` (or wherever the session view is)
- Display `image_finding_match` badge per action in the history table: ✓ visual match / ✗ visual mismatch / — (no image).

**Acceptance criteria:**
- On a fresh OLP case, the image panel shows a placeholder. After typing "Oral mukozayı muayene ediyorum", the OLP image appears with fade-in.
- Students can zoom in to see Wickham striae detail.
- Image upload button in chat sends a multipart request; `visual_findings_observed` appears in the response.
- `tsc --noEmit` and `eslint --max-warnings 0` clean.

**Files:**
- `frontend/components/ClinicalImagePanel.tsx`
- `frontend/components/ChatMessage.tsx` (modified)
- `frontend/app/stats/page.tsx` (minor)

---

### S13-M5 — Visual Complexity Feature for IRT/XGBoost (1 day)

**Problem:** IRT case-difficulty priors and XGBoost case features currently use `CaseDefinition.difficulty` (a 3-level enum set by instructor). Visual cases should have an objective visual complexity score as an additional prior.

`scripts/compute_visual_complexity.py` — offline script:
- For each case image in `assets/images/`, call Gemini with the prompt: `"Rate the visual diagnostic complexity of this clinical image on a 0.0–1.0 scale. Consider: visibility of lesion margins, color contrast, image quality, how many differential diagnoses a student would need to consider. Return JSON: {\"complexity\": float, \"rationale\": str}"`.
- Write results to `data/visual_complexity.json`: `{case_id: {gorsel_id, complexity, rationale, computed_at}}`.

`db/database.py` — add column to `CaseDefinition`:
```python
visual_complexity_score = Column(Float, nullable=True)  # 0.0–1.0, None = no image
```

Alembic migration: `s13m5_add_visual_complexity_to_case_definitions.py`.

`scripts/seed_visual_complexity.py` — reads `data/visual_complexity.json` and updates `CaseDefinition.visual_complexity_score`.

The feature store (S13-A1) then includes `visual_complexity_score` as a case feature, overriding `case_difficulty_ordinal` as the IRT `b` prior when non-null.

**Acceptance criteria:**
- `python scripts/compute_visual_complexity.py` writes scores for all 6 existing images.
- `CaseDefinition.visual_complexity_score` is populated for the 6 imaged cases.
- Running the feature store (S13-A1) returns `visual_complexity_score` in the case feature vector, not null.

**Files:**
- `scripts/compute_visual_complexity.py`
- `scripts/seed_visual_complexity.py`
- `data/visual_complexity.json`
- `db/database.py` (column addition)
- `alembic/versions/<rev>_s13m5_add_visual_complexity.py`

---

## 2. Track A — Adaptive Engine Build

> All Sprint 11 tasks were designed but not implemented. This track builds them. The execution follows the Sprint 11 spec closely; this section records decisions specific to Sprint 13 context.

### S13-A1 — Feature Store (2 days)

**File:** `app/services/feature_store.py`

Implements the Sprint 11 T02 spec. Adaptations for Sprint 13:

1. **Image interaction features (new, not in Sprint 11 plan):**
   - `image_unlock_rate`: fraction of sessions where student unlocked at least one case image (from `ChatLog.metadata_json.has_image`).
   - `image_finding_match_rate_30d`: fraction of image-present actions in last 30 days where `image_finding_match = true`.
   These are added to the user feature group (2 additional features, total 39).

2. **Visual complexity as case feature:**
   - `visual_complexity_score` replaces `case_difficulty_ordinal` as the IRT b prior when non-null (S13-M5 output). When null (no image), fall back to `case_difficulty_ordinal / 2.0` to stay in [0, 1].

3. **Synthetic imputation for cold-start:**
   - `cold_start_flag = 1.0` for users with < 3 sessions.
   - Image features impute to dataset mean when no image interactions exist.

Entry points:
```python
def build_user_features(db, user_id, asof=None) -> dict[str, float]: ...
def build_case_features(db, case_id) -> dict[str, float]: ...
def build_candidate_row(db, user_id, case_id, asof=None) -> dict[str, float]: ...
def materialise_training_frame(db, since, until) -> pd.DataFrame: ...
```

`asof`-correctness is mandatory: features for a training row at `asof_ts` must use only events strictly before `asof_ts`. This is tested explicitly.

**Acceptance criteria:**
- `build_candidate_row` returns 39 features for any valid (user, case) pair with no NaNs (imputed, not dropped).
- `materialise_training_frame` for a date window completes in < 30 s on the dev SQLite.
- Cold-start user produces `cold_start_flag = 1.0` and all behavioral features at documented defaults.
- A unit test constructs a row at `asof=T` and asserts no feature depends on an event at `T+1`.

**Files:**
- `app/services/feature_store.py`
- `tests/unit/test_feature_store.py`

---

### S13-A2 — BKT Mastery Service + Live Wiring (2 days) ✅ (2026-06-17)

**File:** `app/services/bkt_service.py`

Implements Sprint 11 T04. Three additions for Sprint 13:

1. **Visual finding as BKT observation:** When `image_finding_match = true` for an `ACTION`-typed turn, call `bkt_service.observe(db, user_id, topic_id, was_correct=True)` where `topic_id` is the competency tag from the assessment result (e.g., `"oral_pathology"`). When `image_finding_match = false`, call with `was_correct=False`. This is richer signal than text-only assessment — a student who correctly describes a visual finding has a stronger mastery claim.

2. **BKT update in chat.py wiring:**
   ```python
   # In chat.py, after agent.process_student_input() returns:
   if result["llm_interpretation"]["intent_type"] == "ACTION":
       competency_tags = result["assessment"].get("competency_tags", [])
       was_correct = result["assessment"].get("score_change", 0) > 0
       for tag in competency_tags:
           bkt_service.observe(db, student_id, tag, was_correct)
   ```

3. **Visual mismatch as negative observation:** Add `was_correct=False` observation for `"visual_examination"` topic when `image_finding_match = false`.

Topic canonicalisation: `_canonicalise_topic_id(tag: str) -> str` — lowercase, strip, NFC normalise. All writes and reads go through this.

**Acceptance criteria (from Sprint 11 T04 spec):**
- 10 consecutive correct answers on one topic → `mastery_prob > 0.85`.
- 5 alternating → `0.35 ≤ mastery_prob ≤ 0.65`.
- Replay idempotency: bit-for-bit identical posterior after full history replay.
- BKT hook in chat.py adds < 20 ms to request latency.
- Topic canonicalisation: `"Oral_Pathology"`, `" oral_pathology "`, `"oral_pathology"` all map to the same `MasteryState` row.

**Files:**
- `app/services/bkt_service.py`
- `app/api/routers/chat.py` (hook)
- `app/api/routers/quiz.py` (hook on graded answers)
- `app/jobs/refresh_bkt_states.py`
- `tests/unit/test_bkt_service.py`

---

### S13-A3 — IRT 2PL Calibration on Synthetic Bootstrap (1.5 days)

**File:** `app/services/irt_calibration.py`

Implements Sprint 11 T03 on the synthetic bootstrap branch (all data is `is_synthetic=True` until real response volume crosses the gate threshold).

**Synthetic response generation:**
```python
def _generate_synthetic_responses(
    questions: list[Question],
    n_simulated_students: int = 300,
    seed: int = 42,
) -> pd.DataFrame:
    """
    2PL simulator. Initial b prior: difficulty_ordinal → {beginner:-1.0, intermediate:0.0, advanced:1.0}.
    a ~ LogNormal(0, 0.25) clipped to [0.5, 2.0].
    Student abilities ~ N(0, 1).
    P(correct) = 1 / (1 + exp(-a*(θ - b))).
    """
```

Each question gets an `IRTParameters` row with `is_synthetic=True` and a shared `calibration_run_id`.

**CLI:** `python -m app.jobs.recalibrate_irt --dry-run` prints recovered (a, b) per question without writing. Live run upserts within a transaction.

**Transition gate check:** `recalibrate_irt` checks `IRTParameters.is_synthetic` at each run. When `fraction_ready >= 0.20` (per the data readiness probe script), it automatically switches to real-data mode and logs the transition.

**Acceptance criteria:**
- Dry-run produces a Markdown report of every question's (a, b) without DB writes.
- Synthetic recovery test: known (a, b) within `|Δa| < 0.3, |Δb| < 0.3` on simulated data.
- `calibration_run_id` is consistent across all rows of a single run.
- `is_synthetic=True` on all rows when real data is below gate.

**Files:**
- `app/services/irt_calibration.py`
- `app/jobs/recalibrate_irt.py`
- `tests/unit/test_irt_calibration.py` (marked `@pytest.mark.slow`)

---

### S13-A4 — XGBoost Ranker Trainer (2 days)

**File:** `app/services/recommendation_trainer.py`

Implements Sprint 11 T05 with one Sprint 13 addition: the feature set includes the 2 new image interaction features from S13-A1 (39 total features, not 37).

**Training on synthetic data:**
- `materialise_training_frame` with `since=None` returns whatever sessions exist (real or synthetic-seeded).
- Minimum training set gate: if `len(training_frame) < 50`, skip training and log `"Insufficient training data — ranker training deferred"`. This prevents a garbage model from reaching production on day 1.
- When sufficient data exists, train `XGBRanker(objective="rank:pairwise", n_estimators=500, max_depth=6, learning_rate=0.05, early_stopping_rounds=30)` with chronological train/val split (last 21 days → val).
- Persist bundle to `models/recommendation/v2_hybrid_xgb_irt_bkt/`: `model.json`, `scaler.joblib`, `feature_schema.json`.
- Insert `RecommendationModelVersion` row with `is_active=False`.

**Label definition:** `was_completed_within_14d_with_score_gte_70`. Documented in `docs/architecture/RECOMMENDATION_LABELS.md`.

**Feature importance:** Top-10 by gain logged to `models/recommendation/.../feature_importance.json`.

**Acceptance criteria:**
- With seed=42 and same data, two training runs produce identical `ndcg_at_5`.
- Model bundle ≤ 50 MB.
- Feature schema in bundle matches the 39-column list from `feature_store.py`.
- If training data < 50 rows, job exits 0 with a warning (no crash, no garbage model).

**Files:**
- `app/services/recommendation_trainer.py`
- `app/jobs/retrain_ranker.py`
- `app/jobs/promote_recommendation_model.py`
- `docs/architecture/RECOMMENDATION_LABELS.md`
- `tests/unit/test_recommendation_trainer.py`

---

### S13-A5 — Recommendation Engine v2 + Evaluation (2 days)

**File:** `app/services/recommendation_engine_v2.py`

Implements Sprint 11 T06 + T07.

**Hybrid logic:** (from Sprint 11 spec, unchanged)
- If active model is missing → silent fallback to v1 with `algorithm_version = "v1_competency_based"`.
- If cold-start (< 3 sessions) → rule-based ordering, `reason_code = "cold_start_v2"`, ε-greedy exploration at 10%.
- Normal path: XGB scoring + SHAP top-3 per item.

**Visual recommendation reason (new for Sprint 13):**
- If a recommended case has `visual_complexity_score` and the student's `image_finding_match_rate_30d < 0.5`, add a reason code `"visual_skill_gap"` and a Turkish reason text: `"Bu vakada görsel bulgu yorumlama becerisini geliştirmen önerilir."`.
- This makes multimodal performance visible in the recommendation reason.

**Evaluation harness (`app/services/recommendation_evaluator.py`):**
- Implement Sprint 11 T07. On a fresh system with no historical recommendation outcomes, the evaluator correctly reports "insufficient outcome data — promote gate not met" and exits cleanly.
- The evaluation CLI is the daily gate check before any model promotion.

**API changes (`app/api/routers/recommendations.py`):**
- Add `?algorithm=v1_competency_based|v2_hybrid_xgb_irt_bkt|auto` query param.
- Response adds optional `top_features: list[dict]` and `model_version: str`.
- Backward compatible: existing clients without the param get `auto` behavior.

**Acceptance criteria:**
- `GET /api/recommendations/me?algorithm=v2_hybrid_xgb_irt_bkt` returns 200 with `model_version` populated (or graceful v1 fallback with log warning if no active model).
- `GET /api/recommendations/me?algorithm=v1_competency_based` always returns v1.
- Inference p95 < 150 ms for ≤ 30 candidate cases.
- `RecommendationFeatureLog` row written transactionally with `RecommendationSnapshot`.
- Evaluator CLI exits 0 on fresh system with "insufficient data" message, not an exception.
- Visual reason code `"visual_skill_gap"` appears when image match rate < 50%.

**Files:**
- `app/services/recommendation_engine_v2.py`
- `app/services/recommendation_explainer.py`
- `app/services/recommendation_evaluator.py`
- `app/api/routers/recommendations.py`
- `app/jobs/evaluate_recommendations.py`
- `tests/integration/test_recommendation_v2_endpoint.py`

---

## 3. Frontend: Recommendation Explainability Panel

**File:** `frontend/components/RecommendationExplainPanel.tsx`

Implements Sprint 11 T08. Sprint 13 addition: show the `"visual_skill_gap"` reason code with a camera icon and distinct styling.

Layout:
1. Top-5 case cards with title, difficulty pill, estimated duration.
2. Expandable "Bu vaka neden önerildi?" panel — top-3 SHAP features with direction arrows and magnitude bars. Feature names translated via `frontend/lib/featureLabels.ts`.
3. If `visual_skill_gap` reason present: camera icon + `"Görsel bulgu yorumlama odağı"` badge.
4. Cold-start banner.
5. Algorithm version footer.

`frontend/lib/featureLabels.ts`:
```typescript
export const FEATURE_LABELS: Record<string, string> = {
  mastery_gap_on_case_topics: "Eksik yetkinlik alanları",
  image_finding_match_rate_30d: "Görsel bulgu doğruluk oranı",
  days_since_last_session: "Son çalışmadan geçen süre",
  n_topics_below_60pct: "Düşük ustalık seviyeli konular",
  visual_complexity_score: "Görsel tanı zorluğu",
  // ... remaining 34 features
};
```

**Acceptance criteria:**
- Page renders in dev with cold-start banner on a fresh account.
- SHAP bars render for a user with an active model.
- `visual_skill_gap` badge appears and is styled distinctly.
- `tsc --noEmit` and `eslint --max-warnings 0` clean.

---

## 4. Dependency Graph

```
S13-M5 (visual complexity DB column)
    │
    ▼
S13-M1 (multimodal chat endpoint) ──► S13-M3 (visual validator)
    │                                        │
    │                                        ▼
    ├───────────────────────────────► S13-A1 (feature store) ──► S13-A4 (XGB trainer)
    │                                        │                         │
S13-M2 (finding reveal mechanic)            │                         ▼
    │                                S13-A2 (BKT service)    S13-A5 (rec engine v2)
    │                                        │                         │
    ▼                                        ▼                         ▼
S13-M4 (frontend image viewer) ──────────────────────────► Frontend rec panel
```

**Critical path (minimum to ship):** M1 → M2 → M4 → A1 → A2 → A4 → A5 (≈ 12 days)
**Parallel-safe:** M3 can run after M1 independently of M2. M5 can run any time. A3 (IRT) is independent of M-track beyond M5.

---

## 5. Task Schedule (15 days, solo)

| Day | Tasks | Output |
|-----|-------|--------|
| 1–2 | S13-M1 (multimodal endpoint) | Chat accepts images; Gemini returns `visual_findings_observed` |
| 3 | S13-M2 (finding reveal) + S13-M5 (visual complexity column + script) | Images served; DB column seeded |
| 4–5 | S13-M3 (visual validator) | `image_finding_match` in silent evaluation |
| 6–7 | S13-M4 (frontend image viewer) | Students see clinical images; can attach photos |
| 8–9 | S13-A1 (feature store) | 39-feature candidate rows; training frame materialises |
| 10–11 | S13-A2 (BKT wiring) | BKT updates on every chat action and quiz answer |
| 12 | S13-A3 (IRT synthetic calibration) | IRTParameters rows with is_synthetic=True |
| 13–14 | S13-A4 + A5 (XGB trainer + rec engine v2) | v2 recommendation endpoint live; SHAP explanations |
| 15 | Frontend rec panel + buffer + smoke test | Full recommendation page with explainability |

---

## 6. New Database Migration

**Migration file:** `alembic/versions/<rev>_s13_visual_and_image_interaction.py`
**Down revision:** `o0j4m2n59i76` (Sprint 11 T01 head)

Changes:
- `CaseDefinition` + `visual_complexity_score REAL` (nullable)
- `ChatLog.metadata_json` already exists as JSON — no schema change, just new keys written at runtime

---

## 7. New API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/chat` | Extended to accept `multipart/form-data` with optional `image` field |
| `GET` | `/api/cases/{case_id}/media/{filename}` | Serve clinical images (JWT required) |
| `GET` | `/api/recommendations/me?algorithm=...` | Extended with algorithm param + SHAP response fields |
| `GET` | `/api/recommendations/me?algorithm=v2_hybrid_xgb_irt_bkt` | v2 hybrid endpoint |

---

## 8. New Dependencies

```
# requirements-api.txt — no new additions
# (google-generativeai already present; FastAPI multipart via python-multipart already present)

# requirements-ml.txt additions (already in file from Sprint 11):
# xgboost>=2.0.0
# shap>=0.45.0
# py-irt>=0.4.0
# joblib>=1.3.0
```

No new Python packages required. All multimodal capability comes from the already-installed `google-generativeai` SDK.

---

## 9. Sprint 13 Definition of Done

| Criterion | Target |
|---|---|
| `POST /api/chat` with image attachment returns `visual_findings_observed` | ✅ |
| Oral exam action unlocks and serves the corresponding case image | ✅ |
| `image_finding_match` flag in `ChatLog.metadata_json` | ✅ |
| `VisualClinicalValidator` fail-closed: failure → `null`, not `false` | ✅ |
| 6 case images have `visual_complexity_score` in DB | ✅ |
| `feature_store.build_candidate_row` returns 39 features, no NaNs | ✅ |
| BKT `observe()` called on every graded action in chat + quiz flows | ✅ |
| 10 correct answers on one topic → `mastery_prob > 0.85` | ✅ |
| IRT synthetic rows written with `is_synthetic=True` | ✅ |
| XGB trainer defers gracefully when < 50 training rows | ✅ |
| `GET /api/recommendations/me?algorithm=v2_hybrid_xgb_irt_bkt` returns 200 with fallback to v1 when no model active | ✅ |
| `visual_skill_gap` reason code surfaces in recommendations when image match rate < 50% | ✅ |
| Frontend image panel: placeholder → image after oral exam | ✅ |
| Frontend image panel: zoom/pan working | ✅ |
| Frontend recommendation page: SHAP top-3 bars + visual_skill_gap badge | ✅ |
| Path traversal guard on `/api/cases/.../media/...` | ✅ |
| Migration applies cleanly on current head `o0j4m2n59i76` | ✅ |
| Backend test count: +25 minimum | ✅ |
| `tsc --noEmit` and `eslint --max-warnings 0` clean | ✅ |

---

## 10. Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Gemini 2.5 Flash image quota / latency on visual validator | Medium | Medium | `VisualClinicalValidator` has 15 s timeout and fail-closed; does not block text path |
| XGB trainer deferred because < 50 training rows | High (early in sprint) | Low | Graceful deferral coded explicitly; recommendation endpoint falls back to v1 cleanly |
| `py-irt` MCMC slow on CI | Medium | Low | `@pytest.mark.slow` gate; separate nightly CI job |
| BKT topic drift from free-text competency tags | Medium | Medium | `_canonicalise_topic_id` applied at all write and read points |
| Image path traversal in media endpoint | High (if unguarded) | Critical | Explicit guard: resolve path and assert prefix is `assets/images/` before `FileResponse` |
| Student uploads a non-clinical photo (adversarial) | Low | Medium | MIME validation + image is wrapped in `build_untrusted_student_payload` framing before Gemini |

---

## 11. What Sprint 14 Should Pick Up

- **Real IRT calibration:** Once `fraction_ready ≥ 0.20` (gate from Sprint 11 readiness report), re-run `recalibrate_irt` on real response data. Remove `is_synthetic=True` rows.
- **A/B test framework (Sprint 11.5-F):** Online comparison of v1 vs v2 recommendations. This is the only honest validation of NDCG lift.
- **BKT prior EM-fitting:** Fit per-topic `P(T)`, `P(S)`, `P(G)` from accumulated observations (deferred from Sprint 11 T04 spec).
- **Add images to remaining cases:** `mmp_clinical.jpg`, `oscc_clinical.jpg`, `pv_clinical.jpg`, `mronj_clinical.jpg` — referenced in `case_scenarios.json` but not yet in `assets/images/`. Procure or generate these.
- **Fine-tune MedGemma for multimodal:** Once a visual Q&A dataset exists from Sprint 13 image interactions, fine-tune `betuldanismaz/dentai-gemma2-9b-oral-pathology` on image+text pairs to replace `VisualClinicalValidator`'s Gemini dependency.

---

*Sprint 13 Plan — 2026-06-17*
