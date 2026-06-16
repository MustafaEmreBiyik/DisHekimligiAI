# DentAI — Gelecek Çalışmalar (Future Work)

> Bu belge teknik sunumun "Gelecek Çalışmalar" slaydı ve jüri soruları için hazırlanmıştır.
> Her madde somut gerekçe, mevcut kısıt ve önerilen yaklaşım içermektedir.

---

## Öncelik 1: ML Modellerinin Olgunlaştırılması

### FW-01 — BKT Parametre Kalibrasyonu (Domain-Spesifik)

**Mevcut Durum:** BKT parametreleri Corbett & Anderson (1995) varsayılan değerleriyle çalışmaktadır:
```
p_init=0.20, p_transit=0.10, p_slip=0.10, p_guess=0.20
```
Bu değerler genel bilişsel alan için önerilmiş; diş hekimliği oral patoloji eğitimi için kalibre edilmemiştir.

**Neden Önemli:** Yanlış P(G) (tahmin olasılığı) değeri, özellikle MCQ sorularında gerçek öğrenmeyi tahmin edemez. Örneğin, 4 seçenekli sorularda P(G) ≥ 0.25 olmalı, ancak varsayılan 0.20'dir.

**Önerilen Yaklaşım:**
- Yeterli öğrenci verisi biriktikten sonra (≥500 gözlem/konu) EM (Expectation-Maximization) algoritması ile parametre optimizasyonu
- `py-irt` (PyTorch/Pyro tabanlı) kütüphanesi zaten `requirements-ml.txt`'de üretim yükseltme yolu olarak not edilmiş
- Per-konu parametreler: bazı konular (antibiyotik seçimi) başka konulara (radyografi yorumu) göre daha yüksek P(S) ile öğrenilir

**Beklenen Etki:** Konu bazlı uzmanlaşma tahmini doğruluğu +15–20%

---

### FW-02 — IRT Gerçek Veri Oranını Artırma

**Mevcut Durum:** `IRT_MIN_SAMPLE = 200` gerçek yanıt gerektiriyor. Sistemin ilk döneminde neredeyse tüm sorular `is_synthetic=True` ile başlıyor. Sentetik parametreler üretim önerilerini doğrudan sürmüyor.

**Önerilen Yaklaşım:**
- Eşiği kademeli indirme: 200 → 100 → 50 (daha fazla öğrenciden veri birikmesiyle)
- Eş zamanlı fit metrikleri izleme: `|Δa| < 0.3`, `|Δb| < 0.3` kurtarma testi
- IRT → BKT bağlantısı: fit edilen `b` değeri, BKT için daha iyi `p_init` prioru sağlar

**3PL Genişlemesi:**
Mevcut şema `guessing_c` alanını içeriyor ama `2PL` kullanılıyor. Yeterli veriye ulaşınca `3PL`'e geçiş:
```
P(correct | θ) = c + (1−c) × σ(a·(θ−b))
```

---

### FW-03 — XGBoost Öneri Motoru Üretim Rollout

**Mevcut Durum:** XGBoost altyapısı (trainer, feature store, ranker) tamamlandı. Ancak gerçek `RecommendationModelVersion` tablosunda `is_active=True` kayıt için yeterli eğitim verisi henüz yok.

**Eğitim Hedefi (Label):** `outcome_score=1` ↔ öğrenci 14 günde tamamladı + ≥%70 skor

**Engel:** Label toplamak için öğrencilerin sistemi kullanmaya devam etmesi gerekiyor.

**Önerilen Yaklaşım:**
```
Faz 1 (Şu an): V1 kural tabanlı + veri toplama
Faz 2 (≥200 tamamlama): İlk XGBoost modeli eğit, A/B testi kur
Faz 3 (≥1000 tamamlama): Tam üretim XGBoost, V1 yalnızca soğuk başlangıç
```

**Değerlendirme Metrikleri Hedefleri:**
- NDCG@5 > 0.70
- Hit-rate@5 > 0.50

---

### FW-04 — SM-2 Ease Faktörü Domain Kalibrasyonu

**Mevcut Durum:** Varsayılan `ease_factor=2.5` (SM-2 orijinal önerisi). Bu değer İngilizce kelime ezberi için optimize edilmiş.

**Hipotez:** Oral patoloji konuları (klinik tanı kriterleri, antibiyotik protokolleri) görsel-bağlamsal hafıza gerektirir; klasik verbal materyal değildir. Ease faktörü daha yavaş atımı tercih edebilir.

**Önerilen Yaklaşım:**
- SM-2 oturumlarından elde edilen recall başarı oranları ile ease faktörü dağılımını analiz et
- Optimal `_MIN_EASE` ve başlangıç ease değerini ampirik olarak belirle

---

## Öncelik 2: AI Bileşen Yükseltmeleri

### FW-05 — Gerçek MedGemma Modeline Geçiş

**Mevcut Durum:** `MedGemmaService`, HuggingFace üzerinden `google/gemma-2-9b-it` kullanıyor — bu medikal verilerle fine-tune edilmiş MedGemma-27B değil, genel amaçlı Gemma-2'nin 9B versiyonu.

**Neden Bu Tercih Edildi:** MedGemma-27B'nin Hugging Face Inference API üzerinden stabil endpoint'e erişim Sprint 4 döneminde güvenilmez olduğundan geçici çözüm uygulandı.

**Önerilen Yaklaşım:**
1. `google/medgemma-27b-it` modeli Vertex AI üzerinden erişim (Google Cloud)
2. Alternatif: `google/medgemma-4b-it` (daha hızlı, 10s timeout'a uygun)
3. Klinik terminoloji doğruluk karşılaştırması: gemma-2-9b vs medgemma-27b

**Beklenen Etki:** `clinical_accuracy` kararlarında özellikle nadir patolojilerde (sekonder sifiliz, MMP) kayda değer iyileşme.

---

### FW-06 — Gemini Sürüm Takibi ve Prompt Versiyonlama

**Mevcut Durum:** `DENTAL_EDUCATOR_PROMPT` sistem promptu kod içinde sabit. Model değişimi (Gemini 2.5 Flash-Lite → yeni sürüm) promptun yeniden test edilmesini gerektiriyor.

**Önerilen Yaklaşım:**
- Prompt versiyonlarını `system_snapshots.llm_config_payload`'a dahil et (kısmen yapıldı)
- Prompt değişimi → `git tag` → araştırma snapshot'ında commit hash takibi
- `LLMInteractionLog`'daki `model_id` alanı bu değişimi zaten takip ediyor

---

### FW-07 — Açık Uçlu Puanlama (OE) İyileştirmeleri

**Mevcut Durum:** OE scoring tamamen AI draft (ai_score_suggestion), eğitimci onayı zorunlu. `grading_status=PENDING` → `GRADED` → `PUBLISHED` zinciri.

**Önerilen Yaklaşım:**
- İnter-rater güvenilirlik analizi: `inter_rater_delta = |instructor_score − secondary_score|`
  → Tablo zaten hazır: `quiz_answers.secondary_instructor_score`
- Delta eşiği (örn. >2 puan) → 3. eğitimci hakem süreci
- AI önerisi doğruluğunu ölçme: `|ai_score_suggestion − instructor_score|` dağılımı

---

## Öncelik 3: Araştırma Altyapısı

### FW-08 — A/B Test Çerçevesi

**Mevcut Durum:** `ε-greedy` keşif mevcut (%10), ancak öğrenci grubunu V1/V2 arasında sistematik bölen formal A/B test altyapısı yok.

**Önerilen Yaklaşım:**
```
Grup A: %50 öğrenci → V1 kural tabanlı öneri
Grup B: %50 öğrenci → V2 XGBoost öneri

Ölçüm: 30 gün sonunda
  - Vaka tamamlama oranı
  - BKT uzmanlaşma hızı
  - Eğitimci notlarındaki ortalama klinik doğruluk
```
- `RecommendationSnapshot.algorithm_version` bu ayrımı zaten tutuyor
- Eksik: öğrenci-grup atama ve izolasyon mekanizması

---

### FW-09 — LLM Bütçe Uyarı Sistemi

**Mevcut Durum:** `LLMInteractionLog` tüm çağrıları ve tahmini maliyeti (`estimated_cost_usd`) loglıyor. Ancak eşik uyarısı veya kota yönetimi yok.

**Önerilen Yaklaşım:**
- Günlük/aylık bütçe eşiği yapılandırması (örn. $5/gün)
- Eşik aşılınca → INSTRUCTOR rolüne bildirim
- Mock fallback zaten mevcut: `get_mock_interpretation()` kota aşımında devreye giriyor
- Analitik panel: `llm_interaction_logs` üzerinden maliyet dağılım grafiği

---

### FW-10 — Araştırma Snapshot Karşılaştırma API

**Mevcut Durum:** Snapshot oluşturma ve dışa aktarma mevcut. İki snapshot arasında fark (diff) hesaplama yok.

**Önerilen Yaklaşım:**
```
GET /api/research/snapshots/compare?base={id1}&target={id2}
Çıktı:
  - Eklenen/silinen sorular
  - Değişen rubrikler
  - Puanlama yapılandırması farkları
  - LLM model değişimi
```

---

## Öncelik 4: Klinik İçerik Genişletme

### FW-11 — Multi-Modal Simülasyon (Radyografi Entegrasyonu)

**Mevcut Durum:** Simülasyon tamamen metin tabanlı. Gerçek klinisyenler radyografi, fotoğraf ve histolojik kesit görüntülerine bakarak tanı koyar.

**Önerilen Yaklaşım:**
- `order_radiograph` eylemi zaten kural motorunda tanımlı
- Eylem tetiklendiğinde ilgili radyografi görüntüsü öğrenciye gösterilsin
- Gemini Vision API ile görüntü yorumlama entegrasyonu
- `case_definitions.states_json` → `radiograph_url` alanı eklenmesi

---

### FW-12 — Vaka Kategorisi Genişletme

**Mevcut Aktif Kategoriler:** INFECTIOUS, IMMUNOLOGIC, NEOPLASTIC

**Eksik Kategoriler:**
```
TRAUMATIC    → travmatik lezyon vakaları
DEVELOPMENTAL→ gelişimsel anomaliler
ENDODONTIC   → endodontik tanı vakaları
PERIODONTIC  → periodontal hastalık yönetimi
PHARMACOLOGY → ilaç yönetimi odaklı vakalar
```

**Not:** `CLINICAL_RULES_DB` ve kural motoru bu kategorilere hazır; içerik girişi gerekiyor.

---

### FW-13 — Eylem Tuşu Genişletme

**Mevcut:** 27 sabit eylem anahtarı
**Kısıt:** `agent.py`'deki sabit liste büyüdükçe prompt token sayısı artar

**Önerilen Yaklaşım:**
- Eylem anahtarlarını DB'ye taşı (`action_definitions` tablosu)
- Gemini sistem promptunu dinamik olarak yükle (sadece aktif vakadaki anahtarlar)
- Token tasarrufu: tüm 27 yerine o vaka için geçerli ~10 anahtar

---

## Öncelik 5: Platform ve Kullanılabilirlik

### FW-14 — Makul AI Maliyet İzleme Metrikleri

Loglama altyapısı mevcut. Eksik:
- Gerçek zamanlı dashboard (Grafana, Prometheus veya Next.js chart)
- `estimated_cost_usd` toplamı zaman serisi grafiği
- `call_type` (interpretation vs validation vs scoring) maliyet dağılımı

---

### FW-15 — EU AI Act Uyum Kapsamı

`LLMInteractionLog` bazı gereksinimleri karşılıyor (karar kaydı, model ID, latency). Eksikler:

| Gereksinim | Durum |
|------------|-------|
| Her kararın kaydedilmesi | ✅ LLMInteractionLog |
| İnsan denetim mekanizması | ✅ Eğitimci paneli + OE onayı |
| Şeffaflık bildirimi | Eksik (UI'da "AI destekli değerlendirme" etiketi) |
| Model yansızlık raporu | Eksik (cinsiyet/ülke bazlı bias testi yok) |
| Veri saklama politikası | Eksik (GDPR uyumlu silme mekanizması) |

---

### FW-16 — Mobil Duyarlı Frontend

**Mevcut Durum:** Next.js + Tailwind CSS, ancak klinik simülasyon chat ekranı geniş ekran için optimize edilmiş.

**Önerilen Yaklaşım:**
- Öğrenci paneli (quiz, öneriler, tekrar takvimi) mobilde kullanılabilir olmalı
- Chat simülasyonu tablet/iPad için optimize edilmeli (klinik ortamda kullanım)

---

## Özet Tablo

| Kod | Başlık | Etki | Zorluk | Bağımlılık |
|-----|--------|------|--------|-----------|
| FW-01 | BKT Parametre Kalibrasyonu | Yüksek | Orta | Yeterli veri |
| FW-02 | IRT Gerçek Veri Oranı | Yüksek | Düşük | Öğrenci kullanımı |
| FW-03 | XGBoost Üretim Rollout | Yüksek | Orta | 200+ tamamlama |
| FW-04 | SM-2 Ease Kalibrasyonu | Orta | Düşük | Veri analizi |
| FW-05 | Gerçek MedGemma Modeli | Yüksek | Yüksek | API erişimi |
| FW-06 | Prompt Versiyonlama | Düşük | Düşük | — |
| FW-07 | OE Inter-Rater Analizi | Orta | Düşük | Eğitimci veri |
| FW-08 | A/B Test Çerçevesi | Yüksek | Orta | XGBoost (FW-03) |
| FW-09 | LLM Bütçe Uyarısı | Orta | Düşük | — |
| FW-10 | Snapshot Karşılaştırma API | Orta | Düşük | — |
| FW-11 | Multi-Modal Radyografi | Yüksek | Yüksek | Görüntü içerik |
| FW-12 | Vaka Kategorisi Genişletme | Orta | Orta | İçerik girişi |
| FW-13 | Eylem Anahtarı DB'ye Taşıma | Düşük | Orta | — |
| FW-14 | AI Maliyet Dashboard | Düşük | Düşük | — |
| FW-15 | EU AI Act Uyumu | Yüksek | Yüksek | Hukuki analiz |
| FW-16 | Mobil Frontend | Orta | Orta | UI tasarım |

---

## Araştırma Yayın Potansiyeli

DentAI'nin ürettiği veri ile yanıtlanabilecek araştırma soruları:

| Soru | Yöntem | Hedef Dergi |
|------|--------|-------------|
| Diş hekimliği simülasyonunda BKT parametreleri nedir? | EM kalibrasyon | Computers & Education |
| Serbest dil komutlarıyla klinik beceri ölçülebilir mi? | Kural motoru puan analizi | Medical Education |
| Sessiz AI değerlendirici öğrenci davranışını etkiler mi? | A/B testi | BMC Medical Education |
| IRT kalibrasyonu soru bankası kalitesini artırır mı? | Güçlük etiket vs fit-b korelasyon | Assessment & Evaluation in HE |
