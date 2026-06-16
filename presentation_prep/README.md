# DentAI — Sunum Hazırlık Dosyaları

Bu klasör, DentAI projesinin bitirme projeleri yarışması teknik sunumu için hazırlanmış belgelerden oluşmaktadır. Odak: **Araştırma Odaklı Çalışmalar**.

## Dosyalar

| Dosya | İçerik | Öncelik |
|-------|--------|---------|
| `01_proje_ozeti.md` | Projenin genel tanımı, problem, çözüm, tech stack | İlk oku |
| `02_arastirma_odakli_calisma.md` | BKT, IRT, SM-2, XGBoost, araştırma snapshot — teknik derinlik | ANA BELGE |
| `03_sistem_mimarisi.md` | **Güncel** — Tam DB şeması (24 tablo), tüm servisler, akış diyagramları | Mimari sorular için |
| `04_klinik_simulasyon_tasarimi.md` | Simülasyon tasarımı, eylem anahtarları, puanlama | Klinik sorular için |
| `05_sunum_slayt_plani.md` | Slayt akışı, notlar, jüri soru-cevap hazırlığı | Slayt yaparken |
| `06_teknik_detaylar_referans.md` | Parametre değerleri, API listesi, sprint geçmişi | Hızlı başvuru |
| `07_future_work.md` | **16 gelecek çalışma maddesi** — gerekçe + önerilen yaklaşım + araştırma yayın potansiyeli | Gelecek slaydı için |

## Claude'a İletim Talimatı

Bu dosyaları Claude'a iletirken şu bağlamı ekle:

```
Bu dosyalar DentAI adlı bir yapay zeka destekli diş hekimliği eğitim 
simülasyon platformunun teknik sunum materyalleridir. Sunum "araştırma 
odaklı çalışmalar" üzerine odaklanmaktadır. BKT, IRT, SM-2, XGBoost 
ve araştırma snapshot sistemi öne çıkan araştırma katkılarıdır.

[Dosya içeriklerini buraya yapıştır]
```

## Sunum Vurgulanacak Araştırma Katkıları (Öncelik Sırası)

1. **BKT (Bayesian Knowledge Tracing)** — Corbett & Anderson 1995 teorisinin diş hekimliği simülasyonuna uyarlanması
2. **IRT 2PL Kalibrasyon** — Soru güçlüğünün otomatik çıkarımı + sentetik bootstrap
3. **XGBoost Öneri Motoru** — 37 boyutlu özellik vektörü, SHAP yorumlanabilirlik
4. **Araştırma Snapshot** — Tekrarlanabilir araştırma altyapısı
5. **Sessiz Değerlendirici Mimarisi** — MedGemma'nın öğrenciden gizli çalışması
