# Question Bank Folder

This folder is the version-controlled source for bulk question authoring.

## Files

- `mcq_questions.json`
- `open_ended_questions.json`

## Usage

1. Put multiple-choice questions into `mcq_questions.json`.
2. Put open-ended questions into `open_ended_questions.json`.
3. Keep these files as the editable source of truth for bulk updates.
4. Import them into the database after review.
5. The legacy MCQ fallback path in the API now points to `data/question_bank/mcq_questions.json`.

## Notes

- Do not store questions in `.env`.
- Runtime delivery should come from the database, not directly from these files.
