# S8A DATA MODEL & SCHEMA DESIGN
**DENTAI | Sprint 8A: Design-Only**
**Author:** AGENT-2 (Backend / Database)
**Date:** 2026-05-07
**Status:** DRAFT — Pending Orchestrator Approval

---

## 1. Existing Quiz Infrastructure Extension Strategy

**Current State:**
The existing quiz system reads MCQs from a static file (`data/question_bank/mcq_questions.json`). Student answers are graded in memory, and only a high-level summary is saved to the database in the `ExamResult` table (`details_json` holds the breakdown). 

**Extension Strategy (Option A):**
We will **extend the existing infrastructure** rather than building a parallel system. 
1. Migrate the static `mcq_questions.json` into a formal `Question` database table.
2. Evolve the `ExamResult` model to support multi-step grading (instructor-in-the-loop) by introducing a `QuizAnswer` child table for granular tracking of individual responses.
3. This ensures all historical exams remain intact while unlocking Open-Ended functionality and instructor grading workflows.

---

## 2. MCQ + Open-Ended Question Support

To support both types, the `Question` model will use a single-table inheritance or polymorphic design with a `question_type` discriminator.

### `Question` (Table)
- `id` (PK, UUID or String)
- `question_type` (Enum: `MCQ`, `OPEN_ENDED`)
- `question_text` (Text)
- `is_active` (Boolean, default True)

**MCQ-Specific Fields (Nullable or JSON):**
- `options` (JSON Array)
- `correct_option` (String) - *Authoring Only*
- `instructor_explanation` (Text) - *Authoring Only*

**Open-Ended Specific Fields:**
- `rubric_guide` (Text) - *Authoring/Instructor Only*
- `model_answer_outline` (Text) - *Authoring/Instructor Only*
- `max_score` (Integer)

---

## 3. Instructor Grading Records

To support manual grading of Open-Ended questions without losing the auto-grading capability of MCQs, we will introduce a `QuizAnswer` table linked to the parent `QuizAttempt` (formerly `ExamResult`).

### `QuizAnswer` (Table)
- `id` (PK)
- `attempt_id` (FK to `QuizAttempt`)
- `question_id` (FK to `Question`)
- `student_response_text` (Text) - *Stores selected option for MCQ, or free text for OE*
- `auto_score` (Integer, nullable) - *Populated instantly for MCQ*
- `grading_status` (Enum: `PENDING`, `GRADED`, `PUBLISHED`) - *Separates graded-but-unpublished from published feedback. PUBLISHED instantly for MCQ.*
- `instructor_score` (Integer, nullable)
- `instructor_feedback` (Text, nullable)
- `graded_by_id` (FK to `User`, nullable) - *Tracks which instructor graded*
- `graded_at` (DateTime, nullable)
- `review_flag` (Boolean, default False) - *Allows instructors to flag answers for review*

---

## 4. Theory-to-Case Mapping & Tagging Model

Tags and mappings will be stored directly on the `Question` table to satisfy the S8A taxonomy requirements.

### Tagging Fields on `Question`
- `topic_id` (String) - e.g., `oral_lichen_planus`
- `QuestionCaseMapping` (Table relation) - *Recommended over a single case ID or JSON array. Supports multiple mini-case mappings and review-needed blocking. If unmapped, flagged as `[UNMAPPED]`.*
- `competency_areas` (JSON Array) - e.g., `["C1", "C2"]`
- `bloom_level` (Enum) - `remember`, `understand`, `apply`, `analyze`, `evaluate`
- `difficulty` (Enum) - `easy`, `medium`, `hard`
- `safety_category` (Enum) - `none`, `missed_critical_step`, `wrong_medication`, etc.

---

## 5. Student-Safe Data Exposure Matrix & Field Separation

To prevent data leakage, the API response models (Pydantic schemas) will strictly segregate fields.

### 5.1 Authoring-Only Fields
*Protected authoring/grading fields are never exposed to student-facing payloads. They may be exposed only through authorized instructor/admin authoring or grading endpoints.*
- `Question.correct_option`
- `Question.instructor_explanation`
- `Question.model_answer_outline`
- `Question.rubric_guide`
- *Internal scoring metadata*

### 5.2 Instructor-Only Fields
*Exposed only via `/api/instructor/*` endpoints.*
- **Grading Queue:** List of `QuizAnswer` where `grading_status != PUBLISHED` and `question_type = OPEN_ENDED`.
- **Rubric & Scores:** `Question.rubric_guide`, `QuizAnswer.instructor_score`.
- **Unpublished Feedback:** `QuizAnswer.instructor_feedback` (before publish action).
- **Review Flags:** `QuizAnswer.review_flag`.

### 5.3 Student-Visible (Before Submission)
*Exposed via `/api/quiz/questions`.*
- `Question.id`
- `Question.question_text` (Stem)
- `Question.options` (Only if MCQ)
- `Question.question_type` (Mode label: MCQ vs OE)
- `Question.difficulty`, `Question.topic_id` (Allowed tags)

### 5.4 Student-Visible (After Submission/Publish)
*Exposed via `/api/quiz/attempts/{id}` only when `QuizAnswer.grading_status = PUBLISHED`.*
- `QuizAnswer.student_response_text` (Selected answer)
- `QuizAnswer.instructor_score` or `auto_score` (Score)
- `QuizAnswer.instructor_feedback` (Published instructor feedback)
- *Student-safe generic feedback (for MCQs)*

---

## 6. Migration Strategy Notes

**Note: No code or migration implementation is allowed in Sprint 8A. These are notes for Sprint 8B.**

1. **Schema Creation:** Alembic will generate the new `questions`, `quiz_attempts`, and `quiz_answers` tables.
2. **Data Seeding:** A startup script will read `data/question_bank/mcq_questions.json`, map the JSON fields to the new `Question` schema (extracting tags, topics, options, and the correct option), and `INSERT` them into the database.
3. **Legacy Data Migration:** Existing `ExamResult` rows will remain for historical archive, or a script will convert them into `QuizAttempt` headers with a generic "legacy" state. The UI will pull from `QuizAttempt` going forward.
4. **Safety Verification:** The migration must verify that the `correct_option` is stripped from all existing JSON structures and moved securely to the protected DB column.
