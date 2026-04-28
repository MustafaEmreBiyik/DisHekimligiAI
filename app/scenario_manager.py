from __future__ import annotations

import json
import os
import logging
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

from db.database import CaseDefinition, SessionLocal, StudentSession


class ScenarioManager:
    """
    Loads case scenarios and manages per-student scenario state.
    """

    def __init__(
        self,
        cases_path: Optional[str] = None,
        session_factory: Optional[Callable[[], Any]] = None,
        allow_json_fallback: Optional[bool] = None,
    ) -> None:
        self._cases_path = cases_path or os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "data", "case_scenarios.json")
        )
        self._session_factory = session_factory or SessionLocal
        self._allow_json_fallback = (
            allow_json_fallback
            if allow_json_fallback is not None
            else os.getenv("DENTAI_ALLOW_CASE_JSON_FALLBACK", "").strip().lower() in {"1", "true", "yes", "on"}
        )
        self._json_case_data: List[Dict[str, Any]] = []
        self._json_default_case_id: Optional[str] = None
        self._load_json_cases()

    @property
    def case_data(self) -> List[Dict[str, Any]]:
        """Student-visible active cases sourced from DB first."""
        return self.list_cases()

    def _load_json_cases(self) -> None:
        """
        Load JSON fallback cases.
        - On error, log and keep an empty list.
        - Accepts top-level list, or dict with "cases" list.
        """
        try:
            with open(self._cases_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                self._json_case_data = data
            elif isinstance(data, dict) and isinstance(data.get("cases"), list):
                self._json_case_data = data.get("cases", [])
            else:
                logger.error("Unexpected structure in case_scenarios.json; expected a list or a dict with 'cases'.")
                self._json_case_data = []

            if self._json_case_data:
                first_case = self._json_case_data[0]
                cid = first_case.get("case_id")
                if isinstance(cid, str) and cid:
                    self._json_default_case_id = cid

        except FileNotFoundError:
            logger.error("Case scenarios file not found: %s", self._cases_path)
            self._json_case_data = []
        except json.JSONDecodeError as e:
            logger.error("Failed to parse case scenarios JSON: %s", e)
            self._json_case_data = []

    def _serialize_case_definition(self, case: CaseDefinition) -> Dict[str, Any]:
        payload = dict(case.source_payload) if isinstance(case.source_payload, dict) else {}
        patient_info = case.patient_info_json if isinstance(case.patient_info_json, dict) else {}
        states = case.states_json if isinstance(case.states_json, dict) else {}

        payload.update(
            {
                "case_id": case.case_id,
                "schema_version": case.schema_version,
                "title": case.title,
                "category": case.category,
                "difficulty": case.difficulty,
                "estimated_duration_minutes": case.estimated_duration_minutes,
                "is_active": bool(case.is_active),
                "learning_objectives": list(case.learning_objectives or []),
                "prerequisite_competencies": list(case.prerequisite_competencies or []),
                "competency_tags": list(case.competency_tags or []),
                "initial_state": case.initial_state,
                "states": states,
                "patient_info": patient_info,
            }
        )

        if not isinstance(payload.get("name"), str) or not payload.get("name"):
            payload["name"] = case.title

        if not isinstance(payload.get("patient"), dict) or not payload.get("patient"):
            payload["patient"] = patient_info

        return payload

    def _fetch_db_cases(self, *, include_inactive: bool) -> List[Dict[str, Any]]:
        db = self._session_factory()
        try:
            query = db.query(CaseDefinition).filter(CaseDefinition.is_archived.is_(False))
            if not include_inactive:
                query = query.filter(CaseDefinition.is_active.is_(True))

            rows = (
                query.order_by(CaseDefinition.created_at.asc(), CaseDefinition.case_id.asc()).all()
            )
            return [self._serialize_case_definition(row) for row in rows]
        finally:
            db.close()

    def _fetch_db_case(self, case_id: str, *, include_inactive: bool) -> Dict[str, Any]:
        if not case_id:
            return {}

        db = self._session_factory()
        try:
            query = db.query(CaseDefinition).filter(
                CaseDefinition.case_id == case_id,
                CaseDefinition.is_archived.is_(False),
            )
            if not include_inactive:
                query = query.filter(CaseDefinition.is_active.is_(True))

            row = query.first()
            return self._serialize_case_definition(row) if row else {}
        finally:
            db.close()

    def _db_catalog_has_cases(self) -> bool:
        db = self._session_factory()
        try:
            row = (
                db.query(CaseDefinition.id)
                .filter(CaseDefinition.is_archived.is_(False))
                .first()
            )
            return row is not None
        finally:
            db.close()

    def _should_use_json_fallback(self) -> bool:
        if not self._allow_json_fallback:
            return False

        if self._db_catalog_has_cases():
            return False

        logger.warning(
            "Using opt-in JSON case fallback because no DB case_definitions rows are available."
        )
        return True

    def _json_cases(self, *, include_inactive: bool) -> List[Dict[str, Any]]:
        if include_inactive:
            return list(self._json_case_data)

        cases: List[Dict[str, Any]] = []
        for case in self._json_case_data:
            if not isinstance(case, dict):
                continue
            if case.get("is_active", True):
                cases.append(case)
        return cases

    def list_cases(self) -> List[Dict[str, Any]]:
        db_cases = self._fetch_db_cases(include_inactive=False)
        if db_cases:
            return db_cases

        if self._should_use_json_fallback():
            return self._json_cases(include_inactive=False)

        return []

    def get_case(self, case_id: str, *, include_inactive: bool = False) -> Dict[str, Any]:
        case = self._fetch_db_case(case_id, include_inactive=include_inactive)
        if case:
            return case

        if self._should_use_json_fallback():
            for fallback_case in self._json_cases(include_inactive=include_inactive):
                if isinstance(fallback_case, dict) and fallback_case.get("case_id") == case_id:
                    return fallback_case

        return {}

    def _find_case(self, case_id: str) -> Dict[str, Any]:
        if not case_id:
            return {}
        return self.get_case(case_id, include_inactive=True)

    def _get_default_case_id(self) -> Optional[str]:
        cases = self.list_cases()
        if cases:
            case_id = cases[0].get("case_id")
            if isinstance(case_id, str) and case_id:
                return case_id

        if self._should_use_json_fallback():
            return self._json_default_case_id

        return None

    def _build_initial_state(self, case_id: str) -> Dict[str, Any]:
        case = self._find_case(case_id) or {}

        state: Dict[str, Any] = {
            "case_id": case_id,
            "revealed_findings": [],
            "history": [],
        }

        # Case category (used by RuleService / MedGemma silent validation)
        category = case.get("category") or case.get("Category") or case.get("kategori")
        if isinstance(category, str) and category.strip():
            state["category"] = category.strip()

        canonical_patient = case.get("patient_info")
        if isinstance(canonical_patient, dict) and canonical_patient:
            state["patient"] = canonical_patient

        # Normalize patient fields (case_scenarios.json is primarily Turkish-keyed today)
        patient: Dict[str, Any] = {}
        if "patient" not in state:
            hp = case.get("hasta_profili")
            if isinstance(hp, dict):
                if "yas" in hp:
                    patient["age"] = hp.get("yas")
                if "sikayet" in hp:
                    patient["chief_complaint"] = hp.get("sikayet")
                if "tibbi_gecmis" in hp:
                    patient["medical_history"] = hp.get("tibbi_gecmis")
                if "sosyal_gecmis" in hp:
                    patient["social_history"] = hp.get("sosyal_gecmis")

            # Back-compat: if the case uses the older English schema
            if not patient and isinstance(case.get("patient"), dict):
                patient = case.get("patient", {})

            if patient:
                state["patient"] = patient

        case_name = case.get("title") or case.get("name")
        if isinstance(case_name, str) and case_name.strip():
            state["case_name"] = case_name.strip()

        difficulty = case.get("difficulty") or case.get("zorluk_seviyesi")
        if isinstance(difficulty, str) and difficulty.strip():
            state["case_difficulty"] = difficulty.strip()

        return state

    def get_state(self, student_id: str, case_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieve (or initialize) the persistent state for a student.

        Selection rule:
        - If case_id is provided, use the most recent StudentSession for (student_id, case_id).
        - Else, use the most recent StudentSession for the student.

        If no session exists, create one for the default case.
        """
        if not student_id:
            return {}

        db = self._session_factory()
        try:
            query = db.query(StudentSession).filter(StudentSession.student_id == student_id)
            if case_id:
                query = query.filter(StudentSession.case_id == case_id)

            session = query.order_by(StudentSession.start_time.desc()).first()

            if not session:
                # Create a new persistent session for the default case
                chosen_case_id = case_id or self._get_default_case_id()
                if not chosen_case_id:
                    return {}
                initial_state = self._build_initial_state(chosen_case_id)
                session = StudentSession(
                    student_id=student_id,
                    case_id=chosen_case_id,
                    current_score=0.0,
                    state_json=json.dumps(initial_state, ensure_ascii=False),
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                return initial_state

            # Load and validate state_json
            raw = session.state_json or "{}"
            try:
                state = json.loads(raw) if isinstance(raw, str) else {}
            except Exception:
                logger.warning("Invalid state_json for student_id=%s session_id=%s; resetting.", student_id, session.id)
                state = {}

            if not isinstance(state, dict) or not state:
                state = self._build_initial_state(session.case_id or case_id or (self._get_default_case_id() or ""))

            # Ensure case_id is present and consistent
            effective_case_id = case_id or session.case_id or state.get("case_id") or self._get_default_case_id() or ""
            state["case_id"] = effective_case_id

            # Keep DB score as the source of truth for score
            state["current_score"] = session.current_score or 0.0

            # Persist repaired/initialized state back if needed
            if (session.state_json or "").strip() == "" or raw == "{}" or state.get("case_id") != session.case_id:
                session.case_id = effective_case_id
                session.state_json = json.dumps(state, ensure_ascii=False)
                db.commit()

            return state
        finally:
            db.close()

    def update_state(self, student_id: str, updates: Dict[str, Any], case_id: Optional[str] = None) -> None:
        """
        Apply updates from the assessment engine to the student's persistent state.

        Behavior:
        - Updates StudentSession.current_score additively when 'score_change' is numeric.
        - Merges remaining keys into the state_json dict (shallow merge; list extends).
        - Persists back to StudentSession.state_json.
        """
        if not isinstance(updates, dict):
            return

        if not student_id:
            return

        db = self._session_factory()
        try:
            query = db.query(StudentSession).filter(StudentSession.student_id == student_id)
            if case_id:
                query = query.filter(StudentSession.case_id == case_id)
            session = query.order_by(StudentSession.start_time.desc()).first()

            if not session:
                # Ensure a session exists so we have a place to store state
                _ = self.get_state(student_id, case_id=case_id)
                session = db.query(StudentSession).filter(StudentSession.student_id == student_id)
                if case_id:
                    session = session.filter(StudentSession.case_id == case_id)
                session = session.order_by(StudentSession.start_time.desc()).first()
                if not session:
                    return

            # Load current state
            raw = session.state_json or "{}"
            try:
                state = json.loads(raw) if isinstance(raw, str) else {}
            except Exception:
                state = {}

            if not isinstance(state, dict) or not state:
                state = self._build_initial_state(session.case_id or case_id or (self._get_default_case_id() or ""))

            # Apply score change to DB score (source of truth)
            score_delta = updates.get("score_change")
            if isinstance(score_delta, (int, float)):
                session.current_score = (session.current_score or 0.0) + float(score_delta)
                state["current_score"] = session.current_score

            # Merge other fields into state_json
            for k, v in updates.items():
                if k in ("score_change",):
                    continue

                if k not in state:
                    state[k] = v
                else:
                    if isinstance(state[k], dict) and isinstance(v, dict):
                        state[k].update(v)
                    elif isinstance(state[k], list) and isinstance(v, list):
                        state[k].extend(v)
                    else:
                        state[k] = v

            # Ensure case_id
            effective_case_id = case_id or session.case_id or state.get("case_id") or self._get_default_case_id() or ""
            session.case_id = effective_case_id
            state["case_id"] = effective_case_id

            session.state_json = json.dumps(state, ensure_ascii=False)
            db.commit()
        finally:
            db.close()
