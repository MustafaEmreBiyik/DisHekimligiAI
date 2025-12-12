#!/usr/bin/env python
"""Test paterji testi eylemini"""

import sys
import os
from dotenv import load_dotenv

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

load_dotenv()

from app.agent import DentalEducationAgent

try:
    agent = DentalEducationAgent()
    
    # Test için state
    test_state = {
        "case_id": "behcet_01",
        "patient": {"age": 32, "chief_complaint": "Ağızda yaralar"},
        "revealed_findings": []
    }
    
    print("🧪 Test: 'Paterji testi yapıyorum' eylemini yorumlama\n")
    
    raw_action = "Paterji testi yapıyorum"
    
    interpretation = agent.interpret_action(raw_action, test_state)
    
    print("✅ Yorumlama başarılı!")
    print(f"   Intent Type: {interpretation.get('intent_type')}")
    print(f"   Action: {interpretation.get('interpreted_action')}")
    print(f"   Feedback: {interpretation.get('explanatory_feedback')}")
    print(f"   Clinical Intent: {interpretation.get('clinical_intent')}")
    
except Exception as e:
    print(f"❌ HATA: {e}")
    import traceback
    traceback.print_exc()
