#!/usr/bin/env python
"""Test script to verify agent import"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

print(f"Python path: {sys.path[0]}")
print(f"Project root: {project_root}")

try:
    print("\n🔍 Attempting to import DentalEducationAgent...")
    from app.agent import DentalEducationAgent
    print("✅ SUCCESS: DentalEducationAgent imported successfully!")
    print(f"   Agent class: {DentalEducationAgent}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

try:
    print("\n🔍 Attempting to import google.generativeai...")
    import google.generativeai as genai
    print("✅ SUCCESS: google.generativeai imported successfully!")
except Exception as e:
    print(f"❌ FAILED: {e}")

try:
    print("\n🔍 Attempting to import AssessmentEngine...")
    from app.assessment_engine import AssessmentEngine
    print("✅ SUCCESS: AssessmentEngine imported successfully!")
except Exception as e:
    print(f"❌ FAILED: {e}")

try:
    print("\n🔍 Attempting to import ScenarioManager...")
    from app.scenario_manager import ScenarioManager
    print("✅ SUCCESS: ScenarioManager imported successfully!")
except Exception as e:
    print(f"❌ FAILED: {e}")

print("\n✅ All imports completed!")
