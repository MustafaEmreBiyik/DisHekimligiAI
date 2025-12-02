# app/services/rule_service.py
import importlib.util

def load_rules_for_case(category):
    # pathology-category-rules.py dosyasını dinamik yükle
    # category (örn: INFECTIOUS) için ilgili kuralları (REQUIRED_DIAGNOSTIC_FEATURES vs.) döndür.
    pass