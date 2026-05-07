# S8A PRODUCT BRIEF — Oral Pathology Learning Module
**DENTAI | Sprint 8A: Design-Only**
**Author:** AGENT-1 (Product / Scope / Research Alignment)
**Date:** 2026-05-06
**Status:** DRAFT — Pending Orchestrator Approval
**Sprint 7 Baseline:** 66 passed, 4 deselected

---

## 1. Overview

Sprint 8A is a **design-only sprint** that lays the theoretical and structural foundation for DENTAI's Oral Pathology learning module. No code, no database schemas, no endpoint definitions are produced here. This brief defines what to build, why, and for whom — in terms that support TÜBİTAK feasibility/proof-of-concept framing and Wiley / Journal of Dental Education publication alignment.

The Oral Pathology learning module extends the existing case-based simulation with:
- A structured **theoretical knowledge layer** (topic definitions, key findings, differential lists)
- A **question bank** (MCQ + open-ended)
- A **theory-to-case mapping** requirement ensuring every topic is assessable in simulation
- **Instructor-scored open-ended grading** as the primary human-in-the-loop assessment mechanism

All work in this sprint is scoped to **Oral Pathology only**. No other dental specialty is in scope.

---

## 2. Academic Framing

| Dimension | Position |
|---|---|
| Study type | Feasibility / proof-of-concept |
| Assessment mode | Process-oriented, formative |
| Grading authority | Instructor-primary; AI advisory only |
| AI grading claim | Not authoritative in MVP; future research scope |
| Overclaim prevention | AI grading flagged as "preliminary" until formally validated |
| Specialty scope | Oral Pathology only |

> This framing ensures compatibility with TÜBİTAK project constraints and Wiley/JDE's requirement for cautious, evidence-grounded claims.

---

## 3. Learning Objectives

The module targets **five oral pathology competency areas** aligned with dental education curricular frameworks. All objectives are formative; summative grading authority remains with the instructor.

### 3.1 Competency Area Mapping

| # | Competency Area | Learning Objective | Assessment Method |
|---|---|---|---|
| C1 | **Lesion Recognition** | Student can identify and describe oral mucosal lesions by morphology, distribution, and clinical features | MCQ + Open-ended |
| C2 | **Differential Diagnosis Reasoning** | Student can generate a prioritized differential diagnosis list based on clinical and historical findings | Open-ended + Case |
| C3 | **Diagnostic Test Selection** | Student can select appropriate diagnostic tests (biopsy, DIF, serology, Nikolsky, Paterji) and justify their use | MCQ + Case |
| C4 | **Systemic Correlation** | Student can link oral findings to systemic conditions, medications, and patient history | MCQ + Open-ended + Case |
| C5 | **Clinical Safety Reasoning** | Student recognizes safety-critical steps (pacemaker check, allergy screening, antibiotics contraindication) and avoids harmful actions | Case (deterministic rules) |

### 3.2 Bloom's Taxonomy Alignment

| Level | Target Actions |
|---|---|
| Remember | Recognize lesion names, list typical findings |
| Understand | Explain pathogenesis, link signs to diagnosis |
| Apply | Select correct tests, apply clinical protocols |
| Analyze | Construct differential diagnoses, justify test choices |
| Evaluate | Critique a clinical decision (open-ended grading) |

---

## 4. User Stories

### 4.1 Student — MCQ Practice

```
AS A dental student
I WANT TO answer multiple-choice questions on Oral Pathology topics
SO THAT I can test and reinforce my theoretical knowledge before attempting a simulation case

Scenarios covered:
- Choosing the correct diagnosis from a clinical vignette
- Identifying the appropriate diagnostic test for a condition
- Selecting safe treatment or management options
- Recognizing contraindicated actions for a patient profile

Acceptance:
- Student receives immediate feedback: correct/incorrect (no explanation leakage)
- Score is recorded and visible to instructor
- No correct answer key exposed to student before or after submission
- MCQs are tagged to a competency area and an Oral Pathology topic
```

### 4.2 Student — Open-Ended Answer Submission

```
AS A dental student
I WANT TO write a free-text answer to a clinical reasoning question
SO THAT I can articulate my reasoning, not just select from options

Scenarios covered:
- "Justify your differential diagnosis for this patient"
- "Explain which diagnostic test you would order and why"
- "Describe the safety considerations for this case"

Acceptance:
- Student submits text answer; no AI score is shown to student in MVP
- Answer is saved and visible to instructor for manual grading
- Submission confirmation shown to student
- Student can view their own submission text after submitting
- Grade/feedback visible to student only after instructor publishes it
```

### 4.3 Instructor — Open-Ended Grading

```
AS AN instructor
I WANT TO review and score student open-ended answers
SO THAT I can provide formative feedback and capture assessment data for research

Workflows:
- View list of pending (ungraded) open-ended submissions per question per student
- Enter a numeric score within the defined rubric range
- Optionally add written feedback text
- Publish the grade + feedback (student can then see it)
- Save draft (not visible to student yet) and return later

Acceptance:
- Instructor sees student answer, question prompt, and rubric guide
- Score input is validated against rubric max (no out-of-range saves)
- Grading is not delegated to AI in MVP; AI assistance is a future research item
- Graded submissions are stored with timestamp and instructor_id for research audit trail
```

### 4.4 Student — Results and Progress View

```
AS A dental student
I WANT TO see my MCQ scores, open-ended submission statuses, and case performance
SO THAT I can understand my learning progress across competency areas

Views:
- Topic-level MCQ score summary (% correct per topic)
- Open-ended submission list with status (pending / graded) and published feedback
- Case simulation performance (existing sprint infrastructure)
- Aggregate competency heatmap across C1–C5

Acceptance:
- No correct answer exposure for MCQ questions (feedback shows "correct" or "incorrect" only)
- Open-ended feedback visible only after instructor publishes
- Progress view is read-only for students
- No raw AI evaluation metadata visible to students
```

---

## 5. MVP Scope Boundaries

### 5.1 In Scope (MVP)

| Feature | Rationale |
|---|---|
| Oral Pathology topic definitions (theory layer) | Foundation for question bank and case mapping |
| MCQ question bank — Oral Pathology only | Core assessment mechanism; extends existing quiz infrastructure |
| Open-ended question bank — Oral Pathology only | Supports higher-order reasoning; instructor-graded |
| Theory-to-case mapping table | Ensures every topic is assessable in simulation |
| Instructor manual grading UI for open-ended answers | Human-in-the-loop assessment; research-defensible |
| Student results view (MCQ scores + OE status) | Learner feedback; supports engagement |
| Competency tagging for all questions | Enables competency-area analytics for research |
| Two-panel case workflow (Patient Panel + Assistant Panel) | Existing architecture; extended for theory linkage |
| Scoring weight system: MCQ 35% / OE 40% / Case 25% | Defined in Section 6 |

### 5.2 Deferred (Phase 2 / Future Research)

| Feature | Reason Deferred |
|---|---|
| AI-assisted open-ended grading | Not authoritative until formally validated; overclaims research framing |
| Automated instructor notifications | DECISION-075: notifications excluded from MVP; polling/manual refresh only |
| Non-Oral-Pathology specialties | Out of project scope entirely |
| Adaptive question sequencing (ML-based) | Adds research complexity beyond feasibility scope |
| Student-to-student comparison analytics | Privacy implications; not in TÜBİTAK scope |
| Timed/proctored assessment mode | Deployment/security complexity; Phase 2 |
| MedGemma behavior changes | Explicitly excluded from S8A scope |
| Rubric auto-generation via AI | Future research; not validated |

---

## 6. Scoring Weight Rationale

### 6.1 Weights

| Component | Weight | Rationale |
|---|---|---|
| **MCQ** | 35% | Measures recall and recognition (Bloom's L1–L2). Objective, auto-scored. Provides baseline knowledge check aligned with existing quiz infrastructure. Lower weight reflects that recognition alone is insufficient for clinical competence. |
| **Open-Ended** | 40% | Measures reasoning, justification, and analytical thinking (Bloom's L3–L5). Highest weight because it most directly assesses the process-oriented clinical reasoning that is the core research construct. Instructor-scored to preserve academic rigor. |
| **Case Simulation** | 25% | Measures applied reasoning in a simulated clinical workflow. Uses deterministic scoring rules, not AI judgment. Lower weight in v1 because case content is limited to 6–7 scenarios; as content expands, this weight may be revisited. |

### 6.2 Aggregate Session Score Formula

```
Session Score (%) =
  (MCQ_raw / MCQ_max) × 0.35
  + (OE_instructor_score / OE_max) × 0.40
  + (Case_score / Case_max) × 0.25
```

> **Important:** An aggregate score is only displayed if ALL three components have been completed and graded. Partial scores are shown per-component but no aggregate is surfaced until the open-ended component is graded by instructor.

### 6.3 Pending Grade State

- If open-ended is ungraded: aggregate score is `PENDING`
- MCQ score is always immediately available
- Case score is always immediately available
- This prevents students from calculating their effective grade before instructor review

---

## 7. Theory-to-Case Mapping Requirement

### 7.1 Rule

> **Every Oral Pathology topic in the question bank must map to at least one mini-case in the case library.**

This is a hard content requirement, not a UI feature. It ensures that:
- Students can progress from theory (MCQ/OE) to applied reasoning (case simulation) for every topic
- Instructors can assign a theory block + its matched case as a coherent learning unit
- Research data is linkable across assessment types for the same competency

### 7.2 Mapping Table (Initial — Current Cases)

| Topic | Competency Areas | Mapped Case(s) |
|---|---|---|
| Oral Lichen Planus | C1, C2, C4 | `olp_01` |
| Herpetic Gingivostomatitis (Primary) | C1, C3, C5 | `herpes_01` |
| Behçet Disease | C1, C2, C3, C4 | `behcet_01` |
| Secondary Syphilis (Mucosal) | C1, C2, C3 | `syphilis_02` |
| Mucous Membrane Pemphigoid | C1, C2, C3 | `desquamative_01` |
| Chronic Periodontitis (High-Risk Patient) | C4, C5 | `perio_01` |

> **Gap identification rule:** If a question is authored for a topic that has no matching case, it must be flagged `[UNMAPPED]` and AGENT-4 must flag it for content review before it can be published.

### 7.3 Minimum Viable Coverage

- At least **1 MCQ** and **1 open-ended question** per mapped topic
- At least **1 safety-relevant question** (C5) per case where a safety-critical rule exists (`is_critical_safety_rule = true` in DB)

---

## 8. Two-Panel Workflow Overview

The two-panel layout is the existing DENTAI clinical simulation interface. Sprint 8A defines how the theory and question bank layer integrates with it. No structural change to the panels is authorized in MVP.

### 8.1 Patient Panel (Left)

**Purpose:** Presents all patient-facing clinical information the student interacts with.

| Element | Content |
|---|---|
| Patient vignette | Chief complaint, age, demographics |
| Revealed clinical findings | Unlocked by student actions (oral exam, tests) |
| Clinical images | Triggered by specific actions (`perform_oral_exam`, etc.) |
| Student input area | Free-text action entry |
| Action history | Chronological list of student actions in session |

**Theory integration (MVP):**
- A "Theory Link" badge appears on a finding when it maps to a published topic in the question bank
- Clicking the badge opens a lightweight modal with the topic summary (read-only)
- This is informational only; it does not affect scoring
- Theory Link badge is **not shown during active assessment** — only in practice/study mode

### 8.2 Assistant Panel (Right)

**Purpose:** Organizes discovered case information silently; does not coach toward diagnosis.

| Element | Content |
|---|---|
| Discovered findings list | Auto-populated as student reveals findings |
| Competency area indicators | Shows which C1–C5 areas the current session has touched |
| MCQ progress widget | Shows MCQ completion status for the current topic (study mode only) |
| Open-ended submission status | Shows "submitted / pending grade / graded" per question |
| Score summary (post-session) | MCQ % + OE status + Case score (no aggregate until OE graded) |

**Boundary rule:** The Assistant Panel must **organize discovered information**, not suggest next steps, not hint toward diagnosis, and not surface AI evaluation details. This boundary is preserved from S7.

**Theory integration (MVP):**
- After a session ends, the assistant panel surfaces a "Related Theory" section linking to topic summaries for findings encountered
- This appears only in the post-session review state, not during active simulation

---

## 9. Acceptance Criteria for AGENT-4 (Clinical Taxonomy Work)

AGENT-4's role in Sprint 8A is to build the **Oral Pathology clinical taxonomy**: the structured list of topics, sub-topics, key findings, and differential anchors that underpin the question bank and theory-to-case mappings.

### 9.1 Taxonomy Structure Requirements

Each taxonomy entry must include:

| Field | Type | Requirement |
|---|---|---|
| `topic_id` | string | Unique slug, snake_case (e.g., `oral_lichen_planus`) |
| `topic_name_en` | string | English display name |
| `topic_name_tr` | string | Turkish display name (UI requirement) |
| `icd_code` | string | Relevant ICD-10/ICD-11 code (if applicable) |
| `competency_areas` | list[string] | One or more of: `C1, C2, C3, C4, C5` |
| `difficulty_level` | enum | `easy`, `medium`, `hard` |
| `key_clinical_features` | list[string] | ≥ 3 defining clinical features |
| `diagnostic_tests` | list[string] | Relevant confirmatory or differentiating tests |
| `differentials` | list[string] | Conditions that must be distinguished |
| `safety_flags` | list[string] | Any `is_critical_safety_rule = true` considerations |
| `mapped_case_ids` | list[string] | Matching case IDs from existing case library |
| `unmapped_flag` | boolean | True if no case exists yet for this topic |

### 9.2 Content Quality Gates

AGENT-4's taxonomy deliverable is accepted when:

- [ ] All 6 currently mapped topics have complete taxonomy entries per §9.1 structure
- [ ] Every taxonomy entry has `mapped_case_ids` populated or `unmapped_flag = true`
- [ ] Every safety-critical case (`is_critical_safety_rule = true` in scoring rules) has a corresponding `safety_flags` entry in the taxonomy
- [ ] Competency area coverage: at least C1, C2, and C3 are covered across the full taxonomy; C5 covered by at minimum 2 topics
- [ ] Turkish display names present for all entries (UI requirement)
- [ ] Differential lists contain ≥ 2 conditions per topic
- [ ] No diagnosis names are verbatim reproduced as a quiz question answer without clinical framing (prevents trivial recall; enforces reasoning)

### 9.3 Question Bank Seed Requirements

AGENT-4 is also responsible for seeding the initial question bank structure (not the database schema — only the content catalogue in document form):

**Per topic, minimum seed:**
- 2 MCQ items (at different Bloom's levels: one recall, one application)
- 1 open-ended item (Bloom's L4–L5: analysis or evaluation)

**MCQ item format:**
```
question_text: [string]
options: [A, B, C, D] — exactly 4
correct_option: [single letter, internal use only — never exposed to student]
competency_area: [C1–C5]
bloom_level: [remember | understand | apply | analyze]
topic_id: [slug]
difficulty: [easy | medium | hard]
```

**Open-ended item format:**
```
question_text: [string]
rubric_guide: [string — for instructor, not student]
max_score: [integer, e.g., 20]
competency_area: [C1–C5]
bloom_level: [analyze | evaluate]
topic_id: [slug]
```

### 9.4 Taxonomy Review Gate

Before AGENT-4's taxonomy is consumed by AGENT-2 for any data layer work:
1. Taxonomy document must be reviewed by the Orchestrator
2. Any `[UNMAPPED]` topics must be flagged with a content gap note
3. Any `[REVIEW_NEEDED]` topics carried over from Sprint 2 (`behcet_01`, `syphilis_02`, `desquamative_01`) must remain flagged — AGENT-4 must not silently clear them
4. Safety flag accuracy must be cross-referenced against `scoring_rules.json` `is_critical_safety_rule` fields

---

## 10. Design Constraints (Binding)

| Constraint | Source | Rule |
|---|---|---|
| Extend existing quiz infrastructure | DECISION-074 | Do not design a parallel question system. MCQ bank extends current quiz tables. Propose alternative only if AGENT-2 proves infeasibility. |
| No notifications in MVP | DECISION-075 | Instructor grade publishing triggers no push notification. Student uses manual refresh or polling. |
| Open-ended grading = instructor only | S8A charter | AI grading not in MVP. Any AI assistance is future research scope. |
| Oral Pathology only | S8A charter | No other specialty. No scope creep. |
| Student-safe payload | Sprint 1–7 baseline | Correct answers never exposed to student. MCQ key stays server-side. Open-ended rubric not visible to student. |
| Silent evaluation | Project-wide | Evaluation metadata never surfaces in student-facing responses. |
| Assistant Panel = organizer, not coach | S4–S7 decisions | Panel surfaces discovered information; does not hint toward next steps or diagnosis. |

---

## 11. Decisions Needed

| # | Question | Owner | Urgency |
|---|---|---|---|
| D1 | Should the theory module be its own navigation section, or integrated into the case pre-session flow? | Orchestrator / AGENT-3 | Medium |
| D2 | Is "study mode" vs. "assessment mode" a distinct user mode, or the same interface with different affordances? | Orchestrator | Medium |
| D3 | What is the maximum question bank size for MVP launch? (Suggested: ≥6 MCQ + ≥6 OE, one per topic) | Orchestrator | Low |
| D4 | Should `[REVIEW_NEEDED]` cases (behcet_01, syphilis_02, desquamative_01) be blocked from open-ended question association until domain expert review? | Orchestrator | High |
| D5 | Is Bloom's taxonomy level tagging required by AGENT-4, or is competency area tagging sufficient for TÜBİTAK reporting? | Orchestrator | Medium |

---

## 12. Out of Scope (Binding Exclusions)

- No coding of any kind
- No database schema implementation
- No API endpoint design or implementation
- No frontend component implementation
- No non-Oral-Pathology specialties
- No AI grading implementation or MedGemma behavioral changes
- No deployment work
- No notifications infrastructure
- No adaptive learning algorithms
- No proctored assessment mode

---

## 13. Risks

| Risk | Severity | Mitigation |
|---|---|---|
| `[REVIEW_NEEDED]` cases used before domain expert clears them | HIGH | Block open-ended questions from being linked to those cases until cleared (D4 above) |
| Aggregate score displayed before OE is graded | MEDIUM | Enforce PENDING state logic at product level; AGENT-2 must gate aggregate |
| MCQ answer key accidentally included in student payload | HIGH | Existing allowlist pattern from S7 must be extended; no new exposure surface |
| AI grading introduced informally as a "helper" feature | MEDIUM | AGENT-1 scope boundary is explicit: any AI grading is Phase 2, not MVP |
| Theory content authored without case mapping, creating unmapped questions | MEDIUM | AGENT-4 acceptance criteria require `unmapped_flag` and content gap notes |

---

*End of S8A Product Brief*
*Next: Orchestrator review → AGENT-4 taxonomy work → AGENT-2 data layer design*
