# DentAI — Klinik Simülasyon Tasarımı

---

## 1. Simülasyon Felsefesi

Geleneksel çoktan seçmeli soru formatlarının aksine DentAI, öğrenciye **açık uçlu, serbest dil ile komut** girişi sunar. Bu yaklaşımın temel savı şudur:

> Gerçek klinik ortamda hekim menüden seçim yapmaz; kendi kararını bağımsız olarak oluşturur ve uygular.

Bu nedenle sistem:
- Sabit seçenek listeleri **sunmaz**
- Öğrencinin doğal dil ile düşündüğü eylemi girdiğini varsayar
- Girdiyi **NLU → eylem anahtarı** zinciri ile normalleştirir
- Kural motoru normalleştirilmiş anahtar üzerinden puanlar

---

## 2. Desteklenen Klinik Vaka Kategorileri

### Oral Patoloji Vakaları (Aktif)

| Kategori | Kod | Örnek Tanı |
|----------|-----|------------|
| Enfeksiyöz | INFECTIOUS | Primer Herpetik Gingivostomatit, Sekonder Sifiliz |
| İmmünolojik | IMMUNOLOGIC | Oral Liken Planus, Mukozal Membran Pemfigoid |
| Neoplastik | NEOPLASTIC | Şüpheli malignite, biyopsi endikasyonu |
| Sistemik | SYSTEMIC | Behçet Hastalığı, hematolojik bulgular |

---

## 3. Desteklenen Eylem Anahtarları (27 Anahtar)

Sistemde şu anda tanımlı ve puanlanan eylemler:

```
Anamnez:
  gather_medical_history      → Tıbbi geçmiş alma
  gather_personal_info        → Kişisel bilgi toplama
  check_allergies_meds        → Alerji ve ilaç kontrolü
  check_diabetes              → Diyabet sorgulama
  check_bleeding_disorder     → Kanama bozukluğu sorgusu
  check_pacemaker             → Kalp pili sorgusu
  check_oral_hygiene_habits   → Ağız hijyen alışkanlıkları
  ask_hydration_nutrition     → Hidrasyon/beslenme sorgusu
  ask_systemic_symptoms       → Sistemik belirti sorgusu

Muayene:
  perform_oral_exam           → Ağız içi muayene
  perform_extraoral_exam      → Ağız dışı muayene
  check_vital_signs           → Vital bulgular kontrolü
  check_fever                 → Ateş ölçümü

Tanısal Testler:
  order_radiograph            → Radyografi istemi
  perform_pathergy_test       → Paterji testi
  perform_nikolsky_test       → Nikolsky testi
  request_serology_tests      → Seroloji testleri
  request_dif_biopsy          → DIF biyopsi istemi

Tanı:
  diagnose_pulpitis           → Pulpit tanısı
  diagnose_herpetic_gingivostomatitis → HGS tanısı
  diagnose_primary_herpes     → Primer herpes tanısı
  diagnose_behcet_disease     → Behçet tanısı
  diagnose_secondary_syphilis → Sekonder sifiliz tanısı
  diagnose_mucous_membrane_pemphigoid → MMP tanısı

Tedavi:
  prescribe_antibiotics       → Antibiyotik reçeteleme
  prescribe_palliative_care   → Palyatif bakım
  refer_oral_surgery          → Oral cerrahi sevki
```

---

## 4. Puanlama Sistemi

### 4.1 Kural Bazlı Puanlama

Her eylem-vaka çifti için bir kural tanımlanır:

```json
{
  "target_action": "check_allergies_meds",
  "score": 10,
  "rule_outcome": "Alerji geçmişi doğru şekilde sorgulandı",
  "is_critical_safety_rule": false,
  "safety_category": null,
  "competency_tags": ["history_taking", "patient_safety"],
  "state_updates": { "allergy_checked": true }
}
```

### 4.2 Kritik Güvenlik Kuralları

Bazı eylemler kritik güvenlik niteliğindedir. Örnek:

```json
{
  "target_action": "prescribe_antibiotics",
  "score": -20,
  "is_critical_safety_rule": true,
  "safety_category": "wrong_medication",
  "competency_tags": ["pharmacology", "patient_safety"]
}
```

Kritik kurallar hem kural motorunda **hem de** MedGemma'da ayrıca değerlendirilir.

### 4.3 Bileşik Puan

```
Bileşik Puan = f(
  quiz_score,          # Soru bankası performansı
  case_score,          # Vaka tamamlama puanı
  safety_score,        # Güvenlik kural uyumu
  topic_accuracy       # Konu bazlı doğruluk
)
```

---

## 5. Hasta Simülasyonu Davranış Kuralları

### 5.1 Kaçamak Hasta Protokolü

Gerçekçi klinik deneyim için hastalar ilk soruda tüm bilgiyi vermez:

```
İlk tur: Sigara/alkol kullanımı inkâr edilir
         ("Hayır, hiç sigara içmiyorum")

Öğrenci devam ederse: "Dişlerde lekeler görüyorum, buna rağmen?"
         → Hasta kabul etmek zorunda kalır

Geçmiş hastalık: "Ah o, çok eski bir şeydi, önemli değil..."
         → Öğrenci ısrar ederse detay verir
```

### 5.2 Klinik Tanımlama Standartları

Sistem promptuna işlenmiş hassas kurallar:

| Tanı | DOĞRU Tanımlama | YANLIŞ Tanımlama |
|------|-----------------|------------------|
| Primer Herpes | "beyazımsı sarımsı çok sayıda odaklar şeklinde ülserasyonlar" | ~~"beyaz çizgiler"~~ |
| Oral Liken Planus | "Wickham striası — ağ şeklinde beyaz çizgiler" | ~~"yaralar"~~ |
| Pemfigoid | "subepitelyal büller" | ~~"ülser"~~ |

### 5.3 Görsel Metafor Protokolü

- Liken Planus lezyonu → "balık ağı görünümü"
- Kandida → "peynir benzeri beyaz örtü"
- Ülser → "zımbalanmış krater"

---

## 6. Feedback Katmanları

### 6.1 Öğrenci Gören Katman

- **Gemini'nin explanatory_feedback**: Türkçe, kısa (≤3 cümle), tarafsız
- Eylem tipi CHAT ise → sadece sohbet yanıtı
- Eylem tipi ACTION ise → klinik açıklama

### 6.2 Eğitimci Gören Katman (Silent Evaluation)

```
clinical_accuracy:  "high" | "medium" | "low" | null
safety_flags:       ["deterministic:wrong_medication", "medgemma:contraindication"]
missing_critical_steps: ["critical competency: pharmacology"]
faculty_notes:      "Deterministic critical safety pre-check triggered."
```

### 6.3 Puan Görünürlüğü

"Silent Evaluator" mimarisi nedeniyle öğrenci **anlık puan görmez**. Bu bilinçli bir tasarım kararıdır:

- Anında puan görünce öğrenci strateji değiştirir
- Gerçek klinik süreç simüle edilmez
- Eğitimci tüm detayları görür, öğrenci yalnızca açıklayıcı geri bildirim alır

---

## 7. Mini Vaka Sistemi

Uzun simülasyon oturumlarına ek olarak "mini vakalar" kısa, odaklı pratik sağlar:

```
Mini Vaka Özellikleri:
  - Tek bir klinik sorun odağı
  - 3–7 eylem adımı
  - Anında tamamlama
  - Öneri motoru bu verileri de kullanır
```

---

## 8. Rubrik Versiyonlama

Eğitimciler puanlama kriterlerini versiyonlayabilir:

```
case_rubric_v1 → ilk sürüm (Sprint 5)
case_rubric_v2 → güncelleme (Sprint 9)
  ↓
rubric_version_service.py → hangi oturumun hangi versiyonla puanlandığını takip eder
```

Bu yapı araştırma sonuçlarının **rubrik değişikliklerinden izole** edilmesini sağlar.

---

## 9. Soru Bankası ve IRT Entegrasyonu

### 9.1 Soru Yapısı

```
Question:
  unit_id       → Ders birimi
  week_number   → Hafta
  difficulty    → "beginner" | "medium" | "advanced" | "hard"
  competency_tags → ilgili yetkinlikler
  mapped_cases  → hangi klinik vakalarla ilişkili
```

### 9.2 IRT ile Eşleme

Her soru için IRT kalibrasyonu tamamlandığında:
- `a` (ayrım gücü) yüksek sorular → bu soruyu doğru cevaplayan öğrenci ile yanlış cevaplayan arasında güçlü ayrım
- `b` (güçlük) → öğrencinin θ yetenek seviyesine göre optimal soru seçimi

### 9.3 Puanlama Süreci

```
Öğrenci soruyu cevaplar
      ↓
oe_scoring_service.py (açık uçlu)
      ↓
ai_score (0.0–1.0) + grading_status
      ↓
BKT observe() → mastery_prob güncelleme
      ↓
composite_score_service.py → bileşik puan
      ↓
SM-2 next_review_state() → tekrar takvimi
```
