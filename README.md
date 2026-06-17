# Oral Pathology Assessment Platform

An AI-powered educational platform for clinical dental training. Students work through oral pathology cases in a simulated clinical environment; a hybrid AI pipeline interprets their actions, scores them against clinical rules, and provides feedback — all in Turkish.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Next.js 14 / React 18                        │
│          (Case viewer · Radiograph viewer · Analytics UI)        │
└───────────────────────────┬─────────────────────────────────────┘
                            │ REST (JSON)
┌───────────────────────────▼─────────────────────────────────────┐
│                     FastAPI Gateway                              │
│                                                                  │
│  /chat ──► DentalEducationAgent                                  │
│              ├─ Gemini 2.5 Flash Lite  (action interpreter)      │
│              ├─ AssessmentEngine       (rule-based scorer)       │
│              └─ MedGemmaService        (silent validator)        │
│                                                                  │
│  /analytics ──► AnalyticsEngine  (XGBoost · IRT · pandas)       │
│  /quiz      ──► QuizRouter                                       │
│  /cases     ──► CaseRouter                                       │
│  /auth      ──► JWT (student / instructor / admin roles)         │
└──────────────────────────┬──────────────────────────────────────┘
                           │ SQLAlchemy / psycopg3
                  ┌────────▼────────┐
                  │  PostgreSQL 16   │
                  └─────────────────┘
```

---

## AI Pipeline — Silent Evaluator Architecture

Every student message goes through a three-stage hybrid pipeline (`app/agent.py`):

### Stage 1 — Action Interpretation (Gemini)

`DentalEducationAgent.interpret_action()` sends the sanitized student input to **Gemini 2.5 Flash Lite** with a structured system prompt. The model classifies the input as `CHAT` or `ACTION`, maps it to a normalized action key (e.g., `check_allergies_meds`), and returns Turkish explanatory feedback — all as strict JSON.

The allowed action key set is fixed at prompt time (26 keys). Any key not on the list is coerced to `unspecified_action` by `_normalize_interpretation_payload()`, which also validates intent type, clinical category, and priority enumerations.

Prompt injection is detected before the LLM call (`llm_safety.detect_prompt_injection`) using five regex-pattern families (instruction override, role override, exfiltration, jailbreak, system-role injection). Detected signals are logged and attached to the response but do not block the pipeline.

### Stage 2 — Rule-Based Scoring (AssessmentEngine)

`AssessmentEngine.evaluate_action()` loads per-case scoring rules from PostgreSQL (`CaseDefinition.rules_json`). Each rule specifies an action key, expected outcome, score delta, safety category, and optional state updates. A JSON file fallback is available behind `DENTAI_ALLOW_RULE_JSON_FALLBACK=true`.

Safety-critical rules (`is_critical_safety_rule=true`) surface `contraindication_violation`, `wrong_medication`, `premature_treatment`, or `missed_critical_step` flags to the next stage.

### Stage 3 — Silent Validation (MedGemma)

`MedGemmaService` wraps `betuldanismaz/dentai-gemma2-9b-oral-pathology` — a Gemma 2 9B model fine-tuned on 50 oral pathology assessment examples — deployed on Hugging Face Inference API.

The validator runs **after** feedback is already composed for the student. It never blocks the conversational flow. The service retries twice with 0.5 s exponential backoff and enforces a 10-second hard timeout; on any failure it emits a fail-closed result (`MedGemmaService.build_fail_closed_result()`).

Deterministic safety flags from Stage 2 are merged with MedGemma's probabilistic flags before the audit record is persisted.

---

## Fine-Tuning

`finetuning/gemma2_finetune.ipynb` — SFT on Gemma 2 9B using the Hugging Face `trl` + `peft` stack (LoRA).

**Dataset** (`finetuning/finetune_dataset.jsonl`): 50 multi-turn examples across 5 oral pathology cases, labelled with priority (`high` / `medium` / `low`) and safety flags (`premature_treatment`, `wrong_medication`, `missed_critical_safety_check`). Each example pairs a Turkish-language patient scenario with a JSON assessment ground truth.

The fine-tuned model ID on the Hub: `betuldanismaz/dentai-gemma2-9b-oral-pathology`.

---

## Adaptive Learning Engine

**IRT (Item Response Theory)** — `py-irt` (PyTorch backend) fits 2PL/3PL models over student response histories to estimate latent ability θ and per-case difficulty, discrimination, and guessing parameters. Ability estimates are stored as time-series snapshots in `ability_estimates` for longitudinal regression detection.

**XGBoost** — trained on engagement signals, error distributions, and session pacing to predict at-risk students. SHAP values expose feature contributions for instructor dashboards.

**Analytics Engine** (`app/analytics_engine.py`) — maps raw action keys to five competency categories (diagnosis, anamnesis, examination, diagnostic\_tests, treatment), computes per-category averages with pandas, and surfaces the weakest category with a Turkish recommendation string.

---

## Case Library

200+ clinical scenarios with **progressive information disclosure**: history → examination findings → radiographic evidence is released incrementally. Students commit to a working diagnosis before additional data unlocks.

| Category | Examples |
|---|---|
| Oral Lichen Planus | Wickham striae, reticular/erosive variants |
| Primary Herpetic Gingivostomatitis | Vesicle clusters, systemic fever |
| Behçet Disease | Pathergy test, recurrent aphthae |
| Secondary Syphilis | Mucous patches, serology |
| Mucous Membrane Pemphigoid | Nikolsky test, DIF biopsy |
| Periapical Pathology | Apical periodontitis, granulomas |
| Periodontal Disease | Chronic/aggressive periodontitis |

---

## Backend API

| Router | Key Endpoints |
|---|---|
| `auth` | `POST /auth/login`, `POST /auth/register` |
| `chat` | `POST /chat` — main pipeline entry point |
| `cases` | `GET /cases`, `GET /cases/{id}`, case publish/archive |
| `analytics` | `GET /analytics/student/{id}`, weakness report |
| `quiz` | `POST /quiz/submit`, `GET /quiz/results` |
| `instructor` | `GET /instructor/cohort`, `GET /instructor/student/{id}` |
| `admin` | Case CRUD, rule management, user management |
| `recommendations` | Spotlight recommendations, snapshot history |

JWT-based RBAC: tokens carry role claims (`student` / `instructor` / `admin`). `deps.py` provides `get_current_user` and role-guard dependencies injected at router level.

---

## Data Model

```
students          ──< sessions ──< responses
cases             ──< case_media
cases             ──< case_definitions (rules_json, is_archived)
students          ──< ability_estimates (time-series θ snapshots)
students          ──< trajectory_predictions
sessions          ──< recommendation_snapshots (is_spotlight)
quiz_questions    ──< quiz_attempts
```

Migrations managed with Alembic. Schema history spans 8 versioned migrations from initial schema through quiz models, rule JSON columns, and recommendation snapshots.

---

## LLM Safety Layer (`app/services/llm_safety.py`)

- `sanitize_student_text` — strips control characters, normalises whitespace, truncates at 2 000 chars
- `sanitize_model_feedback` — truncates model output at 500 chars, removes blocked tokens (`api key`, `token`, `password`, `system prompt`, etc.)
- `build_untrusted_student_payload` — wraps student text in a labelled envelope so the model treats it as data, not instructions
- `detect_prompt_injection` — scores input against five pattern families; returns `detected: bool`, `risk_level`, and `signals` list

---

## Technology Stack

| Layer | Technology |
|---|---|
| Primary LLM | Gemini 2.5 Flash Lite (`google-generativeai`) |
| Clinical Validator | Gemma 2 9B fine-tuned (`betuldanismaz/dentai-gemma2-9b-oral-pathology`) via Hugging Face Inference API |
| Fine-tuning | `trl` · `peft` (LoRA) · Gemma 2 9B base |
| Rule Engine | PostgreSQL-backed JSON rules + `AssessmentEngine` |
| Adaptive Learning | `py-irt` (IRT 2PL/3PL) · `xgboost` · `shap` · `scikit-learn` |
| Backend | FastAPI · Python 3.11 · Uvicorn |
| Database | PostgreSQL 16 · SQLAlchemy 2 · psycopg3 · Alembic |
| Frontend | Next.js 14 · React 18 · TypeScript · Tailwind CSS |
| Auth | JWT (`python-jose`) · bcrypt (`passlib`) |
| Deployment | Docker Compose (`docker-compose.yml` + override + prod variants) |
