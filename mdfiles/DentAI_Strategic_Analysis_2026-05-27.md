# DentAI — Derinlemesine Stratejik Analiz Raporu

**Hazırlanma Tarihi:** 2026-05-27
**Kapsam:** Mevcut mimari değerlendirmesi + Sprint 9+, Mid-term ve Long-term yol haritası
**Mevcut Durum:** Sprint 0–8 büyük ölçüde tamamlandı; toplam 233+ backend testi geçiyor, TypeScript 0 hata
**Hazırlayan:** Claude (Opus 4.7)

---

## A. MEVCUT MİMARİ DEĞERLENDİRMESİ

### A.1 Güçlü Yönler (Korunmalı)

| Alan | Mevcut Yetkinlik | Stratejik Değer |
|------|-----------------|-----------------|
| **Hybrid AI Pipeline** | `agent.py` (Gemini interpretation) + `assessment_engine.py` (deterministik rule engine) + `med_gemma_service.py` (silent validator) | LLM hallüsinasyon riskini kurala çiviler, klinik güvenlik için kritik |
| **Silent Evaluator Architecture** | MedGemma arka planda validasyon yapar, öğrenci akışını bölmez | Pedagojik flow-state'i koruyor (önemli UX kazancı) |
| **LLM Safety Layer** | `llm_safety.py` — prompt injection deteksiyon (5 patern), text sanitization, response filtering, control char removal | Production-grade, akademik etik kuruluna gösterilebilir seviyede |
| **Rubric Versioning (T-4B)** | `RubricVersion` immutable snapshot tablosu — her cevap, hangi rubrik versiyonu altında değerlendirildiyse o snapshot'a foreign key tutar | Akademik denetlenebilirlik için altın standart — bu hâlâ pek çok ed-tech'te yok |
| **Reasoning Pattern Classifier** | `reasoning_classifier.py` — öğrenci akıl yürütme örüntüsünü 4 sınıfa ayırır (history-driven, test-driven, premature, data-driven) | Bu tek başına **bir araştırma makalesi konusu**. Sıradan bir LMS'te yok |
| **Composite Score with Effective Weight Redistribution** | Eksik bileşen olduğunda ağırlıkları dinamik yeniden dağıtıyor, cold-start ile zero-score ayrımı yapıyor (`None` vs `0.0`) | Psikometrik olarak doğru — istatistiksel hatadan kaçınıyor |
| **Explainable Recommendation Engine** | `RecommendationSnapshot` tablosu reason_code + priority_score + algorithm_version tutar | XAI gereksinimi karşılanmış; AB AI Act ve eğitim etik kurulları için hazır |
| **Validator Audit Log** | Her MedGemma çağrısı session_id + latency + safety_violation ile kayıt altında | Production observability + araştırma için longitudinal veri |
| **Soft-Delete + Archival** | User, Question, CaseDefinition için is_archived + archived_at | Veri kaybı yok, GDPR/KVKK uyumlu |
| **DB-first Rules, JSON Fallback Opt-in** | `assessment_engine.py` rules_json'u DB'den okur, JSON sadece env flag ile fallback | Production hazır; içerik versiyonlama için altyapı kurulmuş |

### A.2 Teknik Borçlar ve Zayıf Noktalar

#### KRİTİK — Production'a Çıkmadan Çözülmeli

1. **SQLite production fitting** — `db/runtime/dentai_app.db` tek dosya. Concurrent write'larda kilit sorunu, replikasyon yok. Postgres normalization var (`_normalize_database_url`) ama gerçek prod test eksik.
2. **In-memory Scenario State riski (`scenario_manager.py`)** — `_STUDENT_STATES` global dict kalıntısı (REACT_MIGRATION_AUDIT'te belirtilmiş); horizontal scale'de oturum kaybı.
3. **Global agent instance (`chat.py`)** — Modül seviyesinde `agent = DentalEducationAgent(...)` singleton; multi-tenancy ve key rotation için anti-pattern.
4. **Test suite stabilitesi** — `test_database_startup_sprint7.py` ve `test_sprint2_schema_import.py`'de pre-existing sandbox hataları (Windows path stripping + PermissionError). CI'ya çıkarsa ürettiği zaman temizlenmeli.

#### YÜKSEK — Yakın Vadede

5. **Hardcoded katsayılar** — `_WEAK_THRESHOLD_PCT = 60.0`, MCQ:0.35 / OE:0.40 / Case:0.25 ağırlıkları. Sprint 6 planında `app/constants.py` öneriliyor — yapılmamış.
6. **`_TOPIC_LABELS` duplikasyonu** — En az iki dosyada tekrar.
7. **`mcq_questions.json` legacy format** — `topic_id`, `bloom_level`, `competency_areas` eksik; tagging matrisini bozar.
8. **`open_ended_questions.json` boş** — Sprint 5'in T-5A bekliyor.
9. **AI scoring rate limiting yok** — HuggingFace free tier throttle olursa cascade failure. Sprint 6 T-6D bunu kapsıyor ama henüz yapılmamış.
10. **Mini-vaka formatı tanımsız** — Sprint 3 borcu, klinik ekip kararı bekliyor.

#### ORTA — Mid-term Toparlanmalı

11. **Frontend bundle ve performance ölçümü yok** — Lighthouse score, code splitting metriği yok.
12. **API endpoint'leri için OpenAPI tag organizasyonu zayıf** — Swagger'da kategorize olmuyor.
13. **CORS allowlist hardcoded** — Production domain join environment'a taşınmalı.
14. **Test coverage raporu yok** — `pytest-cov` yapılandırılmamış; gerçek %X bilinmiyor.
15. **Frontend test yok** — Sadece `tsc --noEmit` var; Jest/Vitest + RTL eksik.
16. **No CI/CD** — `.github/workflows/test.yml` Sprint 6 T-6E'de planlı, henüz yok.

---

## B. STRATEJİK BÜYÜME EKSENLERİ

### B.1 DentAI'yi Sıradan Chatbot Projelerinden Ayıracak İleri Seviye Özellikler

#### F1 — Bayesian Knowledge Tracing (BKT) / DKT Layer

**Konsept:** Her öğrencinin her konu için "mastery probability"'sini ardışık güncelleyen olasılıksal model.

- **Neden önemli:** Şu anki `topic_accuracy_service` sadece *aritmetik ortalama* veriyor (1/3 → %33). BKT, "öğrenci konuyu *öğrenmekte mi yoksa rastgele mi doğru yapıyor*" sorusuna olasılıksal cevap verir.
- **Teknik zorluk:** Orta (BKT) → Yüksek (DKT/LSTM-based)
- **Araştırma değeri:** Çok yüksek — TÜBİTAK feasibility study'sinde "intelligent tutoring system" iddiasını destekler
- **Kullanıcı etkisi:** Yüksek — adaptive recommendation engine'in matematiksel temeli
- **Mimari etkisi:** Yeni `mastery_state` tablosu + her cevapta state update; recommendation engine bunu input olarak alır
- **Kategori:** 🟣 Research Critical + 🔵 Future Vision

#### F2 — Item Response Theory (IRT) Bazlı Soru Kalitesi Metriği

**Konsept:** Her sorunun *difficulty parameter* (b) ve *discrimination parameter* (a) IRT modeli ile fit edilir.

- **Neden önemli:** Şu anki `difficulty` enum (easy/medium/hard) eğitmen sezgisi. IRT, hangi sorunun gerçekten ayırt edici olduğunu istatistiksel olarak söyler.
- **Teknik zorluk:** Orta-Yüksek (2PL veya 3PL model, `py-irt` kütüphanesi)
- **Araştırma değeri:** Çok yüksek — soru bankası kalite makalesi konusu (JDE/EJDE için ideal)
- **Kullanıcı etkisi:** Orta (eğitmen — düşük discrimination'lı soruları temizler)
- **Mimari etkisi:** `Question` tablosuna `irt_a`, `irt_b`, `irt_calibrated_at`; nightly batch job
- **Kategori:** 🟣 Research Critical

#### F3 — Multimodal Lesion Recognition (Image + Text)

**Konsept:** Klinik fotoğraf (OLP wickham striae, herpes ülserler, vb.) öğrenciye gösterilir → öğrenci tanımlar → MedGemma + vision model çift validasyon yapar.

- **Neden önemli:** Oral patoloji **görsel tanıma** üzerine kurulu bir alan. Sadece metin tabanlı simülasyon klinik gerçekliği yansıtmıyor.
- **Teknik zorluk:** Yüksek (image asset pipeline, lisanslı görseller, vision LLM seçimi)
- **Araştırma değeri:** Çok yüksek — multimodal medical AI yayını
- **Kullanıcı etkisi:** Çok yüksek — gerçek klinik beceri transferi
- **Mimari etkisi:** Yeni `LesionImage` tablosu, S3/object storage, image preprocessing, image-aware Question subtype
- **Kategori:** 🔵 Future Vision

#### F4 — Spaced Repetition Scheduler (SM-2 / FSRS)

**Konsept:** Öğrencinin zayıf konularını Anki benzeri spaced repetition algoritması ile yeniden sunma.

- **Neden önemli:** Şu anki "weak topic" tespiti pasif; aksiyon önermiyor. SRS proaktif uzun-vadeli tutundurma sağlar.
- **Teknik zorluk:** Düşük-Orta (FSRS açık kaynak; entegrasyon kolay)
- **Araştırma değeri:** Orta-Yüksek
- **Kullanıcı etkisi:** Çok yüksek — retention metrikleri
- **Mimari etkisi:** `ReviewSchedule` tablosu, daily background job, mobile-friendly notification
- **Kategori:** 🟢 High Impact / Low Effort

#### F5 — Cognitive Load Profiling

**Konsept:** Öğrencinin oturum başına ortalama yanıt süresi, hint kullanımı, geri dönme sayısı vb. ile bilişsel yük profili.

- **Neden önemli:** "Doğru cevap" yetersiz bir sinyal; öğrenci 30 saniye düşünüp doğru yapmakla 5 dakika düşünüp doğru yapmak farklı.
- **Teknik zorluk:** Düşük (zaten `ChatLog` + `CoachHint` + `ValidatorAuditLog` var)
- **Araştırma değeri:** Yüksek — yeni bir analytics dimension
- **Kullanıcı etkisi:** Orta (eğitmen — overloaded öğrenciyi tespit)
- **Mimari etkisi:** Mevcut tablolar yeterli; bir derived analytics view + nightly aggregate
- **Kategori:** 🟢 High Impact / Low Effort

---

### B.2 Akademik Araştırma Değerini Artıracak Sistemler

#### R1 — Reproducible Research Snapshot System

**Konsept:** Belirli bir tarihteki **tüm sistem durumu** (sorular + rubrikler + scoring rules + LLM model_id + prompt versionları) tek bir immutable bundle olarak çekilebilir. Yayında "DentAI v2.3.1 snapshot 2026-04-15" denebilir.

- **Neden önemli:** Yayın yapılan veriler 6 ay sonra reproduce edilemiyorsa peer review'da reddedilir.
- **Teknik zorluk:** Orta
- **Araştırma değeri:** **Kritik** — yayın yapmadan önce kurulması zorunlu
- **Mimari etkisi:** `SystemSnapshot` tablosu + git-tag benzeri release süreci + S3'e bundle export
- **Kategori:** 🟣 Research Critical

#### R2 — A/B Testing Framework (Pedagogical Intervention)

**Konsept:** Öğrenci kohortunu otomatik gruplara böl (örn. "Group A: standart rubrik; Group B: rubrik + AI suggestion") → metrik karşılaştır.

- **Neden önemli:** RCT (randomized controlled trial) yapmadan "AI eğitimi iyileştiriyor" iddiası akademik değer taşımaz.
- **Teknik zorluk:** Orta-Yüksek
- **Araştırma değeri:** Çok yüksek
- **Mimari etkisi:** `Experiment`, `ExperimentArm`, `UserExperimentAssignment` tabloları; feature flag service
- **Kategori:** 🟣 Research Critical

#### R3 — Inter-Rater Reliability Analytics Dashboard

**Konsept:** Sprint 8C'de planlı "Çoklu Hoca Puanlama"nın üzerine Cohen's Kappa, ICC (Intraclass Correlation Coefficient) hesabı + AI-vs-human bias grafiği.

- **Neden önemli:** "Rubrik tutarlı mı?" sorusuna istatistiksel cevap. Aynı zamanda AI scoring validation'ın kendisi de bir yayın konusu.
- **Teknik zorluk:** Orta
- **Araştırma değeri:** Çok yüksek (bunun olmadığı bir LLM-as-judge sistemi peer review'da delinmesi kolay)
- **Mimari etkisi:** `InterRaterAnalysisJob` + dashboard endpoint'i
- **Kategori:** 🟣 Research Critical

#### R4 — Longitudinal Learning Trajectory Tracking

**Konsept:** Bir öğrencinin tüm dönem boyunca *learning curve*'ünü matematiksel modelle (e.g., power law of practice) fit etme.

- **Neden önemli:** "Tek bir snapshot" yerine **trajectory**. Bu, kabuldeki yayında "DentAI öğrenci ilerlemesini X% hızlandırdı" şeklinde claim yapılabilmesinin önkoşulu.
- **Teknik zorluk:** Orta
- **Araştırma değeri:** Çok yüksek
- **Mimari etkisi:** Aggregated weekly snapshots, time-series tablo
- **Kategori:** 🟣 Research Critical

#### R5 — Open Dataset & Anonymization Pipeline

**Konsept:** Yayında **anonymized dataset release** edilebilmesi için PII/PHI strip + k-anonymity guarantee'li export tool.

- **Neden önemli:** Top-tier dergi (Nature Digital Medicine, JAMIA) data availability ister.
- **Teknik zorluk:** Orta-Yüksek (DP audit, k-anonymity test)
- **Araştırma değeri:** Çok yüksek — citation impact'i ciddi şekilde artırır
- **Kategori:** 🟣 Research Critical + 🔵 Future Vision

---

### B.3 Klinik Akıl Yürütme Değerlendirmesini Bilimselleştirecek Mekanizmalar

#### CR1 — Script Concordance Test (SCT) Modülü

**Konsept:** Öğrenciye bir vaka senaryosu verilir, sonra "Eğer X bulgu varsa, Y tanı olasılığı [+2 ... -2] arası nasıl değişir?" sorulur. Cevap, uzman panel ortalamasıyla karşılaştırılır.

- **Neden önemli:** SCT, **uncertainty altında klinik akıl yürütmenin altın standart ölçümü**. Geleneksel MCQ yapamadığı şeyi yapar.
- **Teknik zorluk:** Orta (yeni soru tipi)
- **Araştırma değeri:** **Çok yüksek** — SCT eğitim psikometri literatüründe yaygın, klinik düşünme makalesi konusu
- **Kullanıcı etkisi:** Yüksek
- **Mimari etkisi:** Yeni `QuestionType.SCT` enum değeri + uzman panel `ScriptConcordanceReference` tablosu
- **Kategori:** 🟣 Research Critical

#### CR2 — Bayesian Differential Diagnosis Coach

**Konsept:** Vaka simülasyonunda öğrenci her bulgu topladığında, tanı olasılıkları Bayesian güncellemeyle gösterilir. Öğrencinin kendi olasılık tahmini ile karşılaştırılır.

- **Neden önemli:** "Differential diagnosis reasoning" S8A'da C2 competency olarak tanımlı ama şu anki sistemde sadece "doğru tanı seçildi mi" ölçülüyor. Olasılıksal düşünce ölçülmüyor.
- **Teknik zorluk:** Yüksek
- **Araştırma değeri:** Çok yüksek
- **Kategori:** 🟣 Research Critical + 🔵 Future Vision

#### CR3 — Diagnostic Reasoning Time-Series (Process Tracing)

**Konsept:** Öğrenci hangi sıra ile aksiyon aldı, hangi noktada tanıdan döndü vb. — `reasoning_classifier.py` zaten 4 pattern'i sınıflıyor; bunun üzerine bir vaka-bazlı timeline görselleştirme.

- **Neden önemli:** "Outcome" değil "process" ölçümü. Eğitim psikolojisinde *expert vs novice reasoning pathway* karşılaştırması yayın değeri yüksek.
- **Teknik zorluk:** Orta
- **Araştırma değeri:** Yüksek
- **Mimari etkisi:** ChatLog'lardan derive edilebilir; yeni tablo gerekmez
- **Kategori:** 🟢 High Impact / Low Effort

#### CR4 — Safety-Critical Action Reaction Time Metric

**Konsept:** Pacemaker check, allergy screening gibi safety-critical aksiyonlar için "from case start to action" süresini ölç.

- **Neden önemli:** Klinik safety'de "doğru aksiyon" yeterli değil; **zamanında doğru aksiyon** önemli.
- **Teknik zorluk:** Düşük (ChatLog timestamp'leri zaten var)
- **Araştırma değeri:** Orta-Yüksek
- **Kategori:** 🟢 High Impact / Low Effort

---

### B.4 Production-Grade Mimari Dönüşümleri

#### P1 — Database Migration: SQLite → Postgres (Tam Geçiş)

- **Neden:** Concurrent write, partial index, JSON operators, replication. Şu an `_normalize_database_url` Supabase pooler handling var ama runtime gerçek Postgres üzerinde test edilmemiş.
- **Zorluk:** Orta
- **Kategori:** 🔴 Production Critical

#### P2 — Background Job Queue (Celery / RQ / arq)

- **Neden:** AI scoring, rubric snapshot, IRT calibration, nightly analytics — şu an hepsi sync veya yok. Rate limit'ten önce queue mantıklı.
- **Zorluk:** Orta
- **Kategori:** 🔴 Production Critical

#### P3 — Observability Stack (Logs + Metrics + Traces)

- **Neden:** `ValidatorAuditLog` doğru başlangıç ama application-wide observability eksik. OpenTelemetry + Prometheus + Loki tercih edilebilir.
- **Zorluk:** Orta-Yüksek
- **Kategori:** 🔴 Production Critical

#### P4 — LLM Cost & Latency Tracking

- **Neden:** Gemini ve HuggingFace çağrıları için per-request token sayımı + USD tracking yok. Eğitim kurumunda budget kontrolü zorunlu.
- **Zorluk:** Düşük
- **Kategori:** 🔴 Production Critical

#### P5 — Secrets Management (Vault / AWS Secrets Manager)

- **Neden:** `.env` üretim için yetersiz; key rotation süreci yok.
- **Zorluk:** Orta
- **Kategori:** 🔴 Production Critical

#### P6 — Multi-tenancy (Multi-University Support)

- **Neden:** İleride birden fazla diş fakültesi sisteme bağlanabilir. Şu an `User.user_id` global; tenant scoping yok.
- **Zorluk:** Yüksek (yeni tenant_id her tabloya)
- **Kategori:** 🔵 Future Vision

#### P7 — LMS Integration (LTI 1.3 / Moodle / Canvas)

- **Neden:** Eğitim sistemine entegre olmadan kurumlar zor benimser.
- **Zorluk:** Orta
- **Kategori:** 🔵 Future Vision

#### P8 — Frontend State Management Modernization

- **Neden:** `lib/api.ts` doğrudan fetch + AuthContext. React Query / SWR yok. Cache invalidation manuel.
- **Zorluk:** Orta
- **Kategori:** 🟢 High Impact / Low Effort

#### P9 — Container Orchestration (K8s veya en azından docker-compose prod hardening)

- **Neden:** `docker-compose.prod.yml` var ama scale + rolling update yok.
- **Zorluk:** Yüksek
- **Kategori:** 🔵 Future Vision

#### P10 — Disaster Recovery & Backup Strategy

- **Neden:** SQLite dosyası corrupt olursa: yok. Postgres'e geçince WAL archive + scheduled snapshot + restore drill gerekli.
- **Zorluk:** Orta
- **Kategori:** 🔴 Production Critical

---

### B.5 Explainability & AI Trust

#### X1 — Per-Decision LLM Audit Trail

- **Konsept:** Her AI scoring kararının prompt + response + model_id + temperature + token usage saklanır.
- **Neden önemli:** EU AI Act eğitim sistemlerini "high-risk" kategoride sayar — audit trail zorunlu olacak.
- **Mimari etkisi:** Yeni `LLMInteractionLog` (mevcut `ValidatorAuditLog` yetersiz — sadece chat validator için)
- **Kategori:** 🔴 Production Critical + 🟣 Research Critical

#### X2 — Student-Facing "Why this score?" Explainability

- **Konsept:** Öğrenci puanına tıklayınca → hangi rubrik kriterleri karşılandı/karşılanmadı + AI rationale + rubric_version_id görür.
- **Backend büyük ölçüde hazır** (`ai_score_rationale`, `rubric_version_snapshot`). Sadece UI gerekli.
- **Kategori:** 🟢 High Impact / Low Effort

#### X3 — Faculty Calibration Tool

- **Konsept:** Eğitmenin verdiği puanlar AI'dan ne kadar sapıyor — bias dashboard ve "lenient vs strict" göstergesi.
- **Kategori:** 🟡 Mid-term

---

### B.6 Faculty / Instructor Tooling Eksikleri

| Eksik | Etki | Öncelik |
|-------|------|---------|
| **Eğitmen onboarding rehberi (in-app tour)** | Yeni hocaları sisteme alma sürtünmesi | Orta |
| **Sınıf bazlı kohort yönetimi** | Şu an tek bir global kullanıcı havuzu var; "Grup 2025-A" gibi yapı yok | Yüksek |
| **Rubric drafting collaboration (commenting)** | Birden fazla eğitmen aynı rubriği tartışamıyor | Orta |
| **Konu bazlı master question pool + kalite skoru** | Hangi sorular işe yarıyor görünmüyor (IRT entegrasyonu çözer) | Yüksek |
| **Eğitmen analytics: "benim öğrencilerim vs platform ortalaması"** | Yarışmacı motivasyon | Orta |
| **Question difficulty re-calibration suggestion** | "Bu soru çok kolay, %95 doğru" gibi sinyaller | Orta |
| **Live exam proctoring telemetri** | Sınav modunda tab değiştirme/copy-paste deteksiyonu | Orta-Yüksek (kötü kullanım riski var) |

---

### B.7 Adaptive Learning Fırsatları

#### AL1 — Adaptive Difficulty Progression

- **Konsept:** Öğrenci %80 üstü performans gösterirse otomatik daha zor soru; %50 altı performans gösterirse daha kolay.
- **Bağımlılık:** F2 (IRT) ve F1 (BKT) önce yapılmalı.
- **Kategori:** 🔵 Future Vision

#### AL2 — Personalized Case Recommendation v2

- **Konsept:** Mevcut `recommendations.py` rule-based (`v1_competency_based`). Üzerine collaborative filtering + content embedding eklenir.
- **Kategori:** 🟡 Mid-term

#### AL3 — Just-in-Time Knowledge Reinforcement

- **Konsept:** Öğrenci vakada bir aksiyondan başarısız olduğunda, *o spesifik konunun* mini-açıklaması popup olarak çıkar.
- **Mimari:** Question-Case Mapping zaten var; UI eklemesi yeterli.
- **Kategori:** 🟢 High Impact / Low Effort

#### AL4 — Curriculum-Aware Pacing

- **Konsept:** Sınav takvimine (T-8A) göre, sınav öncesi haftalarda intensive review modu aç.
- **Kategori:** 🟡 Mid-term

---

## C. SPRINT 9+ YOL HARİTASI

### Sprint 9 — "Production Foundations" (2 hafta)

**Tema:** Sistemi gerçek kullanıcılara güvenle açabilir hale getirmek.

| Görev | Kategori | Tahmin |
|-------|----------|--------|
| **S9-A** Postgres'e tam geçiş + production migration test | Production Critical | 3 gün |
| **S9-B** Background job queue (arq veya RQ — sade) — AI scoring, snapshot, recommendation refresh | Production Critical | 3 gün |
| **S9-C** LLM cost & latency tracker (`LLMInteractionLog` tablosu + middleware) | Production Critical | 2 gün |
| **S9-D** `app/constants.py` refaktörü + env-driven konfigürasyon | Tech Debt | 0.5 gün |
| **S9-E** GitHub Actions CI/CD (pytest + tsc + coverage report) | Production Critical | 1 gün |
| **S9-F** Frontend test altyapısı kurulumu (Vitest + RTL, 5 smoke test) | High Impact / Low Effort | 1.5 gün |
| **S9-G** Secrets management taşıması (.env → Vault/SSM) | Production Critical | 1.5 gün |
| **S9-H** Disaster recovery: Postgres backup + restore drill | Production Critical | 1 gün |
| **S9-I** `_STUDENT_STATES` in-memory dict → Redis/DB-backed session store (horizontal scale hazırlığı) | Production Critical | 2 gün |
| **S9-J** Global `agent` singleton (`chat.py`) → per-request instantiation refaktörü | Production Critical | 1 gün |

---

### Sprint 10 — "Pedagogical Depth" (2 hafta)

**Tema:** Yüzeysel doğruluk metriğinden çıkıp gerçek öğrenme analitiğine geçiş.

| Görev | Kategori | Tahmin |
|-------|----------|--------|
| **S10-A** Just-in-Time Knowledge Reinforcement popup (Question-Case Mapping kullanır) | High Impact / Low Effort | 2 gün |
| **S10-B** Student-facing "Why this score?" explainability paneli | High Impact / Low Effort | 1.5 gün |
| **S10-C** Spaced Repetition Scheduler (FSRS entegrasyonu, daily job) | High Impact / Low Effort | 3 gün |
| **S10-D** Cognitive Load Profiling — derived analytics + dashboard | High Impact / Low Effort | 2 gün |
| **S10-E** Safety-Critical Action Reaction Time Metric | High Impact / Low Effort | 1 gün |
| **S10-F** Diagnostic Reasoning Process Trace visualization (instructor view) | Research-grade | 2 gün |

---

### Sprint 11 — "Research Infrastructure" (3 hafta)

**Tema:** Yayın yapılabilir bir sistem altyapısı kurmak.

> **Not:** A/B Testing Framework bu sprint'e alındı (önceki Mid-term M1). Veri toplanmaya başlamadan önce randomizasyon altyapısı kurulmazsa, toplanan verinin kontrollü olmadığı gerekçesiyle yayında kullanılması mümkün olmaz.

| Görev | Kategori | Tahmin |
|-------|----------|--------|
| **S11-A** Reproducible Research Snapshot System | Research Critical | 3 gün |
| **S11-B** Inter-Rater Reliability Analytics (Cohen's Kappa, ICC) — T-8C üzerine | Research Critical | 2.5 gün |
| **S11-C** Anonymization & Export Pipeline (PII strip + k-anonymity) | Research Critical | 3 gün |
| **S11-D** Per-Decision LLM Audit Trail (full request/response log) | Research + Production | 2 gün |
| **S11-E** Longitudinal Learning Trajectory tracking (weekly snapshots) | Research Critical | 2 gün |
| **S11-F** A/B Testing Framework — cohort split + outcome ölçümü + istatistiksel anlamlılık (`Experiment`, `ExperimentArm`, `UserExperimentAssignment` tabloları + feature flag service) | Research Critical | 4 gün |

---

### Sprint 12 — "Faculty Empowerment" (2 hafta)

**Tema:** Eğitmen kullanıcı deneyimini sıçramayla iyileştirmek.

| Görev | Kategori | Tahmin |
|-------|----------|--------|
| **S12-A** Kohort/sınıf yönetimi (`Cohort` model + assignment) | Yüksek | 3 gün |
| **S12-B** Eğitmen analytics dashboard — "benim öğrencilerim vs ortalama" | Orta-Yüksek | 2 gün |
| **S12-C** Faculty Calibration Tool (AI vs human bias chart) | Orta-Yüksek | 2 gün |
| **S12-D** Eğitmen onboarding tour (intro.js veya benzeri) | Orta | 1.5 gün |
| **S12-E** Rubric drafting collaboration (inline yorumlar) | Orta | 2 gün |
| **S12-F** Question quality dashboard (kullanım, doğruluk, AI-vs-human delta) | Yüksek | 1.5 gün |

---

### Sprint 13 — "Adaptive Intelligence" (3 hafta)

**Tema:** Sıradan bir LMS'ten "intelligent tutoring system"e geçiş.

> **Gate Condition:** S13-A (IRT) ve S13-B (BKT) yalnızca her soru için ≥200 öğrenci cevabı biriktiğinde istatistiksel olarak anlamlıdır. Bu eşiğe ulaşılmadan sprint başlatılırsa kalibrasyon mock/yetersiz veriye oturur ve yayın değeri taşımaz. Sprint başlangıcından önce veri yeterliliği `SELECT question_id, COUNT(*) FROM student_answers GROUP BY question_id` sorgusuyla kontrol edilmeli; eşik sağlanmamışsa sprint ertelenip S13-C, S13-D, S13-E önce yapılabilir.

| Görev | Kategori | Tahmin |
|-------|----------|--------|
| **S13-A** IRT calibration pipeline (`py-irt`, nightly batch) | Research Critical | 4 gün |
| **S13-B** Bayesian Knowledge Tracing (BKT) v1 | Research Critical | 5 gün |
| **S13-C** Adaptive difficulty progression (BKT + IRT input) | Future Vision | 3 gün |
| **S13-D** Personalized recommendation engine v2 (content embedding) | Mid-term | 4 gün |
| **S13-E** Just-in-time curriculum-aware pacing | Mid-term | 2 gün |

---

## D. MID-TERM ROADMAP (6–12 ay)

### ~~M1 — A/B Testing & Pedagogical Experiments Framework~~ → Sprint 11'e (S11-F) alındı

*Cohort split + outcome ölçümü + istatistiksel anlamlılık, veri toplanmaya başlamadan önce kurulması gerektiğinden Mid-term'den çıkarılıp Sprint 11'e taşındı.*

### M2 — Script Concordance Test Modülü

**Süre:** 2 hafta
**Çıktı:** Yeni soru tipi + uzman panel referans değerleri + scoring + dashboard.

### M3 — Live Exam Proctoring Module

**Süre:** 2.5 hafta
**Çıktı:** Sınav modunda tab-change deteksiyonu, copy-paste deteksiyonu, focus loss telemetry, instructor live view. (Etik komite ön onayı şart.)

### M4 — Observability Stack (OpenTelemetry + Grafana)

**Süre:** 2 hafta
**Çıktı:** End-to-end tracing, error rate alerting, SLO definitions.

### M5 — Mobile-First PWA

**Süre:** 3 hafta
**Çıktı:** Spaced repetition + push notifications + offline mode (sorular cache'lenir, online olunca sync olur).

### M6 — Bayesian Differential Diagnosis Coach (vaka simülasyonunda olasılık güncelleme)

**Süre:** 3 hafta
**Çıktı:** Vakada her bulgu sonrası AI tarafından hesaplanan tanı olasılıkları + öğrencinin kendi tahmini ile karşılaştırma.

---

## E. LONG-TERM ROADMAP (12–24 ay)

### L1 — Multimodal Lesion Recognition (Image + Text)

**Süre:** 4 ay
**Bağımlılıklar:** Lisanslı görsel veri seti, vision LLM seçimi (MedGemma 4B vision variant?), S3, image-aware Question subtype.
**Yayın değeri:** Multimodal medical AI yayını (üst düzey).

### L2 — Multi-Tenancy (Multi-University Platform)

**Süre:** 3 ay
**Bağımlılıklar:** Tenant scoping schema migration, billing, white-labeling.

### L3 — LMS Integration Suite (LTI 1.3, Moodle plugin, Canvas plugin)

**Süre:** 2 ay
**Stratejik etki:** Kurumsal benimseme hızını 5-10x artırır.

### L4 — Open Dataset Release & Public Benchmark

**Süre:** 6 ay (etik onay + anonymization audit + publication paralel)
**Yayın değeri:** Citation impact'ı en yüksek aksiyon.

### L5 — Generative Case Authoring (LLM-assisted)

**Süre:** 4 ay
**Konsept:** Eğitmen "olp_002 gibi ama farklı klinik bulgular" der → LLM yeni vaka draft'ı üretir → eğitmen düzenler. Content production bottleneck'ini çözer.

### L6 — Other Specialty Expansion (Endodonti, Periodontoloji ayrı modüller)

**Süre:** 6+ ay
**Bağımlılık:** Oral Pathology MVP validasyonu + multi-tenancy.

### L7 — Konuşma Tabanlı Hasta Görüşmesi (Voice Interaction)

**Süre:** 3-4 ay
**Konsept:** Öğrenci hastaya gerçek sesle soru sorar (TTS/STT loop). Hasta empati, anksiyete, evasiveness sergileyen sesli AI.
**Yayın değeri:** Çok yüksek — communication skill assessment yeni jenerasyon ölçümü.

---

## F. ÖNCELİK MATRİSİ (KATEGORİ BAZINDA)

### 🟢 HIGH IMPACT / LOW EFFORT (Hemen yap)

1. Just-in-Time Knowledge Reinforcement popup (S10-A)
2. Student-facing "Why this score?" UI (S10-B)
3. Spaced Repetition Scheduler (S10-C)
4. Cognitive Load Profiling derived analytics (S10-D)
5. Safety-Critical Reaction Time Metric (S10-E)
6. Frontend state management (React Query) (P8)
7. `app/constants.py` refaktörü (S9-D)
8. Frontend test altyapısı (S9-F)

### 🟣 RESEARCH CRITICAL (Yayın yapmadan önce)

1. Reproducible Research Snapshot System (S11-A) — **birinci öncelik**
2. Inter-Rater Reliability Analytics (S11-B)
3. Per-Decision LLM Audit Trail (S11-D)
4. Anonymization & Export Pipeline (S11-C)
5. A/B Testing Framework (S11-F) ← Mid-term M1'den taşındı
6. Longitudinal Learning Trajectory (S11-E)
7. IRT Calibration (S13-A)
8. Bayesian Knowledge Tracing (S13-B)
9. Script Concordance Test (M2)

### 🔴 PRODUCTION CRITICAL (Production'a çıkmadan önce)

1. Postgres tam geçiş (S9-A)
2. Background job queue (S9-B)
3. LLM cost & latency tracker (S9-C)
4. CI/CD pipeline (S9-E)
5. Secrets management (S9-G)
6. Disaster recovery + backup (S9-H)
7. Observability stack (M4)
8. AI scoring rate limiting (Sprint 6 T-6D — hâlâ borç)

### 🔵 FUTURE VISION (12-24 ay)

1. Multimodal lesion recognition (L1)
2. Multi-tenancy (L2)
3. LMS integration suite (L3)
4. Open dataset release (L4)
5. Generative case authoring (L5)
6. Voice interaction (L7)
7. Adaptive difficulty progression (S13-C, bağımlı)
8. Bayesian Differential Diagnosis Coach (M6)

---

## G. ZIMNI EKSİKLER VE KÖR NOKTALAR

Mevcut planda görünmeyen ama uzun vadede bloklayıcı olabilecek konular:

1. **Etik kurul (IRB) süreci başlatılmadı** — herhangi bir akademik yayın için zorunlu; data collection yapılırken retroactive zor olur.
2. **GDPR/KVKK uyumluluk denetimi yapılmadı** — öğrenci verisi tutuyoruz, audit gerekli.
3. **Öğrenci consent flow'u yok** — kayıt sırasında "verilerim araştırmada kullanılabilir" onayı UI'da yok.
4. **AI bias auditi yapılmadı** — özellikle dil (TR vs EN), öğrenci sosyoekonomik profili açısından AI scoring bias testi gerekli (Wiley/JDE bunu sorar).
5. **Accessibility (WCAG 2.1 AA)** — Frontend için audit yapılmadı; renk körlüğü, ekran okuyucu uyumu kontrol edilmeli.
6. **Pedagojik validasyon eksik** — Sistemin gerçekten öğrenmeyi iyileştirip iyileştirmediğine dair *pre-test / post-test* tasarımı yok. Bu olmadan "iyileştirir" iddiası destekli değil.
7. **Faculty training material** — Eğitmen dokümantasyonu eksik; kullanım rehberi yok.
8. **Student feedback loop kapalı** — `FeedbackLog` var ama bu veri kararlara nasıl döner — süreç tanımsız.
9. **Versioning of clinical content** — Rubrik versiyonlama var ama vaka senaryosu (`CaseDefinition`) için `CasePublishHistory` var. Bu güzel — ancak scoring_rules JSON fallback hâlâ tehlike.
10. **No real-world dental expert sign-off** — Klinik içeriği onaylayan akredite uzman listesi tutulmuyor (yayında "validated by N experts" demek için gerekli).

---

## H. ÖNERİLEN İLK 3 AKSİYON (Eğer yarın başlanacaksa)

1. **Sprint 9'u başlat** — Production foundations olmadan kullanıcı sayısı artamaz, araştırma için veri toplanamaz. Postgres + queue + observability bu sprint'in omurgası.
2. **Sprint 11'i paralel başlat (eğer ekip varsa)** — Research infrastructure (snapshot system + audit trail + anonymization) yayın hattını açar; geç başlanırsa retroactive yapması zor.
3. **Klinik ekiple bir "academic publication roadmap" toplantısı yap** — Hedef dergi (JDE, EJDE, Wiley) + study design (RCT mi feasibility mi) + IRB başvuru zamanlaması netleştir. Bu kararlar tüm Sprint 10–13 önceliğini etkiler.

---

## I. SONUÇ VE STRATEJİK POZİSYON

DentAI şu anda **çok güçlü bir teknik temele** sahip:

- Hybrid AI mimari (LLM + rule engine) çoğu LMS'in çok ötesinde
- Reasoning pattern classifier ve rubric versioning **araştırma kalitesinde** özellikler
- 233+ test, role-based güvenlik, prompt injection deteksiyonu — production'a *neredeyse* hazır

Ancak **yayınlanabilir araştırma** ve **gerçek production deployment** arasında 3 stratejik gap var:

1. **Production foundations (Sprint 9):** Postgres, queue, observability, CI, secrets — *3-4 hafta iş*.
2. **Research infrastructure (Sprint 11):** Reproducible snapshot, anonymization, audit trail, A/B test — *3-4 hafta iş*.
3. **Pedagojik validasyon altyapısı (M1 + IRB):** Olmadan "öğrenmeyi iyileştiriyor" iddiası desteklenemez — *6-8 hafta iş + paralel etik onay süreci*.

**En büyük rekabet avantajı potansiyeli:** Reasoning Pattern Classifier + Rubric Versioning + IRT/BKT entegrasyonu — bu üçlü, "intelligent tutoring system" iddiasını sağlam matematiksel-pedagojik temele oturtur ve **Wiley/JDE seviyesinde yayın** yapmaya açar.

---

*DentAI Stratejik Analiz Raporu — Hazırlayan: Claude (Opus 4.7) — 2026-05-27*
*Sonraki adım: Sprint 9 detaylı görev kırılımı için onay bekleniyor.*
