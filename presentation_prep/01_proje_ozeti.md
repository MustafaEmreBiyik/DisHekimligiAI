# DentAI — Proje Özeti

## Projenin Tam Adı
**DentAI: Yapay Zeka Destekli Diş Hekimliği Eğitim Simülasyon Platformu**

## Tek Cümlelik Tanım
DentAI, diş hekimliği öğrencilerinin gerçek hasta vakalarını yapay zeka eşliğinde simüle etmesini sağlayan, adaptif öğrenme algoritmalarıyla donatılmış web tabanlı bir klinik eğitim platformudur.

---

## Problem: Neden Bu Proje?

Diş hekimliği eğitiminde klinik karar verme becerisi, ancak gerçek hasta vakaları üzerinde çalışılarak kazanılır. Ancak:

- Gerçek klinik ortam, öğrencilerin hata yapmasına izin vermez.
- Standart soru bankası uygulamaları yalnızca bilgi ölçer; klinik süreç değerlendirilemez.
- Her öğrencinin eksiklikleri farklıdır, ancak mevcut araçlar adaptif değildir.
- Öğretim üyelerinin her öğrenciyi birebir takip etmesi zaman açısından sürdürülebilir değildir.

---

## Çözüm: DentAI'nin Yaklaşımı

1. **Klinik Simülasyon**: Öğrenci, sanal bir hastaya serbest dil ile komut girer ("Hastanın alerji geçmişini sorguluyorum"). Sistem bu girdiyi yorumlar, puanlar ve gerçekçi hasta yanıtları üretir.

2. **Hibrit AI Pipeline**: Google Gemini (açıklayıcı geri bildirim) + MedGemma (sessiz klinik doğrulama) + Kural Motoru (objektif puanlama) birlikte çalışır.

3. **Adaptif Öneri Motoru**: Öğrencinin güçlü/zayıf konuları gerçek zamanlı izlenir ve kişiselleştirilmiş sıradaki vaka önerilir.

4. **Araştırma Altyapısı**: Bayesian Knowledge Tracing, IRT kalibrasyon, SM-2 tekrarlama ve XGBoost sıralama ile eğitim verisi bilimsel olarak analiz edilir.

---

## Kullanıcı Rolleri

| Rol | Yaptıkları |
|-----|------------|
| **Öğrenci** | Vaka çözme, quiz, kişiselleştirilmiş öneri alma, tekrar programı takibi |
| **Eğitimci** | Vaka yönetimi, rubrik oluşturma, öğrenci performans analizi, araştırma anlık görüntüsü |
| **Admin** | Kullanıcı yönetimi, sistem sağlığı, AI yapılandırma |

---

## Teknik Yığın (Tech Stack)

| Katman | Teknoloji |
|--------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy, Alembic |
| Frontend | Next.js 15, TypeScript, Tailwind CSS |
| Veritabanı | PostgreSQL |
| AI — Eğitim Asistanı | Google Gemini 2.5 Flash-Lite |
| AI — Klinik Validatör | Google MedGemma |
| ML — Öneri | XGBoost (rank:pairwise) + SHAP |
| ML — Öğrenme Takibi | BKT (Bayesian Knowledge Tracing) |
| ML — Soru Kalibrasyonu | IRT 2PL (Item Response Theory) |
| ML — Tekrarlama | SM-2 (SuperMemo-2) |

---

## Sprint Yolculuğu (Özet)

| Sprint | Odak |
|--------|------|
| S1–S3 | Temel klinik simülasyon, kural motoru, auth, analitik |
| S4–S6 | Coach/Validator mimari, güvenlik katmanı, admin paneli |
| S7–S8 | DB-runtime kurallar, quiz sistemi, sınav takvimi |
| S9–S10 | LLM etkileşim logları, SM-2 tekrarlama, IRT taslak |
| **S11** | **BKT, IRT kalibrasyon, feature store, XGBoost öneri motoru, araştırma snapshot** |

---

## Projenin Özgünlük Noktaları

1. Serbest dil ile klinik komut girişi — hiçbir menü veya şablon yok
2. MedGemma "sessiz değerlendirici" mimarisi — öğrenci görmez, eğitimci görür
3. Klinik güvenlik kuralları deterministik + AI katmanlı doğrulama
4. Prompt injection koruması eğitim ortamında da aktif
5. Araştırma anlık görüntüsü — reproducibility için sistem durumu dondurulabilir
