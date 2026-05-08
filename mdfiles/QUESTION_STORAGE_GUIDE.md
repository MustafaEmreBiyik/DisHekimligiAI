# Question Storage Guide
**DentAI**
**Date:** 2026-05-08

## Goal

You have multiple MCQ and open-ended questions, plus answer keys or grading criteria.
The best storage approach in this project is:

1. Store questions at runtime in the database.
2. Keep the original question bank in version-controlled files inside the repo.
3. Import from those files into the database with a repeatable script.

This gives you both operational safety and maintainability.

---

## Recommended Storage Model

### 1. Canonical runtime store: `questions` table

DentAI already has a `questions` table in the application database for both MCQ and open-ended items.

Use that table as the source the app reads during normal operation because:

- the API already loads questions from the DB
- student-safe and instructor-only fields are already separated
- MCQ and open-ended questions can live in one model
- grading and analytics workflows already connect to DB-backed questions

Use the DB for:

- active question delivery
- instructor authoring
- grading workflows
- auditability
- future filtering by topic, difficulty, Bloom level, and safety category

### 2. Canonical authoring source in the repo

Do not rely on manually entering a large question bank through the UI.
For many questions, keep a clean importable source file in the repo as your authoring source.

Recommended location:

- `data/question_bank/`

Recommended files:

- `data/question_bank/mcq_questions.json`
- `data/question_bank/open_ended_questions.json`

The app fallback path for static MCQs should also point to this folder so the project uses one consistent source path.

You can also use CSV if your source is in Excel, but JSON is usually better here because:

- MCQ options are naturally arrays
- open-ended rubric fields are multi-line text
- metadata fields are easier to preserve

### 3. Import script between repo files and DB

The project should treat repo files as seed/import content and the DB as runtime content.

That means:

- edit questions in JSON or CSV
- run an import script
- insert or upsert rows into the `questions` table

This is the cleanest workflow for a medium or large bank.

---

## Why This Is Better Than Other Options

### Better than storing only in JSON

If you store everything only in JSON:

- instructor workflows become harder
- filtering and grading integration become weaker
- updates across environments become manual
- production data and authoring data get mixed

### Better than storing only in the DB

If you store everything only in the DB:

- bulk editing is painful
- version history is weak
- review and collaboration are harder
- migrating to a new environment is riskier

### Better than storing in `.env`

`.env` is only for configuration.
It is not a content store.
Questions and answers should never be stored there.

---

## Best Practical Structure

Use this split:

### A. Repo content

Store import-ready question files in the repository:

```text
data/
  question_bank/
    mcq_questions.json
    open_ended_questions.json
```

### B. Runtime data

Store active questions in the application DB:

```text
db/runtime/dentai_app.db
```

or in production:

- a persistent Docker volume
- or an external database

### C. Import utility

Keep one import script, for example:

```text
scripts/import_question_bank.py
```

Its job should be:

- read JSON or CSV
- validate required fields
- upsert rows into `questions`
- reject broken MCQs
- reject open-ended rows missing rubric fields

---

## Suggested Data Shape

### MCQ item

```json
{
  "question_id": "mcq-oral-pathology-lesion-triage-001",
  "question_type": "MCQ",
  "question_text": "A persistent red-white lesion is found on the lateral tongue. What is the most appropriate next step?",
  "topic_id": "Oral Patoloji",
  "competency_areas": ["lesion triage", "clinical decision making"],
  "bloom_level": "apply",
  "difficulty": "medium",
  "safety_category": "high",
  "options": [
    "Review in one year",
    "Start antifungal treatment only",
    "Arrange urgent biopsy or specialist referral",
    "Polish the area and reassess later"
  ],
  "correct_option": "Arrange urgent biopsy or specialist referral",
  "instructor_explanation": "Persistent red-white lateral tongue lesions may have malignant potential and require urgent tissue diagnosis.",
  "max_score": 1,
  "is_active": true
}
```

### Open-ended item

```json
{
  "question_id": "oe-oral-pathology-lesion-triage-001",
  "question_type": "OPEN_ENDED",
  "question_text": "Explain how you would prioritize the differential diagnosis and next diagnostic step for a persistent red-white lesion on the lateral tongue.",
  "topic_id": "Oral Patoloji",
  "competency_areas": ["differential diagnosis", "lesion triage"],
  "bloom_level": "analyze",
  "difficulty": "hard",
  "safety_category": "high",
  "rubric_guide": "Award full credit when the answer identifies malignant potential, prioritizes serious causes, and recommends urgent biopsy or referral.",
  "model_answer_outline": "Identify red-flag features, prioritize malignant disorders, justify urgency, and recommend biopsy or specialist referral.",
  "instructor_explanation": "This checks whether the learner recognizes a potentially dangerous lesion and escalates correctly.",
  "max_score": 10,
  "is_active": true
}
```

---

## Field Rules

### MCQ rules

- `options` must be an array
- at least 3 options, usually 4
- `correct_option` must exactly match one option
- `rubric_guide` is not required
- `model_answer_outline` is not required

### Open-ended rules

- no options
- no correct option
- `rubric_guide` is required
- `model_answer_outline` is required

### Shared rules

- `question_id` should be unique
- `question_text` should be required
- `topic_id`, `difficulty`, `bloom_level`, and `safety_category` should always be filled
- `is_active` should control whether the item is visible to students

---

## Recommended Workflow

### Small number of questions

If you only have a few items:

- use the instructor panel
- save directly into the database

### Medium or large bank

If you have many items already prepared:

1. Put them into structured JSON files under `data/question_bank/`
2. Validate the format
3. Run an import script
4. Write them into the `questions` table
5. Keep the JSON files as the version-controlled master copy

This is the best balance for maintainability.

---

## Docker / Deployment Note

If you use Docker, do not depend on an in-container SQLite file with no persistence.

Use one of these:

- a mounted persistent volume for SQLite
- or a real external DB

Otherwise your imported question bank can disappear when containers are recreated.

---

## Final Recommendation

For this project, the best approach is:

1. Keep your question bank in repo files under `data/question_bank/`
2. Import those files into the DB-backed `questions` table
3. Let the app read only from the database at runtime

That gives you:

- bulk import support
- version control
- stable runtime behavior
- compatibility with instructor grading and authoring
- a clean path to production

---

## Next Best Step

If your questions already exist in:

- Excel
- CSV
- Word-derived tables
- JSON

the next step should be to create one importer that converts them into the `questions` table automatically.
