"""
Mock responses for testing when API quota is exceeded.
Used only as fallback when LLM API fails.
"""

from typing import Dict, Any

# Türkçe eylem anahtar kelimeleri -> action mapping
TURKISH_ACTION_MAP = {
    # Vital signs
    "ateş": "check_vital_signs",
    "ateşini": "check_vital_signs",
    "vital": "check_vital_signs",
    
    # Examinations
    "muayene": "perform_oral_exam",
    "oral muayene": "perform_oral_exam",
    "ağız muayene": "perform_oral_exam",
    "ekstraoral": "perform_extraoral_exam",
    
    # Tests
    "paterji": "perform_pathergy_test",
    "paterji test": "perform_pathergy_test",
    "seroloji": "request_serology_tests",
    "kan testi": "request_serology_tests",
    "vdrl": "request_serology_tests",
    "tpha": "request_serology_tests",
    
    # History taking
    "sistemik": "ask_systemic_symptoms",
    "sistemik semptom": "ask_systemic_symptoms",
    "tıbbi geçmiş": "gather_medical_history",
    "alerji": "check_allergies_meds",
    "ilaç": "check_allergies_meds",
    
    # Treatment
    "antibiyotik": "prescribe_antibiotics",
    "destekleyici tedavi": "prescribe_palliative_care",
    "palyatif": "prescribe_palliative_care",
    
    # Diagnosis
    "herpes tanı": "diagnose_herpetic_gingivostomatitis",
    "behçet tanı": "diagnose_behcet_disease",
    "sifiliz tanı": "diagnose_secondary_syphilis",
}


def get_mock_interpretation(raw_action: str) -> Dict[str, Any]:
    """
    Simple keyword-based fallback when LLM API is unavailable.
    Returns a structured interpretation based on Turkish keywords.
    """
    raw_lower = raw_action.lower()
    
    # Try to match action
    matched_action = "unspecified_action"
    for keyword, action in TURKISH_ACTION_MAP.items():
        if keyword in raw_lower:
            matched_action = action
            break
    
    # Determine if it's clinical or chat
    clinical_keywords = ["yap", "ölç", "sorgula", "başlat", "test", "muayene", "tanı", "reçete"]
    is_clinical = any(kw in raw_lower for kw in clinical_keywords)
    
    if is_clinical:
        return {
            "intent_type": "ACTION",
            "interpreted_action": matched_action,
            "clinical_intent": "diagnosis_gathering",
            "priority": "medium",
            "safety_concerns": [],
            "explanatory_feedback": f"Eylem yorumlandı: {matched_action.replace('_', ' ').title()}",
            "structured_args": {},
        }
    else:
        return {
            "intent_type": "CHAT",
            "interpreted_action": "general_chat",
            "clinical_intent": "other",
            "priority": "low",
            "safety_concerns": [],
            "explanatory_feedback": "Sohbet modu. Klinik eylemlere odaklanın.",
            "structured_args": {},
        }
