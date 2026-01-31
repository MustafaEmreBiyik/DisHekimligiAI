"""
Dental Tutor - Ana Uygulama
===========================
Streamlit uygulaması için ana giriş noktası
"""

import streamlit as st

st.set_page_config(
    page_title="Dental Tutor",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🦷 Dental Tutor")
st.header("Diş Hekimliği Vaka Tabanlı Öğrenme Platformu")

st.markdown("""
### Hoş Geldiniz! 👋

Bu platform, diş hekimliği öğrencilerinin klinik vakalarda pratik yapmasına 
ve yapay zeka destekli geri bildirim almasına olanak sağlar.

#### 🎯 Özellikler:
- 💬 **Vaka Çalışması**: Hasta görüşmesi simülasyonları
- 📊 **İstatistikler**: Performans takibi ve değerlendirme
- 👤 **Profil Yönetimi**: Kişisel öğrenme geçmişi
- 🤖 **AI Destekli Değerlendirme**: Anlık geri bildirim

#### 🚀 Başlamak için:
Sol menüden **💬 Vaka Çalışması** sayfasına gidin.
""")

st.divider()

col1, col2, col3 = st.columns(3)

with col1:
    st.info("📚 **Vaka Kütüphanesi**\n\n6 farklı klinik vaka senaryosu")

with col2:
    st.success("🎯 **Hedef Odaklı**\n\nKlinik akıl yürütme becerileri")

with col3:
    st.warning("🔄 **Sürekli Geri Bildirim**\n\nAnlık performans değerlendirmesi")
