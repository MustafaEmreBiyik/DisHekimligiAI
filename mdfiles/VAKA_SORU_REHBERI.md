# 📋 VAKA SORU REHBERİ - DentAI

**Tüm Vakalarda Sorulabilecek Sorular ve Görsel Çıkış Durumları**

---

## 🦷 VAKA 1: Oral Liken Planus (OLP)

### 👤 Hasta Profili

- **Yaş:** 45 / **Cinsiyet:** -
- **Şikayet:** "Ağzımda beyaz çizgiler ve acı hissediyorum"
- **Tıbbi Geçmiş:** Hipertansiyon (ACE inhibitörü)
- **Zorluk:** Orta

### 💬 Sorulabilecek Sorular & Puanlama

| #   | Soru/Eylem              | AI'ya Nasıl Söylenir                         | Puan | Görsel Çıkar mı?                   |
| --- | ----------------------- | -------------------------------------------- | ---- | ---------------------------------- |
| 1   | İlaç ve alerji kontrolü | "İlaç kullanıyor musunuz? Alerjiniz var mı?" | 15   | ❌                                 |
| 2   | Oral muayene            | "Ağız içi muayenesi yapmak istiyorum"        | 20   | ✅ **EVET** - OLP klinik görüntüsü |

### 🖼️ Görsel Detayı

- **Dosya:** `assets/images/olp_clinical.jpg`
- **Açıklama:** Bilateral bukkal mukozada retikular beyaz çizgiler (Wickham striae)
- **Tetikleyici:** `perform_oral_exam` eylemi

### ✅ Doğru Tanı

Oral Liken Planus

### 📊 Maksimum Puan: 35

---

## 🦷 VAKA 2: Kronik Periodontitis (Riskli Hasta)

### 👤 Hasta Profili

- **Yaş:** 55 / **Cinsiyet:** Erkek
- **Şikayet:** "Diş etlerimde kanama ve dişlerde sallanma var"
- **Tıbbi Geçmiş:** Tip 2 Diyabet, Kalp Pili (Pacemaker)
- **İlaçlar:** Metformin, Kan Sulandırıcı (Aspirin)
- **Alerji:** Penisilin
- **Sosyal:** Günde 1 paket sigara (20 yıl)
- **Zorluk:** Zor

### 💬 Sorulabilecek Sorular & Puanlama

| #   | Soru/Eylem             | AI'ya Nasıl Söylenir                                 | Puan   | Görsel Çıkar mı?                   |
| --- | ---------------------- | ---------------------------------------------------- | ------ | ---------------------------------- |
| 1   | Kimlik bilgileri       | "Hastanın adını ve kimlik bilgilerini alalım"        | 5      | ❌                                 |
| 2   | **Kalp pili kontrolü** | "Kalp pili var mı? Elektronik implant?"              | **25** | ❌ (KRİTİK!)                       |
| 3   | Kanama/Pıhtılaşma      | "Kanama probleminiz var mı? Ameliyat geçirdiniz mi?" | 15     | ✅ **EVET** - Kanama riski görseli |
| 4   | Diyabet kontrolü       | "Şeker hastalığınız var mı? Kaç yıldır?"             | 15     | ❌                                 |
| 5   | Sigara sorgusu         | "Sigara kullanıyor musunuz?"                         | 10     | ❌                                 |
| 6   | Ağız hijyeni           | "Günde kaç kez diş fırçalıyorsunuz?"                 | 10     | ❌                                 |
| 7   | İlaç/Alerji            | "Hangi ilaçları kullanıyorsunuz? Alerjiniz var mı?"  | 10     | ❌                                 |
| 8   | Oral muayene           | "Ağız içi muayene yapalım"                           | 15     | ✅ Kanama görseli (tekrar)         |

### 🖼️ Görsel Detayı

- **Dosya:** `assets/images/perio_clinical.jpg`
- **Açıklama:** Dişetlerinde kanama ve periodontal hasar
- **Tetikleyici:** `check_bleeding_disorder` veya `perform_oral_exam`

### ✅ Doğru Tanı

Evre 3 Derece C Periodontitis

### 📊 Maksimum Puan: 105

⚠️ **DİKKAT:** Bu vakada kalp pili sorgulaması 25 puanla en kritik adımdır!

---

## 🦷 VAKA 3: Primer Herpetik Gingivostomatitis

### 👤 Hasta Profili

- **Yaş:** 6 / **Cinsiyet:** Erkek
- **Şikayet:** "Ağzımda çok sayıda yara var, ateşliyim ve yemek yiyemiyorum"
- **Tıbbi Geçmiş:** Yok
- **Sosyal:** Kreşe gidiyor
- **Zorluk:** Orta

### 💬 Sorulabilecek Sorular & Puanlama

| #   | Soru/Eylem              | AI'ya Nasıl Söylenir                               | Puan    | Görsel Çıkar mı?                 |
| --- | ----------------------- | -------------------------------------------------- | ------- | -------------------------------- |
| 1   | Oral muayene            | "Ağız içi muayene yapalım"                         | 20      | ✅ **EVET** - Herpetik lezyonlar |
| 2   | Vital bulgular          | "Ateşini ölçelim, nabız kontrol"                   | 10      | ❌                               |
| 3   | ❌ Antibiyotik reçetesi | "Antibiyotik reçete edelim"                        | **-20** | ❌ (HATA!)                       |
| 4   | ✅ Palyatif bakım       | "Bol sıvı, yatak istirahati, ağrı kesici önerelim" | 25      | ❌                               |
| 5   | Tanı koyma              | "Primer herpetik gingivostomatit tanısı koyuyorum" | 30      | ❌                               |

### 🖼️ Görsel Detayı

- **Dosya:** `assets/images/herpes_clinical.jpg`
- **Açıklama:** Tüm oral mukozada patlamış veziküller ve ağrılı ülserler
- **Tetikleyici:** `perform_oral_exam`

### ✅ Doğru Tanı

Primer Herpetik Gingivostomatitis

### 📊 Maksimum Puan: 85 (Antibiyotik yazılmazsa)

⚠️ **DİKKAT:** Antibiyotik reçete etmek -20 puan kaybettirir! Viral enfeksiyon, antibiyotik etkisiz.

---

## 🦷 VAKA 4: Behçet Hastalığı

### 👤 Hasta Profili

- **Yaş:** 32 / **Cinsiyet:** Erkek
- **Şikayet:** "Ağzımda sürekli çıkan ve çok ağrıyan yaralar var"
- **Tıbbi Geçmiş:** Gözde tekrarlayan kızarıklık (Üveit)
- **Sosyal:** Sigara kullanıyor
- **Zorluk:** Zor

### 💬 Sorulabilecek Sorular & Puanlama

| #   | Soru/Eylem        | AI'ya Nasıl Söylenir                                       | Puan   | Görsel Çıkar mı?                    |
| --- | ----------------- | ---------------------------------------------------------- | ------ | ----------------------------------- |
| 1   | Oral muayene      | "Ağız içi muayene yapalım"                                 | 15     | ✅ **EVET** - Genital ülser görseli |
| 2   | Sistemik semptom  | "Başka yerlerde de yara çıkıyor mu? Göz sorununuz var mı?" | 20     | ✅ Genital ülser (tekrar)           |
| 3   | **Paterji testi** | "Paterji testi yapalım"                                    | **30** | ❌ (KRİTİK!)                        |
| 4   | Tanı koyma        | "Behçet hastalığı tanısı koyuyorum"                        | 30     | ❌                                  |

### 🖼️ Görsel Detayı

- **Dosya:** `assets/images/behcet_clinical.jpg`
- **Açıklama:** Genital bölgede benzer aftöz ülserler
- **Tetikleyici:** `perform_oral_exam` VEYA `ask_systemic_symptoms`

### ✅ Doğru Tanı

Behçet Hastalığı

### 📊 Maksimum Puan: 95

💡 **İPUCU:** İlk oral muayenede veya sistemik semptom sorgusunda genital ülser bulgusu görsel olarak açılır!

---

## 🦷 VAKA 5: Sekonder Sifiliz (Müköz Plak)

### 👤 Hasta Profili

- **Yaş:** 28 / **Cinsiyet:** Kadın
- **Şikayet:** "Boğazımda ağrı ve ağzımda garip beyaz lekeler var"
- **Tıbbi Geçmiş:** Halsizlik, hafif ateş
- **Sosyal:** Şüpheli temas öyküsü
- **Zorluk:** Zor

### 💬 Sorulabilecek Sorular & Puanlama

| #   | Soru/Eylem        | AI'ya Nasıl Söylenir                | Puan | Görsel Çıkar mı?                 |
| --- | ----------------- | ----------------------------------- | ---- | -------------------------------- |
| 1   | Oral muayene      | "Ağız içi muayene yapalım"          | 15   | ✅ **EVET** - Müköz plak görseli |
| 2   | Seroloji testleri | "VDRL ve TPHA testleri istiyorum"   | 25   | ❌                               |
| 3   | Tanı koyma        | "Sekonder sifiliz tanısı koyuyorum" | 30   | ❌                               |

### 🖼️ Görsel Detayı

- **Dosya:** `assets/images/syphilis_clinical.jpg`
- **Açıklama:** Dudak ve damakta grimsi-beyaz müköz plaklar (enfeksiyöz!)
- **Tetikleyici:** `perform_oral_exam`

### ✅ Doğru Tanı

Sekonder Sifiliz

### 📊 Maksimum Puan: 70

---

## 🦷 VAKA 6: Kronik Deskuamatif Gingivitis (Müköz Membran Pemfigoidi)

### 👤 Hasta Profili

- **Yaş:** 46 / **Cinsiyet:** Kadın
- **Şikayet:** "Diş etlerimde sızlama, yanma ve soyulmalar var. Asitli yiyecekleri yiyemiyorum"
- **Tıbbi Geçmiş:** Hipertansiyon
- **İlaçlar:** ACE İnhibitörü
- **Zorluk:** Zor

### 💬 Sorulabilecek Sorular & Puanlama

| #   | Soru/Eylem         | AI'ya Nasıl Söylenir                        | Puan   | Görsel Çıkar mı?                           |
| --- | ------------------ | ------------------------------------------- | ------ | ------------------------------------------ |
| 1   | Oral muayene       | "Ağız içi muayene yapalım"                  | 10     | ✅ **EVET** - Deskuamatif gingivit görseli |
| 2   | **Nikolsky testi** | "Nikolsky testi yapalım"                    | **25** | ❌ (KRİTİK!)                               |
| 3   | **DIF Biyopsi**    | "Direkt immünofloresan biyopsi istiyorum"   | **30** | ❌ (ALTIN STANDART!)                       |
| 4   | Tanı koyma         | "Müköz membran pemfigoidi tanısı koyuyorum" | 40     | ❌                                         |

### 🖼️ Görsel Detayı

- **Dosya:** `assets/images/desquamative_clinical.jpg`
- **Açıklama:** Yapışık dişetinde yaygın, parlak kırmızı eritem ve soyulmalar
- **Tetikleyici:** `perform_oral_exam`

### ✅ Doğru Tanı

Müköz Membran Pemfigoidi

### 📊 Maksimum Puan: 105

⚠️ **DİKKAT:** Bu vaka en yüksek puanlı tanıyı içerir (40 puan)! Nikolsky testi ve DIF biyopsi kritik adımlardır.

---

## 📊 GENEL İSTATİSTİKLER

### Vaka Zorluk Dağılımı

- 🟢 **Kolay:** 0 vaka
- 🟡 **Orta:** 2 vaka (OLP, Herpes)
- 🔴 **Zor:** 4 vaka (Perio, Behçet, Sifiliz, Pemfigoid)

### Görsel İçeren Eylemler

| Vaka      | Görsel Tetikleyen Eylem                            | Görsel Dosyası            |
| --------- | -------------------------------------------------- | ------------------------- |
| OLP       | `perform_oral_exam`                                | olp_clinical.jpg          |
| Perio     | `check_bleeding_disorder` veya `perform_oral_exam` | perio_clinical.jpg        |
| Herpes    | `perform_oral_exam`                                | herpes_clinical.jpg       |
| Behçet    | `perform_oral_exam` veya `ask_systemic_symptoms`   | behcet_clinical.jpg       |
| Sifiliz   | `perform_oral_exam`                                | syphilis_clinical.jpg     |
| Pemfigoid | `perform_oral_exam`                                | desquamative_clinical.jpg |

### En Yüksek Puanlı Eylemler

1. **Pemfigoid Tanısı:** 40 puan
2. **Behçet Tanısı, Herpes Tanısı, Sifiliz Tanısı:** 30 puan
3. **DIF Biyopsi (Pemfigoid):** 30 puan
4. **Paterji Testi (Behçet):** 30 puan
5. **Kalp Pili Kontrolü (Perio):** 25 puan

### Kritik Hatalar

| Hata                                    | Puan Kaybı | Vaka   |
| --------------------------------------- | ---------- | ------ |
| Viral enfeksiyonda antibiyotik reçetesi | -20 puan   | Herpes |

---

## 🎯 BAŞARI İPUÇLARI

### Her Vakada Mutlaka:

1. ✅ **Oral muayene yapın** → Neredeyse her vakada puan + görsel verir
2. ✅ **Sistemik sorgu** → Gizli bulguları ortaya çıkarır
3. ✅ **Özel testler** → Nikolsky, Paterji gibi testler kritik puanlar
4. ✅ **Laboratuvar** → Seroloji, biyopsi gibi testler tanıyı destekler

### Dikkat Edilmesi Gerekenler:

- 🔴 **Kalp pili olan hastada** elektronik cihaz kullanımına dikkat (Perio vakası)
- 🔴 **Viral enfeksiyonda** antibiyotik yazma (Herpes vakası)
- 🔴 **Kanama riski olan hastada** girişimsel işlemler öncesi sorgu (Perio vakası)
- 🔴 **Pemfigoid şüphesinde** DIF biyopsi altın standarttır

### Görsel Stratejisi:

- 💡 İlk adımda mutlaka **oral muayene** yapın → Hemen görsel açılır ve klinik tabloyu görürsünüz
- 💡 **Sistemik semptom** sorgusu → Ekstra organ tutulumlarını öğrenirsiniz (Behçet'te genital ülser gibi)

---

## 📝 SORU ÖRNEKLERİ (AI'ya Nasıl Söylerim?)

### Anamnez Soruları:

- "Hastanın tıbbi geçmişini öğrenmek istiyorum"
- "İlaç kullanıyor mu? Alerji var mı?"
- "Sigara içiyor musunuz?"
- "Daha önce ameliyat geçirdiniz mi?"
- "Ailede benzer durum var mı?"

### Muayene:

- "Ağız içi muayene yapmak istiyorum"
- "Vital bulgularını kontrol edelim"
- "Cilt muayenesi yapayım"
- "Lenf nodlarına bakalım"

### Özel Testler:

- "Nikolsky testi yapalım"
- "Paterji testi istiyorum"
- "Biyopsi almak istiyorum"
- "DIF incelemesi yapılsın"

### Laboratuvar:

- "Kan testleri istiyorum"
- "VDRL ve TPHA testleri"
- "Şeker ölçümü yapalım"

### Tanı:

- "Oral liken planus tanısı koyuyorum"
- "Behçet hastalığı olduğunu düşünüyorum"
- "Primer herpetik gingivostomatit tanısı"

### Tedavi:

- "Topikal steroid reçete edelim"
- "Palyatif bakım önerelim"
- "Ağız hijyeni eğitimi verelim"
- "Uzmana sevk edelim"

---

**Son Güncelleme:** Sprint 3 - Intelligent Analytics (Aralık 2025)  
**Toplam Vaka:** 6  
**Toplam Maksimum Puan:** 495 puan
