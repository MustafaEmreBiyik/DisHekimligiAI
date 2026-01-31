from __future__ import annotations

import json
import os
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Global in-memory store simulating a database
_STUDENT_STATES: Dict[str, Dict[str, Any]] = {}


class ScenarioManager:
    """
    Loads case scenarios and manages per-student scenario state.
    """

    def __init__(self, cases_path: Optional[str] = None) -> None:
        self._cases_path = cases_path or os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "data", "case_scenarios.json")
        )
        self.case_data: List[Dict[str, Any]] = []
        self._default_case_id: str = "olp_001"
        self._load_cases()

    def _load_cases(self) -> None:
        """
        Load all cases from JSON.
        - On error, log and keep an empty list.
        - Accepts top-level list, or dict with "cases" list.
        """
        try:
            with open(self._cases_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, list):
                self.case_data = data
            elif isinstance(data, dict) and isinstance(data.get("cases"), list):
                self.case_data = data.get("cases", [])
            else:
                logger.error("Unexpected structure in case_scenarios.json; expected a list or a dict with 'cases'.")
                self.case_data = []

            # Determine default case_id from the first case, if available
            if self.case_data:
                first_case = self.case_data[0]
                cid = first_case.get("case_id")
                if isinstance(cid, str) and cid:
                    self._default_case_id = cid

        except FileNotFoundError:
            logger.error("Case scenarios file not found: %s", self._cases_path)
            self.case_data = []
        except json.JSONDecodeError as e:
            logger.error("Failed to parse case scenarios JSON: %s", e)
            self.case_data = []

    def get_state(self, student_id: str) -> Dict[str, Any]:
        """
        Retrieve (or initialize) the state for a student.
        - If new, initialize with the first case's case_id (or default) and current_score=0.
        """
        if student_id not in _STUDENT_STATES:
            # Determine initial case and optional patient info
            first_case = self.case_data[0] if self.case_data else {}
            case_id = first_case.get("case_id") or self._default_case_id

            initial_state: Dict[str, Any] = {
                "case_id": case_id,
                "current_score": 0,
            }
            # Optionally include common fields if available
            if "patient" in first_case and isinstance(first_case["patient"], dict):
                initial_state["patient"] = first_case["patient"]
            if "name" in first_case and isinstance(first_case["name"], str):
                initial_state["case_name"] = first_case["name"]

            _STUDENT_STATES[student_id] = initial_state

        return _STUDENT_STATES[student_id]

    def update_state(self, student_id: str, updates: Dict[str, Any]) -> None:
        """
        Apply updates from the assessment engine to the student's state.
        - If 'score_change' is present and numeric, add it to 'current_score' (do not replace).
        - Merge remaining keys into the student's state.
        """
        if not isinstance(updates, dict):
            return

        state = self.get_state(student_id)  # ensure initialized

        # Handle score change additively
        score_delta = updates.get("score_change")
        if isinstance(score_delta, (int, float)):
            state["current_score"] = state.get("current_score", 0) + score_delta

        # Merge other fields (avoid replacing current_score directly)
        for k, v in updates.items():
            if k in ("score_change", "current_score"):
                continue

            if k not in state:
                state[k] = v
            else:
                # Shallow merge for dicts; extend for lists; replace otherwise
                if isinstance(state[k], dict) and isinstance(v, dict):
                    state[k].update(v)
                elif isinstance(state[k], list) and isinstance(v, list):
                    state[k].extend(v)
                else:
                    state[k] = v

    def get_case_by_id(self, case_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve full case data by case_id from loaded scenarios.
        Returns None if case not found.
        """
        for case in self.case_data:
            if case.get("case_id") == case_id:
                return case
        logger.warning(f"Case not found: {case_id}")
        return None

    def get_case_persona(self, case_id: str) -> str:
        """
        Generate a patient persona prompt for roleplay based on case data.
        Handles inconsistent JSON keys (patient vs hasta_profili).
        
        Returns:
            A Turkish-language patient persona instruction for the LLM.
        """
        case = self.get_case_by_id(case_id)
        if not case:
            return "Siz bir diş hekimliği hastasısınız. Doğal ve samimi şekilde yanıt verin."
        
        # Handle both Turkish (hasta_profili) and English (patient) keys
        patient_data = case.get("patient") or case.get("hasta_profili") or {}
        
        # Extract patient information with fallbacks for both naming conventions
        age = patient_data.get("age") or patient_data.get("yas") or "bilinmeyen yaş"
        gender = patient_data.get("gender") or patient_data.get("cinsiyet") or ""
        chief_complaint = (
            patient_data.get("chief_complaint") or 
            patient_data.get("sikayet") or 
            "Şikayetim var"
        )
        
        # Medical history
        medical_history = (
            patient_data.get("medical_history") or 
            patient_data.get("tibbi_gecmis") or 
            []
        )
        
        # Social history
        social_history = (
            patient_data.get("social_history") or 
            patient_data.get("sosyal_gecmis") or 
            []
        )
        
        # Medications
        medications = patient_data.get("medications") or []
        
        # Construct persona prompt (without emojis to avoid encoding issues)
        persona = f"""SEN BIR HASTA ROLUNDE OYNUYORSUN (ROLEPLAY):

[KIMLIGIN]
- Yas: {age} yasindasin
{f'- Cinsiyet: {gender}' if gender else ''}
- Ana Sikayetin: "{chief_complaint}"

[TIBBI GECMISIN]
{chr(10).join([f'- {item}' for item in medical_history]) if medical_history else '- Ozel bir hastaligim yok'}

[ILACLAR]
{chr(10).join([f'- {item}' for item in medications]) if medications else '- Duzenli ilac kullanmiyorsun'}

[SOSYAL GECMIS]
{chr(10).join([f'- {item}' for item in social_history]) if social_history else '- Ozel bir aliskanlik yok'}

[ROLUNU OYNAMA KURALLARI]
1. SEN HASTAYSIN - Dis hekimi ogrencisi sana soru soracak, sen hasta gibi yanit vereceksin
2. DOGAL KONUS - Tibbi terimler kullanma, siradan bir hasta gibi konus
3. TANINI ACIKLAMA - "Liken planusum var" DEME! Sadece belirtileri anlat: "Agzimda beyaz cizgiler var"
4. KISA VE SAMIMI OL - Gercek hastalar uzun konusmaz, dogal ve ozlu yanitlar ver
5. TURKCE KONUS - Tum yanitlarin Turkce olmali
6. DOKTOR SANA "HOCA" DEMEYECEKTIR - Sen hastasi\nn, ona "Doktor" veya "Hocam" diyeceksin
7. BILMEDIGINI SOYLE - Eger sana teknik bir sey sorulursa "Bilmiyorum hocam" de
8. ACI/RAHATSIZLIK VARSA BELIRT - Eger agrin varsa dogal sekilde "Ah, aciyor" gibi ifade et

SIMDI HASTA ROLUNE GIR ve ogrenci doktorun sorularini yanitla!"""
        
        return persona