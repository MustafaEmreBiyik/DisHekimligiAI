from __future__ import annotations

from typing import Any, Dict, List


class ReasoningPatternClassifier:
    """
    Classifies student reasoning behavior into one of four patterns based on
    ordered clinical actions and post-diagnosis deviation signals.
    """

    HISTORY_ACTIONS = {
        "gather_personal_info",
        "check_allergies_meds",
        "ask_hydration_nutrition",
        "check_smoking_history",
        "check_fever",
        "check_vital_signs",
        "check_diabetes",
        "check_bleeding_disorder",
        "check_pacemaker",
        "check_oral_hygiene_habits",
    }

    TEST_ACTIONS = {
        "perform_oral_exam",
        "request_imaging",
        "order_incisional_biopsy",
        "palpate_neck",
    }

    MIN_REQUIRED_ACTIONS = 4
    MIN_REQUIRED_HISTORY_ACTIONS = 2
    MIN_REQUIRED_TEST_ACTIONS = 1

    def classify(self, session_id: int, action_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_actions = len(action_history)
        if total_actions == 0:
            return {
                "session_id": session_id,
                "pattern": "DATA_DRIVEN_EXPLORATION",
                "confidence": 0.4,
                "evidence": {
                    "total_actions": 0,
                    "history_actions": 0,
                    "test_actions": 0,
                    "diagnosis_position": 0.0,
                    "deviation_flags_after_diagnosis": 0,
                },
            }

        actions = [str(item.get("action", "")).strip() for item in action_history]
        history_actions = sum(1 for a in actions if a in self.HISTORY_ACTIONS)
        test_actions = sum(1 for a in actions if a in self.TEST_ACTIONS)

        diagnosis_indices = [i for i, a in enumerate(actions) if a.startswith("diagnose_")]
        diagnosis_index = diagnosis_indices[0] if diagnosis_indices else None
        diagnosis_position = (
            ((diagnosis_index + 1) / total_actions) if diagnosis_index is not None else 0.0
        )

        history_ratio = history_actions / total_actions
        test_ratio = test_actions / total_actions

        deviation_flags_after_diagnosis = 0
        has_revised_diagnosis = False
        if diagnosis_index is not None:
            for idx, item in enumerate(action_history):
                if idx <= diagnosis_index:
                    continue

                item_action = str(item.get("action", "")).strip()
                if item_action.startswith("diagnose_"):
                    has_revised_diagnosis = True

                # Primary expected MedGemma key.
                deviation = item.get("reasoning_deviation")
                # Backward-compatible fallback if flags are provided as counts.
                deviation_count = item.get("reasoning_deviation_flags", 0)

                if isinstance(deviation, bool) and deviation:
                    deviation_flags_after_diagnosis += 1
                elif isinstance(deviation_count, int) and deviation_count > 0:
                    deviation_flags_after_diagnosis += deviation_count

        minimum_required_completed = (
            total_actions >= self.MIN_REQUIRED_ACTIONS
            and history_actions >= self.MIN_REQUIRED_HISTORY_ACTIONS
            and test_actions >= self.MIN_REQUIRED_TEST_ACTIONS
        )

        # 1) Failed hypothesis revision
        if (
            diagnosis_index is not None
            and deviation_flags_after_diagnosis > 0
            and not has_revised_diagnosis
        ):
            pattern = "FAILED_HYPOTHESIS_REVISION"
            confidence = min(0.95, 0.75 + 0.05 * deviation_flags_after_diagnosis)

        # 2) Premature diagnostic closure
        elif (
            diagnosis_index is not None
            and diagnosis_position <= 0.30
            and not minimum_required_completed
        ):
            pattern = "PREMATURE_DIAGNOSTIC_CLOSURE"
            confidence = 0.9

        # 3) Hypothesis-driven inquiry
        elif (
            diagnosis_index is not None
            and history_ratio > 0.4
            and diagnosis_position > 0.70
        ):
            pattern = "HYPOTHESIS_DRIVEN_INQUIRY"
            confidence = min(0.95, 0.7 + history_ratio * 0.3)

        # 4) Data-driven exploration
        elif test_ratio > 0.6:
            pattern = "DATA_DRIVEN_EXPLORATION"
            confidence = min(0.95, 0.7 + test_ratio * 0.25)

        # Deterministic fallback to one of the requested four labels.
        else:
            if diagnosis_index is not None and history_ratio >= test_ratio:
                pattern = "HYPOTHESIS_DRIVEN_INQUIRY"
                confidence = 0.55
            else:
                pattern = "DATA_DRIVEN_EXPLORATION"
                confidence = 0.55

        return {
            "session_id": session_id,
            "pattern": pattern,
            "confidence": round(confidence, 2),
            "evidence": {
                "total_actions": total_actions,
                "history_actions": history_actions,
                "test_actions": test_actions,
                "diagnosis_position": round(diagnosis_position, 2),
                "deviation_flags_after_diagnosis": deviation_flags_after_diagnosis,
            },
        }
