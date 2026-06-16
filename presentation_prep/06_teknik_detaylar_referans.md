# DentAI — Teknik Detaylar Referans Kartı

> Bu dosya sunumda sorulabilecek teknik sorulara hazırlık için hızlı başvuru kartıdır.

---

## API Endpoint Referansı

| Endpoint | Method | Açıklama |
|----------|--------|---------|
| `/api/auth/register` | POST | Yeni kullanıcı kaydı |
| `/api/auth/login` | POST | JWT token üretimi |
| `/api/chat/{case_id}/start` | POST | Simülasyon oturumu başlatma |
| `/api/chat/{session_id}/message` | POST | Öğrenci komutu gönderme |
| `/api/recommendations` | GET | Kişiselleştirilmiş vaka önerisi |
| `/api/research/snapshots` | POST | Araştırma snapshot oluşturma |
| `/api/research/snapshots` | GET | Snapshot listesi |
| `/api/research/snapshots/{id}/export` | GET | Snapshot dışa aktarma |

---

## Veritabanı Tablo Sayımı

| Kategori | Tablo Sayısı | Örnekler |
|----------|-------------|---------|
| Auth/Kullanıcı | 1 | users |
| Klinik İçerik | 3 | case_definitions, case_publish_history, mini_cases |
| Öğrenci Etkileşim | 6 | student_sessions, chat_logs, quiz_attempts, quiz_answers, exam_results, llm_interaction_log |
| ML/Araştırma | 8 | mastery_states, irt_parameters, recommendation_model_versions, recommendation_snapshots, recommendation_feature_logs, system_snapshots, ai_scoring_log |
| Tekrarlama | 1 | review_schedules |
| Bildirim | 1 | notifications |

Toplam Alembic Migration: 18 revizyon

---

## Modeller ve Parametreler

### BKT Varsayılan Parametreler
```python
BKT_P_INIT    = 0.3    # İlk bilgi olasılığı
BKT_P_TRANSIT = 0.1    # Öğrenme geçişi
BKT_P_SLIP    = 0.1    # Bilen öğrencinin yanlış yapma olasılığı
BKT_P_GUESS   = 0.2    # Bilmeyenin doğru tahmin olasılığı

Eşikler:
  BKT_MASTERY_HIGH_THRESHOLD = 0.80  # Uzmanlaşma
  BKT_MASTERY_LOW_THRESHOLD  = 0.60  # Risk bölgesi
```

### IRT Parametreleri
```python
IRT_MIN_SAMPLE = 200        # Gerçek fit için minimum yanıt sayısı
IRT_MODEL = "2PL"           # İki parametreli lojistik

a_bounds = (0.05, 5.0)      # Ayrım gücü sınırları
b_bounds = (-4.0, 4.0)      # Güçlük sınırları
n_simulees = 300             # Sentetik bootstrap örnek sayısı
```

### Öneri Motoru Parametreleri
```python
EXPLORATION_EPSILON = 0.10                    # ε-greedy keşif oranı
COLD_START_SESSION_THRESHOLD = 5              # Bu altında V1 kullanılır
RECOMMENDATION_ALGORITHM = "v2_hybrid_xgb_irt_bkt"
RECOMMENDATION_FALLBACK = "v1_competency_based"
```

### SM-2 Parametreleri
```python
_MIN_EASE = 1.3      # Minimum ease faktörü
_EASE_BONUS = 0.1    # Rating=5 için bonus
_EASE_PENALTY = 0.2  # Başarısız için ceza

Aralık formülü:
  rep=1 → 1 gün
  rep=2 → 6 gün
  rep>2 → önceki × ease_factor
```

---

## Gemini Yapılandırması

```python
model_name = "models/gemini-2.5-flash-lite"
temperature = 0.2              # Düşük → deterministik yanıtlar
top_p = 0.9
top_k = 40
max_output_tokens = 512
response_mime_type = "application/json"
```

---

## Güvenlik Eşik Değerleri

```python
MAX_STUDENT_INPUT_CHARS = 2000    # Öğrenci girdi sınırı
MAX_MODEL_FEEDBACK_CHARS = 500    # Model çıktı sınırı

Injection Risk Skorları:
  instruction_override  : 3
  role_override         : 2
  prompt_exfiltration   : 3
  jailbreak_pattern     : 2
  system_role_injection : 2
  
Eşik → tespit için toplam skor hesaplanır, loglanır
```

---

## Sprint - Özellik Matrisi (Tüm Geçmiş)

| Sprint | Ana Özellikler |
|--------|----------------|
| S1 | Klinik simülasyon çekirdeği, JWT auth, temel kural motoru |
| S2 | Schema tanımları, öğrenci profili |
| S3 | Analitik motoru, öneri taslağı |
| S4 | Coach/Validator mimarisi (MedGemma taslak) |
| S5 | Eğitimci paneli, vaka yönetimi |
| S6 | LLM güvenlik katmanı, admin paneli |
| S7 | DB-runtime kurallar, dinamik vaka yükleme |
| S8 | Quiz sistemi, açık uçlu puanlama, sınav takvimi |
| S9 | LLM etkileşim loglama, bildirim sistemi |
| S10 | SM-2 tekrarlama, rubrik versiyonlama, IRT taslak |
| **S11** | **BKT, IRT 2PL fit, Feature Store (37 boyut), XGBoost, araştırma snapshot** |

---

## Klasör Yapısı (Önemli Dizinler)

```
dentai/
├── backend/
│   ├── app/
│   │   ├── agent.py                    # Ana AI pipeline
│   │   ├── assessment_engine.py        # Kural motoru
│   │   ├── analytics_engine.py         # Performans analizi
│   │   ├── rules/clinical_rules.py     # Klinik kural veritabanı
│   │   ├── services/
│   │   │   ├── bkt_service.py          # BKT
│   │   │   ├── irt_calibration.py      # IRT 2PL
│   │   │   ├── spaced_repetition.py    # SM-2
│   │   │   ├── feature_store.py        # 37-boyut özellik matrisi
│   │   │   ├── recommendation_engine_v2.py  # XGBoost
│   │   │   ├── recommendation_trainer.py    # Model eğitimi
│   │   │   ├── llm_safety.py           # Güvenlik
│   │   │   └── med_gemma_service.py    # MedGemma wrapper
│   │   └── api/routers/
│   │       └── research.py             # Snapshot API
│   ├── alembic/versions/              # 18 DB migrasyon
│   └── tests/                         # Birim + API + E2E testler
│
└── frontend/
    └── app/
        ├── chat/[case_id]/             # Simülasyon arayüzü
        ├── student/recommendations/    # Öneri görüntüleme
        └── instructor/research/        # Araştırma snapshotlar
```

---

## Kullanılan Akademik Referanslar

| Algoritma | Referans |
|-----------|---------|
| BKT | Corbett & Anderson (1995), "Knowledge Tracing" |
| IRT 2PL | Birnbaum (1968), Lord (1980) |
| SM-2 | Wozniak (1990), SuperMemo-2 Algorithm |
| XGBoost | Chen & Guestrin (2016) |
| SHAP | Lundberg & Lee (2017) |
| ε-greedy | Sutton & Barto (2018), Reinforcement Learning |

---

## Test Kapsamı

```
tests/
├── unit/           # BKT, IRT, composite score, topic accuracy, rubric versioning
├── api/            # Auth, cases, quiz, bulk questions, mini cases
├── security/       # LLM safety, quiz hardening, prompt injection
└── e2e/            # Uçtan uca oturum akışı
```

Toplam test dosyası: 20+
