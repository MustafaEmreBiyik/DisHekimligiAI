# S8A TAXONOMY — Oral Pathology Learning Module

**Author:** AGENT-4 (Clinical Content)
**Date:** 2026-05-06
**Status:** DRAFT — Pending Orchestrator Approval

---

## 1. Oral Pathology Topic Taxonomy

The taxonomy is restricted strictly to **Oral Pathology**. It is organized hierarchically into four major clinical categories.

### Category 1: Immune-Mediated & Autoimmune Conditions
* **topic_id:** `oral_lichen_planus`
  * **topic_name_en:** Oral Lichen Planus
  * **topic_name_tr:** Oral Liken Planus
  * **competency_areas:** [C1, C2, C4]
  * **difficulty_level:** medium
  * **key_clinical_features:** ["Reticular white striae (Wickham's striae)", "Bilateral buccal mucosa involvement", "Erosive/erythematous areas"]
  * **diagnostic_tests:** ["Clinical examination", "Biopsy (if atypical)"]
  * **differentials:** ["Oral Candidiasis", "Leukoplakia", "Mucous Membrane Pemphigoid"]
  * **safety_flags:** []
  * **mapped_case_ids:** ["olp_001"]
  * **unmapped_flag:** false

* **topic_id:** `behcet_disease`
  * **topic_name_en:** Behçet Disease
  * **topic_name_tr:** Behçet Hastalığı
  * **competency_areas:** [C1, C2, C3, C4]
  * **difficulty_level:** hard
  * **key_clinical_features:** ["Recurrent aphthous-like ulcers", "Genital ulcers", "Ocular lesions (uveitis)"]
  * **diagnostic_tests:** ["Pathergy Test", "Clinical Criteria (ISG)"]
  * **differentials:** ["Recurrent Aphthous Stomatitis", "Crohn's Disease", "Erythema Multiforme"]
  * **safety_flags:** ["missed_critical_step (Pathergy test)"]
  * **mapped_case_ids:** ["behcet_01"]
  * **unmapped_flag:** false
  * **review_needed:** true

* **topic_id:** `mucous_membrane_pemphigoid`
  * **topic_name_en:** Mucous Membrane Pemphigoid
  * **topic_name_tr:** Müköz Membran Pemfigoidi
  * **competency_areas:** [C1, C2, C3, C5]
  * **difficulty_level:** hard
  * **key_clinical_features:** ["Desquamative gingivitis", "Intact bullae", "Positive Nikolsky sign"]
  * **diagnostic_tests:** ["Direct Immunofluorescence (DIF)", "Nikolsky Test"]
  * **differentials:** ["Pemphigus Vulgaris", "Erosive Lichen Planus", "Linear IgA Disease"]
  * **safety_flags:** ["missed_critical_step (DIF biopsy)", "missed_critical_step (Ophthalmology referral)"]
  * **mapped_case_ids:** ["desquamative_01"]
  * **unmapped_flag:** false
  * **review_needed:** true

### Category 2: Infectious Diseases of the Oral Mucosa
* **topic_id:** `primary_herpetic_gingivostomatitis`
  * **topic_name_en:** Primary Herpetic Gingivostomatitis
  * **topic_name_tr:** Primer Herpetik Gingivostomatitis
  * **competency_areas:** [C1, C3, C5]
  * **difficulty_level:** medium
  * **key_clinical_features:** ["Diffuse vesicles and ulcers", "Erythematous gingiva", "Systemic symptoms (fever, lymphadenopathy)"]
  * **diagnostic_tests:** ["Clinical examination", "Cytology (Tzanck smear)"]
  * **differentials:** ["Herpangina", "Hand-Foot-and-Mouth Disease", "Erythema Multiforme"]
  * **safety_flags:** ["wrong_medication (Antibiotics)", "missed_critical_step (Fever/vital check)"]
  * **mapped_case_ids:** ["herpes_primary_01", "infectious_child_01"]
  * **unmapped_flag:** false

* **topic_id:** `secondary_syphilis`
  * **topic_name_en:** Secondary Syphilis (Mucosal)
  * **topic_name_tr:** Sekonder Sifiliz (Müköz Plak)
  * **competency_areas:** [C1, C2, C3, C4, C5]
  * **difficulty_level:** hard
  * **key_clinical_features:** ["Mucous patches", "Maculopapular rash (palms/soles)", "Lymphadenopathy"]
  * **diagnostic_tests:** ["VDRL/RPR", "TPHA/FTA-ABS"]
  * **differentials:** ["Oral Squamous Cell Carcinoma", "Oral Candidiasis", "Infectious Mononucleosis"]
  * **safety_flags:** ["missed_critical_step (Serology)", "missed_critical_step (Infection control/PPE)"]
  * **mapped_case_ids:** ["syphilis_02"]
  * **unmapped_flag:** false
  * **review_needed:** true

### Category 3: Potentially Malignant Disorders & Neoplasms
* **topic_id:** `oral_leukoplakia`
  * **topic_name_en:** Oral Leukoplakia
  * **topic_name_tr:** Oral Lökoplaki
  * **competency_areas:** [C1, C2, C3]
  * **difficulty_level:** medium
  * **key_clinical_features:** ["White plaque that cannot be scraped off", "Cannot be characterized clinically as any other disease"]
  * **diagnostic_tests:** ["Incisional Biopsy"]
  * **differentials:** ["Frictional Keratosis", "Hyperplastic Candidiasis", "Lichen Planus"]
  * **safety_flags:** []
  * **mapped_case_ids:** []
  * **unmapped_flag:** true

### Category 4: Reactive & Inflammatory Lesions
* **topic_id:** `pyogenic_granuloma`
  * **topic_name_en:** Pyogenic Granuloma
  * **topic_name_tr:** Piyojenik Granülom
  * **competency_areas:** [C1, C2]
  * **difficulty_level:** easy
  * **key_clinical_features:** ["Erythematous nodule", "Bleeds easily", "Often on gingiva"]
  * **diagnostic_tests:** ["Excisional Biopsy"]
  * **differentials:** ["Peripheral Giant Cell Granuloma", "Peripheral Ossifying Fibroma", "Hemangioma"]
  * **safety_flags:** []
  * **mapped_case_ids:** []
  * **unmapped_flag:** true

---

## 2. Unified Tagging Standard

Every question in the question bank must adhere to the following tagging standard to enable competency analytics and theory-to-case linkage.

| Tag Category | Allowed Values | Usage Rule |
|---|---|---|
| **Topic ID** | `oral_lichen_planus`, `behcet_disease`, etc. | Must match exactly one `topic_id` from the taxonomy. |
| **Competency Area** | `C1`, `C2`, `C3`, `C4`, `C5` | Multi-select allowed. Must align with the topic's defined competencies. |
| **Difficulty** | `easy`, `medium`, `hard` | Single selection. Reflects the cognitive load of the question. |
| **Bloom Level** | `remember`, `understand`, `apply`, `analyze`, `evaluate` | Mandatory. MCQs typically L1-L3; Open-ended L4-L5. |
| **Safety Category** | `missed_critical_step`, `premature_treatment`, `wrong_medication`, `contraindication_violation`, `none` | Required for any question tagged with `C5`. |
| **Course Week** | `week_01` to `week_14` | Optional. Used by instructors for curriculum sequencing. |

---

## 3. Sample MCQ Templates

*Note: `correct_option` and `instructor_explanation` must NEVER be exposed in student-facing pre-submit payloads (Student-Safe boundary from S7).*

### MCQ Example 1: Lesion Recognition (Bloom: Understand)
* **Question Text:** A 45-year-old female presents with bilateral interlacing white lines on her buccal mucosa. She reports mild sensitivity when eating spicy foods. Which of the following is the most likely diagnosis?
* **Options:**
  * A) Pseudomembranous Candidiasis
  * B) Oral Lichen Planus
  * C) Leukoplakia
  * D) Linea Alba
* **[AUTHORING-ONLY] Correct Option:** B
* **[AUTHORING-ONLY] Instructor Explanation:** Bilateral reticular white lines (Wickham's striae) on the buccal mucosa are pathognomonic for Oral Lichen Planus. Candidiasis scrapes off; Leukoplakia is typically unilateral and a diagnosis of exclusion; Linea alba is unilateral/bilateral but presents as a single thick line at the occlusal plane without sensitivity.
* **[STUDENT-SAFE] Feedback Note:** Review the defining morphological characteristics and distribution patterns of immune-mediated mucocutaneous lesions.
* **Tags:** `topic: oral_lichen_planus`, `competency: C1`, `bloom: understand`, `difficulty: medium`, `safety: none`

### MCQ Example 2: Diagnostic Test Selection (Bloom: Apply)
* **Question Text:** A 6-year-old child presents with diffuse oral vesicles, erythematous gingiva, a temperature of 39°C, and lymphadenopathy. Which of the following is the most appropriate next step in management?
* **Options:**
  * A) Prescribe systemic amoxicillin
  * B) Perform an incisional biopsy
  * C) Recommend palliative care, hydration, and antipyretics
  * D) Apply topical corticosteroids
* **[AUTHORING-ONLY] Correct Option:** C
* **[AUTHORING-ONLY] Instructor Explanation:** The clinical picture is classic for Primary Herpetic Gingivostomatitis (viral). Antibiotics (A) and corticosteroids (D) are contraindicated. A biopsy (B) is unnecessary for a classic acute presentation. Supportive care (C) is correct.
* **[STUDENT-SAFE] Feedback Note:** Consider the viral etiology of this acute presentation and the contraindications for medications like antibiotics in viral infections.
* **Tags:** `topic: primary_herpetic_gingivostomatitis`, `competency: C3, C5`, `bloom: apply`, `difficulty: easy`, `safety: wrong_medication`

### MCQ Example 3: Systemic Correlation (Bloom: Analyze)
* **Question Text:** A patient presents with desquamative gingivitis. A positive Nikolsky sign is observed. Direct immunofluorescence (DIF) of a perilesional biopsy shows linear deposition of IgG and C3 at the basement membrane zone. Which systemic complication must this patient be urgently evaluated for?
* **Options:**
  * A) Uveitis and genital ulcers
  * B) Symblepharon and conjunctival scarring
  * C) Neurosyphilis
  * D) Esophageal candidiasis
* **[AUTHORING-ONLY] Correct Option:** B
* **[AUTHORING-ONLY] Instructor Explanation:** The DIF pattern and clinical signs define Mucous Membrane Pemphigoid (MMP). MMP has a high risk of ocular involvement (cicatricial pemphigoid), which can lead to symblepharon and blindness. Prompt ophthalmology referral is a critical safety step.
* **[STUDENT-SAFE] Feedback Note:** Review the systemic mucosal sites affected by Mucous Membrane Pemphigoid and their long-term complications.
* **Tags:** `topic: mucous_membrane_pemphigoid`, `competency: C4, C5`, `bloom: analyze`, `difficulty: hard`, `safety: missed_critical_step`

---

## 4. Sample Open-Ended Templates

*Rule: Open-ended grading is manual (Instructor). AI grading is excluded from the MVP. Do NOT link these to `[REVIEW_NEEDED]` cases in production until cleared.*

### Open-Ended Example 1: Differential Diagnosis (Bloom: Analyze)
* **Question Text:** A 32-year-old male presents with recurrent, painful aphthous-like ulcers in the oral cavity. List three essential questions you must ask during the anamnesis to narrow your differential diagnosis, and justify why each question is necessary.
* **Tags:** `topic: behcet_disease`, `competency: C2, C4`, `bloom: analyze`, `difficulty: hard`
* **[AUTHORING-ONLY] Rubric Criteria:**
  1. Mentions genital ulcers (Systemic correlation for Behçet).
  2. Mentions ocular symptoms like uveitis/redness (Systemic correlation for Behçet).
  3. Mentions GI symptoms or skin lesions (Crohn's, Erythema Multiforme).
  4. Provides valid justification for each.
* **[AUTHORING-ONLY] Score Bands:**
  * **Excellent (16-20 pts):** Identifies 3 correct areas with strong justification.
  * **Adequate (10-15 pts):** Identifies 2 correct areas or lacks justification.
  * **Poor (0-9 pts):** Focuses only on local trauma; misses systemic links.
* **Faculty Review Note:** *[REVIEW_NEEDED] — Do not link to active case `behcet_01` until clinical accuracy of the case itself is cleared by the domain expert.*

### Open-Ended Example 2: Treatment & Safety Justification (Bloom: Evaluate)
* **Question Text:** A 5-year-old patient is diagnosed with Primary Herpetic Gingivostomatitis. The parents request antibiotics because the child has a high fever and swollen gums. Draft your explanation to the parents, detailing your treatment plan and why you are refusing antibiotics.
* **Tags:** `topic: primary_herpetic_gingivostomatitis`, `competency: C5`, `bloom: evaluate`, `difficulty: medium`
* **[AUTHORING-ONLY] Rubric Criteria:**
  1. Clearly states the etiology is viral, not bacterial.
  2. Explains that antibiotics are ineffective and may cause harm/resistance.
  3. Outlines supportive care (hydration, antipyretics, soft diet).
* **[AUTHORING-ONLY] Score Bands:**
  * **Excellent (16-20 pts):** Empathetic communication, correct etiology, clear safety rationale.
  * **Adequate (10-15 pts):** Mentions viral etiology but lacks detailed supportive care.
  * **Poor (0-9 pts):** Agrees to prescribe antibiotics or fails to explain the rationale.

### Open-Ended Example 3: Diagnostic Reasoning (Bloom: Analyze)
* **Question Text:** Compare and contrast the clinical presentation of Oral Lichen Planus (reticular type) and Oral Leukoplakia. Why is an incisional biopsy often mandatory for Leukoplakia but not always for classic reticular Lichen Planus?
* **Tags:** `topic: oral_lichen_planus`, `competency: C1, C2, C3`, `bloom: analyze`, `difficulty: medium`
* **[AUTHORING-ONLY] Rubric Criteria:**
  1. Recognizes Leukoplakia as a potentially malignant disorder and a diagnosis of exclusion.
  2. Recognizes classic reticular OLP has pathognomonic bilateral presentation.
  3. States biopsy in Leukoplakia is to rule out dysplasia/SCC.
* **[AUTHORING-ONLY] Score Bands:**
  * **Excellent (16-20 pts):** Covers all three points accurately.
  * **Adequate (10-15 pts):** Compares clinical features but misses the dysplasia aspect.
  * **Poor (0-9 pts):** Incorrectly defines the lesions or recommends wrong biopsy strategy.

---

## 5. Clinical Accuracy & Faculty Review Workflow

### 5.1 Faculty Approval Scope
The Domain Expert (Faculty) must formally approve:
1. All `[REVIEW_NEEDED]` case definitions before they are published to students.
2. The `is_critical_safety_rule` designations in the scoring engine.
3. The validity of internal correct answers for MCQs and Rubric guidelines for Open-Ended questions.

### 5.2 Handling `[REVIEW_NEEDED]` Cases
- **Rule 1:** Cases marked as `[REVIEW_NEEDED]` (e.g., `behcet_01`, `syphilis_02`, `desquamative_01`) **cannot** be linked to active, graded open-ended questions.
- **Rule 2:** The `[REVIEW_NEEDED]` flag exists in the orchestrator logs and migration notes. It **cannot be unilaterally cleared** by an AI agent.
- **Rule 3:** If a theory topic maps to a `[REVIEW_NEEDED]` case, the theory topic itself may be published for MCQ study mode, but the OE assessment linkage remains BLOCKED.

---

## 6. Theory-to-Case Mapping Examples

This mapping table enforces the S8A-T1 requirement that topics must be assessable in simulation.

| Topic ID | Mapped Case ID | Status | Notes |
|---|---|---|---|
| `oral_lichen_planus` | `olp_001` | **APPROVED** | Fully mapped and cleared for both MCQ and OE links. |
| `primary_herpetic_gingivostomatitis` | `herpes_primary_01` | **APPROVED** | Cleared for MCQ, OE, and simulation workflow. |
| `mucous_membrane_pemphigoid` | `desquamative_01` | **BLOCKED** | Case is `[REVIEW_NEEDED]`. OE linkage is disabled until faculty clears the Nikolsky/DIF critical safety flags. |
| `secondary_syphilis` | `syphilis_02` | **BLOCKED** | Case is `[REVIEW_NEEDED]`. Waiting for faculty decision on PPE/infection control rules. |
| `behcet_disease` | `behcet_01` | **BLOCKED** | Case is `[REVIEW_NEEDED]`. Waiting for progressive disclosure fix verification. |
| `oral_leukoplakia` | `none` | **UNMAPPED** | Gap identified. Needs a case to be authored in future sprints. |

---

## 7. Data Visibility Boundaries

This section defines the strict payload and UI visibility boundaries for all assessment data to maintain the "Student-Safe" requirement.

### 7.1 Authoring-Only
*Never exposed in any runtime payload (student or instructor).*
- `correct_answer`
- `correct_option`
- `instructor_explanation`
- `model_answer_outline`
- `rubric_guide`
- `internal scoring metadata`

### 7.2 Instructor-Only
*Visible to authenticated instructors; never exposed to students.*
- `grading queue`
- `rubric scores`
- `unpublished feedback`
- `review flags`

### 7.3 Student-Visible (Before Submission)
*Safe for exposure during active assessment.*
- `question stem`
- `options`
- `allowed tags if safe`
- `mode label`

### 7.4 Student-Visible (After Submission/Publish)
*Exposed only after student completes the action or instructor publishes grades.*
- `selected answer`
- `score if appropriate`
- `student-safe feedback`
- `published instructor feedback`

---
*End of Document*
