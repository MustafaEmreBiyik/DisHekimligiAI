# Patoloji Kategorilerine Göre Vaka Kuralları ve Validasyon

from enum import Enum
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

class DifficultyLevel(Enum):
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    EXPERT = "expert"

class PathologyCategory(Enum):
    INFECTIOUS = "infectious"
    NEOPLASTIC = "neoplastic"
    IMMUNOLOGIC = "immunologic"
    TRAUMATIC = "traumatic"
    DEVELOPMENTAL = "developmental"
    SYSTEMIC = "systemic"
    REACTIVE = "reactive"
    RARE = "rare_conditions"



@dataclass
class CategoryRules:
    """Her patoloji kategorisi için özel kurallar"""
    
    category: PathologyCategory
    min_cases_per_level: Dict[DifficultyLevel, int]
    required_features: List[str]
    optional_features: List[str]
    assessment_focus: Dict[str, float]  # Değerlendirme ağırlıkları
    special_considerations: List[str]

# ============================================================================
# KATEGORİ KURALLARI TANIMLAMALARI
# ============================================================================

INFECTIOUS_DISEASE_RULES = CategoryRules(
    category=PathologyCategory.INFECTIOUS,
    min_cases_per_level={
        DifficultyLevel.BASIC: 8,
        DifficultyLevel.INTERMEDIATE: 8,
        DifficultyLevel.EXPERT: 4
    },
    required_features=[
        "etiyolojik ajan bilgisi",
        "bulaşma yolu",
        "karakteristik klinik bulgular",
        "tanı yöntemi (kültür/smear/PCR)",
        "antimikrobiyal tedavi protokolü"
    ],
    optional_features=[
        "immunokompromize hasta faktörü",
        "antibiyotik direnci",
        "komplikasyonlar"
    ],
    assessment_focus={
        "mikrobiyal tanımlama": 0.25,
        "tedavi seçimi": 0.30,
        "enfeksiyon kontrolü": 0.25,
        "komplikasyon önleme": 0.20
    },
    special_considerations=[
        "Antibiyotik seçiminde alerji kontrolü ZORUNLU",
        "Viral enfeksiyonlarda antibiyotik reçete edilmemeli",
        "Fungal enfeksiyonlarda predispozan faktörler sorgulanmalı",
        "İmmun yetmezlik durumunda konsültasyon gerekli"
    ]
)

NEOPLASTIC_DISEASE_RULES = CategoryRules(
    category=PathologyCategory.NEOPLASTIC,
    min_cases_per_level={
        DifficultyLevel.BASIC: 5,
        DifficultyLevel.INTERMEDIATE: 10,
        DifficultyLevel.EXPERT: 8
    },
    required_features=[
        "lezyon karakteristikleri (boyut, sınır, konsistans)",
        "malignite risk faktörleri",
        "TNM evreleme (malign vakalar için)",
        "biyopsi endikasyonu",
        "acil sevk kriterleri"
    ],
    optional_features=[
        "genetik predispozisyon",
        "metastaz değerlendirmesi",
        "adjuvan tedavi seçenekleri"
    ],
    assessment_focus={
        "erken tanı": 0.30,
        "risk stratifikasyonu": 0.25,
        "sevk zamanlaması": 0.25,
        "hasta bilgilendirme": 0.20
    },
    special_considerations=[
        "Premalign lezyonlarda ZORUNLU takip protokolü",
        "Asemptomatik lezyon = tehlike sinyali",
        "Erken sevk = hayat kurtarır vurgusu",
        "2 haftada iyileşmeyen ülser = biyopsi",
        "Field cancerization konsepti açıklanmalı"
    ]
)

IMMUNOLOGIC_DISEASE_RULES = CategoryRules(
    category=PathologyCategory.IMMUNOLOGIC,
    min_cases_per_level={
        DifficultyLevel.BASIC: 3,
        DifficultyLevel.INTERMEDIATE: 10,
        DifficultyLevel.EXPERT: 7
    },
    required_features=[
        "otoimmün mekanizma",
        "sistemik manifestasyonlar",
        "immunosupresif tedavi seçenekleri",
        "dental tedavi modifikasyonları",
        "multidisipliner yönetim"
    ],
    optional_features=[
        "genetik faktörler",
        "tetikleyici faktörler",
        "alevlenme-remisyon paternleri"
    ],
    assessment_focus={
        "oral-sistemik bağlantı": 0.30,
        "immunosupresyon riskleri": 0.25,
        "tedavi koordinasyonu": 0.25,
        "uzun dönem takip": 0.20
    },
    special_considerations=[
        "Kortikosteroid yan etkileri bilgisi ZORUNLU",
        "Dental prosedür öncesi medikal konsültasyon",
        "Nikolsky sign değerlendirmesi",
        "Immunosupresif tedavi altında enfeksiyon riski yüksek"
    ]
)

TRAUMATIC_LESION_RULES = CategoryRules(
    category=PathologyCategory.TRAUMATIC,
    min_cases_per_level={
        DifficultyLevel.BASIC: 5,
        DifficultyLevel.INTERMEDIATE: 3,
        DifficultyLevel.EXPERT: 2
    },
    required_features=[
        "travma kaynağı identifikasyonu",
        "kronik vs akut travma ayrımı",
        "iyileşme süreci beklentisi",
        "travma kaynağı eliminasyonu"
    ],
    optional_features=[
        "alışkanlık (bruksizm, dil ısırma)",
        "iatrojenik nedenler",
        "self-mutilation"
    ],
    assessment_focus={
        "neden-sonuç ilişkisi": 0.35,
        "kronik travma riski": 0.25,
        "önleyici yaklaşım": 0.25,
        "iyileşme takibi": 0.15
    },
    special_considerations=[
        "2 hafta içinde iyileşme beklenir",
        "Travma kaynağı elimine edilmezse rekürrens",
        "Kronik travma = premalign potansiyel",
        "Şüpheli travma öyküsü = abus olasılığı"
    ]
)

DEVELOPMENTAL_ANOMALY_RULES = CategoryRules(
    category=PathologyCategory.DEVELOPMENTAL,
    min_cases_per_level={
        DifficultyLevel.BASIC: 5,
        DifficultyLevel.INTERMEDIATE: 6,
        DifficultyLevel.EXPERT: 4
    },
    required_features=[
        "gelişimsel timing",
        "genetik/herediter faktörler",
        "sendrom ilişkisi",
        "fonksiyonel etki"
    ],
    optional_features=[
        "aile taraması",
        "prenatal faktörler",
        "cerrahi/ortodontik müdahale"
    ],
    assessment_focus={
        "anomali tanımlama": 0.30,
        "sendrom ayırımı": 0.25,
        "tedavi gerekliliği": 0.25,
        "genetik danışmanlık": 0.20
    },
    special_considerations=[
        "Çoklu anomali = sendrom araştır",
        "Aile öyküsü sorgulanmalı",
        "Erken tanı = daha iyi prognoz",
        "Multidisipliner yaklaşım (ortodonti, cerrahi, genetik)"
    ]
)

SYSTEMIC_MANIFESTATION_RULES = CategoryRules(
    category=PathologyCategory.SYSTEMIC,
    min_cases_per_level={
        DifficultyLevel.BASIC: 3,
        DifficultyLevel.INTERMEDIATE: 10,
        DifficultyLevel.EXPERT: 7
    },
    required_features=[
        "primer sistemik hastalık",
        "oral manifestasyon mekanizması",
        "sistemik hastalık kontrolü",
        "dental tedavi modifikasyonları",
        "medikal konsültasyon"
    ],
    optional_features=[
        "ilaç yan etkileri",
        "nutrisyonel faktörler",
        "metabolik bozukluklar"
    ],
    assessment_focus={
        "oral bulgu-sistemik hastalık bağlantısı": 0.35,
        "medikal durum değerlendirmesi": 0.25,
        "tedavi modifikasyonları": 0.25,
        "multidisipliner iletişim": 0.15
    },
    special_considerations=[
        "Oral bulgular sistemik hastalığın ilk belirtisi olabilir",
        "Kontrolsüz sistemik hastalık = dental tedavi ertele",
        "İlaç etkileşimleri mutlaka kontrol et",
        "Düzenli medikal takip şart"
    ]
)

REACTIVE_LESION_RULES = CategoryRules(
    category=PathologyCategory.REACTIVE,
    min_cases_per_level={
        DifficultyLevel.BASIC: 4,
        DifficultyLevel.INTERMEDIATE: 2,
        DifficultyLevel.EXPERT: 1
    },
    required_features=[
        "irritan faktör identifikasyonu",
        "lezyon gelişim mekanizması",
        "cerrahi eksizyon endikasyonu",
        "rekürrens önleme"
    ],
    optional_features=[
        "hormonal faktörler",
        "sistemik predispozisyon"
    ],
    assessment_focus={
        "irritan eliminasyonu": 0.30,
        "cerrahi planlama": 0.30,
        "histopatolojik doğrulama": 0.25,
        "rekürrens riski": 0.15
    },
    special_considerations=[
        "İrritasyon kaynağı çıkarılmazsa nüks eder",
        "Cerrahi eksizyon sırasında tam çıkarılmalı",
        "Histopatolojik inceleme ZORUNLU",
        "Oral hijyen eğitimi önemli"
    ]
)

RARE_CONDITION_RULES = CategoryRules(
    category=PathologyCategory.RARE,
    min_cases_per_level={
        DifficultyLevel.BASIC: 0,  # Rare cases are not basic
        DifficultyLevel.INTERMEDIATE: 3,
        DifficultyLevel.EXPERT: 5
    },
    required_features=[
        "nadir görülme sıklığı bilgisi",
        "literatür tarama becerisi",
        "uzman konsültasyonu kararı",
        "atipik prezentasyon tanıma"
    ],
    optional_features=[
        "genetik testler",
        "moleküler patoloji",
        "deneysel tedaviler"
    ],
    assessment_focus={
        "literatür kullanımı": 0.25,
        "ayırıcı tanı genişliği": 0.30,
        "uzman sevk kararı": 0.25,
        "belirsizlik yönetimi": 0.20
    },
    special_considerations=[
        "Literatür araştırma izin verilebilir",
        "Emin değilsen konsülte et mesajı",
        "Nadir = her zaman düşün ama önce sık olanlar",
        "Atipik bulgular dikkatle değerlendirilmeli",
        "Multidisipliner yaklaşım esastır"
    ]
)

# ============================================================================
# VAKA VALIDASYON SINIFI
# ============================================================================

class CaseValidator:
    """Vaka kurallarına uygunluk kontrolü"""
    
    def __init__(self):
        self.category_rules = {
            PathologyCategory.INFECTIOUS: INFECTIOUS_DISEASE_RULES,
            PathologyCategory.NEOPLASTIC: NEOPLASTIC_DISEASE_RULES,
            PathologyCategory.IMMUNOLOGIC: IMMUNOLOGIC_DISEASE_RULES,
            PathologyCategory.TRAUMATIC: TRAUMATIC_LESION_RULES,
            PathologyCategory.DEVELOPMENTAL: DEVELOPMENTAL_ANOMALY_RULES,
            PathologyCategory.SYSTEMIC: SYSTEMIC_MANIFESTATION_RULES,
            PathologyCategory.REACTIVE: REACTIVE_LESION_RULES,
            PathologyCategory.RARE: RARE_CONDITION_RULES
        }
    
    def validate_case(self, case_data: Dict) -> Dict[str, any]:
        """Vakayı tüm kurallara göre doğrula"""
        validation_results = {
            "is_valid": True,
            "errors": [],
            "warnings": [],
            "score": 100
        }
        
        # Zorunlu alan kontrolü
        required_fields = [
            "case_id", "metadata", "classification", 
            "patient_profile", "clinical_data", "assessment"
        ]
        
        for field in required_fields:
            if field not in case_data:
                validation_results["errors"].append(
                    f"Zorunlu alan eksik: {field}"
                )
                validation_results["is_valid"] = False
                validation_results["score"] -= 20
        
        if not validation_results["is_valid"]:
            return validation_results
        
        # Kategori-spesifik validasyon
        category = PathologyCategory(case_data["classification"]["pathology_category"])
        rules = self.category_rules[category]
        
        # Zorunlu özellikler kontrolü
        case_features = case_data.get("clinical_data", {}).get("features", [])
        for required_feature in rules.required_features:
            if not self._feature_present(required_feature, case_features):
                validation_results["errors"].append(
                    f"Zorunlu özellik eksik: {required_feature}"
                )
                validation_results["score"] -= 10
        
        # Zorluk seviyesi - patoloji kategorisi uyumu
        difficulty = DifficultyLevel(case_data["classification"]["difficulty_level"])
        if not self._validate_difficulty_category_match(difficulty, category, case_data):
            validation_results["warnings"].append(
                "Zorluk seviyesi ve kategori uyumsuz olabilir"
            )
            validation_results["score"] -= 5
        
        # Süre kontrolü
        estimated_duration = case_data["classification"]["estimated_duration_minutes"]
        if not self._validate_duration(difficulty, estimated_duration):
            validation_results["warnings"].append(
                f"Süre zorluk seviyesi için uygun değil: {estimated_duration} dakika"
            )
            validation_results["score"] -= 5
        
        # Öğrenme hedefleri kontrolü
        learning_objectives = case_data["classification"]["learning_objectives"]
        if len(learning_objectives) < 3:
            validation_results["warnings"].append(
                "En az 3 öğrenme hedefi olmalı"
            )
            validation_results["score"] -= 5
        
        # Soru yapısı validasyonu
        if not self._validate_assessment_structure(case_data["assessment"], difficulty):
            validation_results["errors"].append(
                "Değerlendirme yapısı zorluk seviyesine uygun değil"
            )
            validation_results["score"] -= 15
        
        # Son karar
        if validation_results["score"] < 70:
            validation_results["is_valid"] = False
        
        return validation_results
    
    def _feature_present(self, feature: str, case_features: List[str]) -> bool:
        """Özelliğin vakada bulunup bulunmadığını kontrol et"""
        # Basit string matching - gerçek implementasyonda NLP kullanılabilir
        feature_keywords = feature.lower().split()
        for case_feature in case_features:
            if all(keyword in case_feature.lower() for keyword in feature_keywords):
                return True
        return False
    
    def _validate_difficulty_category_match(
        self, difficulty: DifficultyLevel, category: PathologyCategory, case_data: Dict
    ) -> bool:
        """Zorluk ve kategori uyumunu kontrol et"""
        rules = self.category_rules[category]
        
        # Her kategorinin minimum vaka sayısı gereksinimi var
        if rules.min_cases_per_level[difficulty] == 0:
            return False  # Bu zorluk seviyesinde bu kategori olmamalı
        
        return True
    
    def _validate_duration(self, difficulty: DifficultyLevel, duration: int) -> bool:
        """Süre uygunluğunu kontrol et"""
        expected_ranges = {
            DifficultyLevel.BASIC: (10, 15),
            DifficultyLevel.INTERMEDIATE: (20, 30),
            DifficultyLevel.EXPERT: (30, 45)
        }
        
        min_duration, max_duration = expected_ranges[difficulty]
        return min_duration <= duration <= max_duration
    
    def _validate_assessment_structure(
        self, assessment: Dict, difficulty: DifficultyLevel
    ) -> bool:
        """Değerlendirme yapısının uygunluğunu kontrol et"""
        questions = assessment.get("questions", [])
        
        expected_question_counts = {
            DifficultyLevel.BASIC: (3, 5),
            DifficultyLevel.INTERMEDIATE: (4, 6),
            DifficultyLevel.EXPERT: (5, 7)
        }
        
        min_q, max_q = expected_question_counts[difficulty]
        if not (min_q <= len(questions) <= max_q):
            return False
        
        # Toplam puan kontrolü
        total_points = sum(q.get("max_points", 0) for q in questions)
        if total_points != 100:
            return False
        
        return True

# ============================================================================
# VAKA OLUŞTURMA YÖNERGELERİ
# ============================================================================

class CaseCreationGuidelines:
    """Vaka oluşturma için rehber sınıf"""
    
    @staticmethod
    def get_template(category: PathologyCategory, difficulty: DifficultyLevel) -> Dict:
        """Kategori ve zorluk için vaka şablonu döndür"""
        
        base_template = {
            "case_id": f"{category.value.upper()}_{difficulty.value.upper()}_XXX",
            "metadata": {
                "version": "1.0",
                "created_date": datetime.now().isoformat(),
                "author": "TO_BE_FILLED",
                "reviewed_by": [],
                "status": "draft"
            },
            "classification": {
                "difficulty_level": difficulty.value,
                "pathology_category": category.value,
                "estimated_duration_minutes": CaseCreationGuidelines._get_duration(difficulty),
                "learning_objectives": []
            },
            "patient_profile": {
                "demographics": {
                    "age": None,
                    "gender": None,
                    "ethnicity": "turkish"
                },
                "presentation": {
                    "chief_complaint": "",
                    "duration": "",
                    "onset": "gradual|sudden",
                    "progression": "worsening|stable|improving"
                },
                "history": {
                    "medical": [],
                    "medications": [],
                    "social": {},
                    "family": []
                }
            },
            "clinical_data": {
                "stages": CaseCreationGuidelines._get_stages(difficulty),
                "findings": {
                    "intraoral": [],
                    "extraoral": [],
                    "radiographic": [],
                    "laboratory": []
                },
                "images": {
                    "clinical_photos": [],
                    "radiographs": [],
                    "histopathology": []
                }
            },
            "assessment": {
                "questions": CaseCreationGuidelines._get_question_template(difficulty),
                "correct_answers": {},
                "explanation": {},
                "references": []
            },
            "ai_evaluation_criteria": {
                "knowledge_weight": 0.3,
                "reasoning_weight": 0.4,
                "application_weight": 0.3,
                "custom_rubric": {}
            }
        }
        
        return base_template
    
    @staticmethod
    def _get_duration(difficulty: DifficultyLevel) -> int:
        """Zorluk seviyesine göre varsayılan süre"""
        durations = {
            DifficultyLevel.BASIC: 12,
            DifficultyLevel.INTERMEDIATE: 25,
            DifficultyLevel.EXPERT: 35
        }
        return durations[difficulty]
    
    @staticmethod
    def _get_stages(difficulty: DifficultyLevel) -> int:
        """Progresif açılım aşama sayısı"""
        stages = {
            DifficultyLevel.BASIC: 3,
            DifficultyLevel.INTERMEDIATE: 4,
            DifficultyLevel.EXPERT: 5
        }
        return stages[difficulty]
    
    @staticmethod
    def _get_question_template(difficulty: DifficultyLevel) -> List[Dict]:
        """Zorluk seviyesine göre soru şablonu"""
        
        if difficulty == DifficultyLevel.BASIC:
            return [
                {
                    "id": "q1",
                    "type": "multiple_choice",
                    "text": "En olası tanı nedir?",
                    "max_points": 25,
                    "options": [],
                    "correct_index": None
                },
                {
                    "id": "q2",
                    "type": "multiple_select",
                    "text": "Predispozan faktörler nelerdir?",
                    "max_points": 20,
                    "options": [],
                    "correct_indices": []
                },
                {
                    "id": "q3",
                    "type": "short_answer",
                    "text": "Uygun tedavi yaklaşımı nedir?",
                    "max_points": 30,
                    "key_points": []
                },
                {
                    "id": "q4",
                    "type": "short_answer",
                    "text": "Önleme stratejileri nelerdir?",
                    "max_points": 25,
                    "key_points": []
                }
            ]
        
        elif difficulty == DifficultyLevel.INTERMEDIATE:
            return [
                {
                    "id": "q1",
                    "type": "essay",
                    "text": "Ayırıcı tanı listesi oluşturun ve gerekçelendirin",
                    "max_points": 25,
                    "rubric": {
                        "differential_list": 10,
                        "justification": 15
                    }
                },
                {
                    "id": "q2",
                    "type": "multiple_choice",
                    "text": "En olası tanı hangisidir?",
                    "max_points": 20,
                    "options": [],
                    "correct_index": None
                },
                {
                    "id": "q3",
                    "type": "essay",
                    "text": "Hangi ek tetkikler gereklidir?",
                    "max_points": 20,
                    "key_points": []
                },
                {
                    "id": "q4",
                    "type": "essay",
                    "text": "Kapsamlı tedavi planı oluşturun",
                    "max_points": 25,
                    "rubric": {
                        "primary_treatment": 10,
                        "supportive_care": 8,
                        "follow_up": 7
                    }
                },
                {
                    "id": "q5",
                    "type": "short_answer",
                    "text": "Prognoz nasıldır?",
                    "max_points": 10,
                    "key_points": []
                }
            ]
        
        else:  # EXPERT
            return [
                {
                    "id": "q1",
                    "type": "essay",
                    "text": "Kapsamlı tanısal analiz yapın (diferansiyel tanı, evreleme, risk stratifikasyonu)",
                    "max_points": 25,
                    "rubric": {
                        "differential_diagnosis": 10,
                        "staging": 8,
                        "risk_assessment": 7
                    }
                },
                {
                    "id": "q2",
                    "type": "essay",
                    "text": "Multidisipliner yaklaşım planlayın",
                    "max_points": 20,
                    "rubric": {
                        "specialist_identification": 8,
                        "consultation_sequence": 7,
                        "coordination": 5
                    }
                },
                {
                    "id": "q3",
                    "type": "essay",
                    "text": "Tedavi stratejisi geliştirin",
                    "max_points": 25,
                    "rubric": {
                        "primary_treatment": 10,
                        "adjuvant_options": 8,
                        "complication_management": 7
                    }
                },
                {
                    "id": "q4",
                    "type": "essay",
                    "text": "Prognoz ve takip protokolü",
                    "max_points": 20,
                    "key_points": []
                },
                {
                    "id": "q5",
                    "type": "essay",
                    "text": "Hasta danışmanlığı ve etik değerlendirme",
                    "max_points": 10,
                    "key_points": []
                }
            ]

# ============================================================================
# KULLANIM ÖRNEĞİ
# ============================================================================

if __name__ == "__main__":
    # Yeni vaka oluşturma
    guidelines = CaseCreationGuidelines()
    new_case = guidelines.get_template(
        PathologyCategory.INFECTIOUS,
        DifficultyLevel.BASIC
    )
    
    print("Yeni vaka şablonu oluşturuldu:")
    print(f"Case ID: {new_case['case_id']}")
    print(f"Kategori: {new_case['classification']['pathology_category']}")
    print(f"Zorluk: {new_case['classification']['difficulty_level']}")
    print(f"Tahmini süre: {new_case['classification']['estimated_duration_minutes']} dakika")
    
    # Vaka validasyonu
    validator = CaseValidator()
    
    # Örnek vaka verisi (eksik)
    sample_case = {
        "case_id": "INF_BASIC_001",
        "metadata": {
            "version": "1.0",
            "created_date": "2025-01-15",
            "author": "Dr. Smith",
            "status": "draft"
        },
        "classification": {
            "difficulty_level": "basic",
            "pathology_category": "infectious",
            "estimated_duration_minutes": 12,
            "learning_objectives": [
                "Oral kandidiyazis tanıma",
                "Risk faktörlerini belirleme"
            ]
        },
        "patient_profile": {},
        "clinical_data": {
            "features": [
                "beyaz plaklarla",
                "silinebilir lezyon",
                "diabetes mellitus"
            ]
        },
        "assessment": {
            "questions": [
                {"id": "q1", "max_points": 40},
                {"id": "q2", "max_points": 60}
            ]
        }
    }
    
    # Validasyon yap
    result = validator.validate_case(sample_case)
    
    print("\n" + "="*60)
    print("VALIDASYON SONUÇLARI:")
    print("="*60)
    print(f"Geçerli mi: {result['is_valid']}")
    print(f"Skor: {result['score']}/100")
    
    if result['errors']:
        print("\nHATALAR:")
        for error in result['errors']:
            print(f"  ❌ {error}")
    
    if result['warnings']:
        print("\nUYARILAR:")
        for warning in result['warnings']:
            print(f"  ⚠️  {warning}")