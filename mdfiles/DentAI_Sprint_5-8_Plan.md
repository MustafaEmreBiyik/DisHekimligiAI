# DentAI — Sprint 5–8 Planı

**Hazırlanma tarihi:** 2026-05-24  
**Başlangıç durumu:** Sprint 0–4 tamamlandı (22/23 görev ✅). Tek açık kalem: Sprint 3 mini-vaka seti (klinik ekip kararı bekliyor).  
**Takip belgesi:** `DentAI_Sprint_Audit_Report.md`

---

## Mevcut Durum Özeti

| Sprint | Durum | Notlar |
|--------|-------|--------|
| 0 — Veri Modeli & Altyapı | ✅ Tamamlandı | Tüm DB modelleri, auth, rol sistemi |
| 1 — Soru Bankası & Öğrenci UI | ✅ Tamamlandı | MCQ + OE soru ekleme, öğrenci quiz akışı |
| 2 — Puanlama & Raporlama | ✅ Tamamlandı | Kompozit skor, zayıf konu raporu |
| 3 — Vaka Eşleme & Rubrik | ✅ Tamamlandı | Mapping API + UI, vaka rubrik servisi |
| 3 — Mini-vaka seti | ⚠️ Bekliyor | Klinik ekip formatı tanımlamalı |
| 4 — AI Puanlama & Versiyonlama | ✅ Tamamlandı | Gemma-2-9B AI scoring, rubrik versiyonlama |

**Backend birim testi toplamı (Sprint 0–4):** 233+ test, tamamı geçiyor ✅  
**TypeScript derleyici:** 0 hata ✅

---

## Sprint 5 — İçerik & Soru Bankası Dolumu

**Hedef:** Platformu gerçek klinik içerikle doldurmak; eğitmenlerin toplu içerik girebilmesini sağlamak.  
**Tahmini süre:** 2 hafta  
**Öncelik:** 🔴 Kritik — Öğrenciler soru görmeden sistemi test edemez.

### T-5A — OE Soru Bankası Import Scripti

**Açıklama:**  
`scripts/import_questions.py` adında bir CLI scripti yaz. Eğitmen, hazırladığı JSON veya CSV dosyasını bu script üzerinden veritabanına toplu olarak aktarabilir.

**Gereksinimler:**
- Girdi formatı: `data/sample_questions.json` (zaten `QUESTION_STORAGE_GUIDE.md`'de tanımlı)
- `question_id` çakışmasında `--upsert` flag'i ile güncelleme, yoksa hata ver
- Dry-run modu: `--dry-run` ile içe aktarmadan önce doğrulama raporu göster
- Çıktı: kaç soru eklendi / güncellendi / atlandı / hata verdi

**Dosyalar:**
- `backend/scripts/import_questions.py` (yeni)
- `backend/data/sample_oe_questions.json` (10 örnek OE soru içeren seed dosyası)
- `backend/tests/unit/test_import_script.py` (5+ test)

**Kabul kriteri:** `python scripts/import_questions.py --file data/sample_oe_questions.json` başarıyla çalışır, DB'de sorular görünür.

---

### T-5B — Mini-Vaka Formatı Tanımla & 6 Vaka Gir

**Açıklama:**  
Mevcut `case_scenarios.json` tam simülasyon vakalarını içeriyor; Sprint 3'te kalan gereksinim bunlar değil. Klinik ekiple "mini-vaka" (lightweight, teori-bağlantılı) formatını belirle ve 6 vaka JSON olarak gir.

**Mini-vaka JSON şeması:**
```json
{
  "mini_case_id": "mc_oral_lichen_001",
  "linked_topic_ids": ["oral_lichen_planus"],
  "title": "string",
  "clinical_vignette": "string (2-3 cümle klinik hikaye)",
  "key_findings": ["string"],
  "question_ids": ["Q-OLP-001", "Q-OLP-002"],
  "learning_objectives": ["string"],
  "difficulty": "easy|medium|hard"
}
```

**Hedef vakalar:** oral_lichen_planus, herpes_simplex, behcet, pemphigus_vulgaris, erythema_multiforme, geographic_tongue

**Dosyalar:**
- `backend/data/mini_cases.json` (yeni, 6 vaka)
- `backend/app/services/mini_case_service.py` (yeni, `get_mini_case()`, `list_mini_cases()`)
- `backend/app/api/routers/mini_cases.py` (yeni, `GET /api/mini-cases`, `GET /api/mini-cases/{id}`)
- `frontend/app/instructor/mini-cases/page.tsx` (eğitmen listesi)
- `frontend/app/student/mini-cases/page.tsx` (öğrenci görünümü — teori vakasına bak, ilgili sorulara git)

**Kabul kriteri:** Öğrenci mini-vakaya tıklayınca klinik vignette + ilgili quiz sorularına link görür.

---

### T-5C — Eğitmen: Toplu Soru İşlemleri UI

**Açıklama:**  
`/instructor/questions` sayfasına çoklu seçim ve toplu işlem (bulk action) desteği ekle.

**Özellikler:**
- Checkbox ile çoklu soru seçimi
- Seçili soruları toplu arşivle / aktif yap
- Seçili soruların `unit_id` veya `week_number`'ını toplu güncelle
- CSV export: seçili soruları CSV olarak indir

**Dosyalar:**
- `frontend/app/instructor/questions/page.tsx` (mevcut, genişlet)
- `backend/app/api/routers/quiz.py` — `PATCH /api/quiz/instructor/questions/bulk` endpoint (yeni)

**Kabul kriteri:** 5 soru seç → "Toplu Arşivle" butonu tıkla → 5 soru arşivlendi.

---

### T-5D — Öğrenci: Quiz Geçmişi & Detay Sayfası

**Açıklama:**  
Öğrenci kendi eski denemelerini görebilmeli: hangi sorulara ne cevap verdi, puanları neydi, geri bildirim neydi.

**Dosyalar:**
- `backend/app/api/routers/quiz.py` — `GET /api/quiz/my-attempts` (deneme listesi), `GET /api/quiz/my-attempts/{attempt_id}` (detay)
- `frontend/app/student/history/page.tsx` (yeni — deneme listesi + her denemedeki sorular ve puanlar)

**Kabul kriteri:** Öğrenci "Geçmişim" sayfasında tüm eski denemelerini görür ve her birinin üzerine tıklayınca detaylı yanıt listesini görür.

---

## Sprint 6 — Teknik Borç & Altyapı

**Hedef:** Kod kalitesini iyileştir, hardcoded değerleri yönetilebilir hale getir, admin panel ekle.  
**Tahmini süre:** 1.5 hafta  
**Öncelik:** 🟡 Yüksek — Teknik borcun birikmesi ilerideki sprintleri yavaşlatır.

### T-6A — Ortak Sabitler Modülü (`app/constants.py`)

**Açıklama:**  
Şu anda `topic_accuracy_service.py` ve `quiz.py`'de aynı `_TOPIC_LABELS` sözlüğü tekrarlı var. Ek olarak `_WEAK_THRESHOLD_PCT = 60.0` ve kompozit ağırlıklar (`MCQ: 0.35`, `OE: 0.40`, `Case: 0.25`) hardcoded.

**Yapılacaklar:**
- `backend/app/constants.py` oluştur:
  ```python
  TOPIC_LABELS: dict[str, str] = { ... }
  WEAK_THRESHOLD_PCT: float = float(os.getenv("DENTAI_WEAK_THRESHOLD", "60"))
  COMPOSITE_WEIGHTS = {"mcq": 0.35, "oe": 0.40, "case": 0.25}
  ```
- `topic_accuracy_service.py` ve `quiz.py` import etsin
- `.env` dosyasına `DENTAI_WEAK_THRESHOLD` örnek ekle

**Kabul kriteri:** `_TOPIC_LABELS` sadece bir yerde tanımlı; `DENTAI_WEAK_THRESHOLD=70` env değişkeniyle eşik değiştirilebiliyor.

---

### T-6B — Admin Panel: Kullanıcı Yönetimi

**Açıklama:**  
Admin rolündeki kullanıcıların sistemi yönetmesi için temel bir panel.

**Backend:**
- `GET /api/admin/users` — tüm kullanıcıları listele (sayfalama ile)
- `PATCH /api/admin/users/{user_id}/role` — rol değiştir (student → instructor vb.)
- `DELETE /api/admin/users/{user_id}` — soft delete (is_archived=True)
- `GET /api/admin/stats` — genel istatistikler (toplam kullanıcı, soru sayısı, deneme sayısı)

**Frontend:**
- `frontend/app/admin/users/page.tsx` (yeni)
- `frontend/app/admin/stats/page.tsx` (yeni)
- `frontend/components/admin/AdminRouteGuard.tsx` (yeni)

**Kabul kriteri:** Admin kullanıcısı sisteme giriş yapıp tüm kullanıcıları görebilir, birinin rolünü değiştirebilir.

---

### T-6C — Eğitmen: Soru CSV/JSON Import UI

**Açıklama:**  
T-5A'daki CLI scriptinin frontend karşılığı. Eğitmen doğrudan arayüzden CSV veya JSON dosyası yükleyebilir.

**Dosyalar:**
- `frontend/app/instructor/import/page.tsx` (yeni — file upload + önizleme tablosu + import butonu)
- `backend/app/api/routers/quiz.py` — `POST /api/quiz/instructor/import` (multipart JSON/CSV kabul eder)

**Kabul kriteri:** Eğitmen 20 soruluk JSON dosyası yükler → önizleme tablosunda görür → "İçe Aktar" butonuyla DB'ye kaydeder.

---

### T-6D — AI Scoring Rate Limiting & Hata İzleme

**Açıklama:**  
`POST /api/quiz/instructor/answers/{id}/ai-score` endpoint'i ücretsiz HuggingFace API limitine takılabilir. Basit bir retry + cooldown mekanizması ekle, ayrıca AI skorlama hatalarını bir log tablosuna kaydet.

**Dosyalar:**
- `backend/app/services/oe_scoring_service.py` — exponential backoff retry (3 deneme)
- `backend/db/database.py` — `AIScoringLog` tablosu (answer_id, model_id, status, error_message, latency_ms)
- `backend/alembic/versions/...` — migration

**Kabul kriteri:** HuggingFace API meşgulse 3 kez yeniden dener; başarısız olursa `AIScoringLog`'a hata yazar.

---

### T-6E — Test Altyapısı İyileştirme

**Açıklama:**
- `pytest_composite.ini` dosyasını temizle (tek `pyproject.toml` kullan)
- `conftest.py`'e `InMemoryDB` fixture'ı taşı (tekrar eden `create_engine` bloklarını ortadan kaldır)
- GitHub Actions (veya benzeri CI) için `.github/workflows/test.yml` ekle

**Kabul kriteri:** `python -m pytest` tek komutla tüm testleri çalıştırıyor; CI config dosyası var.

---

## Sprint 7 — Bildirim & Raporlama

**Hedef:** Öğrenciler puanları hakkında bildirim alır; eğitmenler sınıf raporları alır.  
**Tahmini süre:** 2 hafta  
**Öncelik:** 🟡 Yüksek — Öğrenci tutundurması için kritik.

### T-7A — Puan Yayınlanma Bildirimleri

**Açıklama:**  
Bir eğitmen OE cevabını "Yayınla" butonuyla yayınladığında öğrenci bunu görmeli.

**Backend:**
- `backend/db/database.py` — `Notification` tablosu (user_id, type, payload_json, is_read, created_at)
- `backend/app/api/routers/quiz.py` — grade submit sırasında bildirim oluştur
- `GET /api/notifications` — okunmamış bildirimler
- `PATCH /api/notifications/{id}/read` — okundu olarak işaretle

**Frontend:**
- Header'a bildirim zili ikonu + badge (okunmamış sayısı)
- `frontend/app/student/notifications/page.tsx` (yeni — bildirim listesi)
- Öğrenci paneli: "Son Bildirimler" widget'ı

**Kabul kriteri:** Eğitmen puanı yayınlar → öğrenci zil ikonunda badge görür → bildirime tıklayınca hangi soruya ne puan verildiğini görür.

---

### T-7B — Eğitmen: Sınıf Puan Raporu Export

**Açıklama:**  
Eğitmen tüm öğrencilerin puanlarını Excel/CSV olarak indirebilmeli.

**Backend:**
- `GET /api/quiz/instructor/grade-report?format=csv` (veya `xlsx`)
- Kolonlar: öğrenci adı, user_id, konu bazlı doğruluk oranları, AI skor ortalaması, final skor

**Frontend:**
- `/instructor/grading` sayfasına "Rapor İndir" butonu

**Kütüphane:** `openpyxl` (zaten `backend` bağımlılıklarında mevcut mu kontrol et; yoksa ekle)

**Kabul kriteri:** Eğitmen "Rapor İndir" → tarayıcı `.xlsx` indirir; 10+ öğrenci satırı içerir.

---

### T-7C — Öğrenci: Kişisel Puan Raporu PDF

**Açıklama:**  
Öğrenci kendi performans raporunu PDF olarak indirebilir.

**Backend:**
- `GET /api/quiz/my-report?format=pdf` — kompozit skor + konu doğruluğu + güçlü/zayıf alanlar

**Frontend:**
- `/student/statistics` sayfasına "PDF İndir" butonu
- PDF içeriği: kişisel özet, radar grafiği placeholder, konu bazlı çubuk grafik

**Kabul kriteri:** Öğrenci "PDF İndir" → `.pdf` dosyası tarayıcıda açılır.

---

### T-7D — Eğitmen: Soru Bazlı İstatistik Dashboard

**Açıklama:**  
Hangi soruyu kaç kişi doğru yaptı? Hangi soruların AI skoru ile hoca skoru en fazla ayrışıyor?

**Backend:**
- `GET /api/quiz/instructor/question-stats` — her soru için doğru/yanlış oranı, AI vs hoca skor delta
- `GET /api/quiz/instructor/ai-vs-human-delta` — en yüksek delta'lı top-10 soru

**Frontend:**
- `frontend/app/instructor/question-stats/page.tsx` (yeni — soru listesi, her birinin yanında doğru% bar)
- AI vs hoca delta tablosu

**Kabul kriteri:** Eğitmen en sık yanlış yapılan 5 soruyu görebilir.

---

## Sprint 8 — Sınav Takvimi & İleri Özellikler

**Hedef:** Zamanlanmış sınavlar, süre kısıtı, çoklu hoca desteği.  
**Tahmini süre:** 2.5 hafta  
**Öncelik:** 🟢 Orta — Sprint 5–7 tamamlandıktan sonra.

### T-8A — Sınav Takvimi: `ExamSchedule` Tablosu

**Açıklama:**  
Eğitmen belirli sorulardan oluşan bir sınav paketini belirli tarih-saat aralığında açabilsin.

**DB şeması:**
```
ExamSchedule
  id            Integer PK
  title         String
  question_ids  JSON     (sınavdaki soru ID listesi)
  opens_at      DateTime
  closes_at     DateTime
  time_limit_minutes  Integer nullable
  created_by    String
  is_active     Boolean
```

**Backend:**
- `POST /api/quiz/instructor/exam-schedules` — sınav oluştur
- `GET /api/quiz/exam-schedules` — öğrenciye açık sınavları listele (zaman filtreli)
- `GET /api/quiz/instructor/exam-schedules` — tüm sınavlar (eğitmen görünümü)

**Kabul kriteri:** Eğitmen "Final Sınavı" paketi oluşturur, 1 hafta sonra öğrencilere açılır.

---

### T-8B — Sınav Süre Kısıtı & Otomatik Gönderim

**Açıklama:**  
`ExamSchedule.time_limit_minutes` varsa öğrenci sınav başlatınca geri sayım başlar; süre dolunca otomatik gönderilir.

**Frontend:**
- `frontend/app/student/exam/[scheduleId]/page.tsx` (yeni — countdown timer + otomatik submit)
- `QuizAttempt` modeline `time_limit_expires_at` alanı eklenir

**Backend:**
- Submit endpoint'e süre aşımı kontrolü ekle: eğer `now > time_limit_expires_at` ise cevapları olduğu gibi kaydet, uyarı döndür

**Kabul kriteri:** 10 dakikalık sınav başlar → 10 dakika sonra otomatik gönderilir.

---

### T-8C — Çoklu Hoca Puanlama (Inter-Rater)

**Açıklama:**  
Bir OE cevabı birden fazla hoca tarafından puanlanabilir; final puan ortalama veya birinci hocanın puanı olabilir.

**DB değişikliği:**
```
QuizAnswer
  secondary_instructor_score    Float nullable
  secondary_instructor_id       String nullable
  secondary_graded_at           DateTime nullable
  inter_rater_delta             Float nullable  (otomatik hesaplanan |score1 - score2|)
```

**Backend:**
- `POST /api/quiz/instructor/answers/{id}/secondary-grade` endpoint
- `GET /api/quiz/instructor/high-delta-answers` — yüksek delta'lı cevaplar (tartışma gerektiren)

**Frontend:**
- Grading UI'a "İkinci Değerlendirme" modu

**Kabul kriteri:** İki farklı hoca aynı cevabı puanlar; delta 2 puanı aşarsa liste üst sıraya çıkar.

---

### T-8D — Öğrenci: Takvim Görünümü

**Açıklama:**  
Öğrenci hangi sınavın ne zaman açılıp kapandığını görebilir.

**Frontend:**
- `frontend/app/student/calendar/page.tsx` (yeni — takvim grid veya timeline)
- Gelecek sınav için geri sayım widget'ı ana sayfada

**Kabul kriteri:** Öğrenci takvim sayfasında önümüzdeki 7 günde açılacak sınavları görür.

---

## Görev Öncelik Matrisi (Tüm Sprintler)

| Görev ID | Başlık | Sprint | Öncelik | Zorunluluk | Tahmini Süre |
|----------|--------|--------|---------|------------|-------------|
| T-5A | OE Soru Import Scripti | 5 | 🔴 Kritik | Platform kullanılabilirliği | 1 gün |
| T-5B | Mini-Vaka Formatı + 6 Vaka | 5 | 🔴 Kritik | Sprint 3 borcu | 2 gün (klinik ekip) |
| T-5C | Toplu Soru İşlem UI | 5 | 🟡 Yüksek | Eğitmen verimliliği | 1 gün |
| T-5D | Öğrenci Quiz Geçmişi | 5 | 🟡 Yüksek | Öğrenci deneyimi | 1 gün |
| T-6A | Ortak Sabitler Modülü | 6 | 🟡 Yüksek | Teknik borç | 0.5 gün |
| T-6B | Admin Panel | 6 | 🟡 Yüksek | Kullanıcı yönetimi | 2 gün |
| T-6C | Import UI | 6 | 🟢 Orta | Eğitmen kolaylığı | 1 gün |
| T-6D | AI Rate Limiting | 6 | 🟡 Yüksek | Üretim güvenilirliği | 1 gün |
| T-6E | Test Altyapısı | 6 | 🟢 Orta | CI/CD | 0.5 gün |
| T-7A | Puan Bildirimleri | 7 | 🟡 Yüksek | Öğrenci tutundurma | 2 gün |
| T-7B | Sınıf Raporu Export | 7 | 🟡 Yüksek | Eğitmen iş akışı | 1 gün |
| T-7C | Öğrenci PDF Raporu | 7 | 🟢 Orta | Öğrenci deneyimi | 1.5 gün |
| T-7D | Soru İstatistik Dashboard | 7 | 🟡 Yüksek | Veri odaklı içerik | 1.5 gün |
| T-8A | ExamSchedule Tablosu | 8 | 🟢 Orta | Sınav yönetimi | 1.5 gün |
| T-8B | Süre Kısıtı & Otomatik Submit | 8 | 🟢 Orta | Sınav bütünlüğü | 1 gün |
| T-8C | Çoklu Hoca Puanlama | 8 | 🟢 Orta | Akademik güvenilirlik | 2 gün |
| T-8D | Öğrenci Takvim Görünümü | 8 | 🟢 Orta | UX | 1 gün |

**Toplam tahmini geliştirme süresi:** ~22 geliştirici günü (yaklaşık 5–6 hafta, 1 geliştirici)

---

## Bağımlılık Grafiği

```
T-5A ──┐
T-5B ──┤── Sprint 5 tamamlanır ──► T-6C (Import UI T-5A'ya dayanır)
T-5C ──┤
T-5D ──┘

T-6A ──► T-7B, T-7D (sabitler her ikisinde kullanılır)
T-6B ──► T-8C (admin user management → inter-rater assignment)
T-8A ──► T-8B, T-8D (takvim yoksa süre kısıtı anlamsız)
T-7A ──► T-8A (bildirim altyapısı sınav bildirimleri için de kullanılır)
```

---

## Teknik Borç Özeti (Sprint 6 Öncesi)

| Borç | Etki | Sprint |
|------|------|--------|
| `_TOPIC_LABELS` iki dosyada tekrar ediyor | Yeni konu eklenince iki dosya güncellenmeli | T-6A |
| `_WEAK_THRESHOLD_PCT = 60.0` hardcoded | Admin ayarlayamıyor | T-6A |
| `pytest_composite.ini` kalıntısı | Kafa karışıklığı, olası çakışma | T-6E |
| `open_ended_questions.json` boş | OE soru bankası boş | T-5A + T-5B |
| AI scoring retry yok | HuggingFace meşgulse skor alınamıyor | T-6D |
| Admin paneli yok | Kullanıcı yönetimi manuel DB operasyonu | T-6B |
| `QuizAttempt` üzerinde süre takibi yok | Sınav süresi kontrol edilemiyor | T-8B |

---

## Başarı Kriterleri (Sprint 5–8 Sonu)

| Kriter | Hedef |
|--------|-------|
| OE soru bankası içeriği | ≥ 30 gerçek klinik soru |
| Mini-vaka seti | 6 vaka (tüm hedef hastalıklar için) |
| Öğrenci bildirimi | Puan yayınlanma → 5 dk içinde bildirim |
| Eğitmen raporu | Excel export < 3 saniye (100 öğrenciye kadar) |
| Sınav takvimi | Eğitmen tarihe bağlı sınav açabilir |
| Test kapsamı | Backend birim testi: ≥ 300 test |
| TypeScript | 0 hata (tüm yeni sayfalar dahil) |
| AI scoring güvenilirliği | 3 retry sonrasında hata oranı < %5 |

---

*DentAI Sprint 5–8 Planı — Son güncelleme: 2026-05-24*
