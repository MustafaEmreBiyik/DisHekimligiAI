"""
Dashboard Ana Sayfa - DentAI
"""

import streamlit as st
import os
import sys

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.student_profile import init_student_profile, show_login_form, show_profile_card
from db.database import init_db

# Initialize database (create tables if not exist)
init_db()

# Initialize profile system
init_student_profile()

# Page config
st.set_page_config(
    page_title="DentAI - Ana Sayfa",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .subtitle {
        font-size: 1.2rem;
        color: #424242;
        text-align: center;
        margin-bottom: 2rem;
    }
    .feature-box {
        background-color: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 5px solid #1E88E5;
        margin-bottom: 1rem;
        color: #212529;
    }
    .feature-box h3 {
        color: #1E88E5;
        margin-top: 0;
    }
    .feature-box p {
        color: #495057;
        margin: 0.5rem 0;
    }
    .feature-box small {
        color: #6c757d;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stat-number {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0;
    }
    .stat-label {
        font-size: 1rem;
        opacity: 0.9;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown('<div class="main-header">🦷 DentAI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Akıllı Diş Hekimliği Eğitim Asistanı</div>', unsafe_allow_html=True)

st.divider()

# ==================== AUTHENTICATION CHECK ====================
# Check if user is authenticated (support both new and legacy session keys)
is_authenticated = st.session_state.get("authentication_status") or st.session_state.get("is_logged_in")

if is_authenticated:
    # User is logged in - show welcome message
    user_info = st.session_state.get("user_info") or st.session_state.get("student_profile", {})
    user_name = user_info.get("name", "Kullanıcı")
    
    st.success(f"👋 Hoş geldiniz, **{user_name}**!")
    
    # Quick action buttons for logged-in users
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("👤 Hesabıma Git", width="stretch", type="primary"):
            st.switch_page("pages/2_account.py")
    
    with col2:
        if st.button("💬 Vaka Çalışması", width="stretch", type="primary"):
            st.switch_page("pages/3_chat.py")
    
    with col3:
        if st.button("📊 İstatistikler", width="stretch", type="primary"):
            st.switch_page("pages/5_stats.py")
    
    st.divider()
else:
    # User is NOT logged in - show login prompt
    st.info("🔐 Lütfen devam etmek için giriş yapın.")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔑 Giriş Yap", width="stretch", type="primary"):
            st.switch_page("pages/1_login.py")
    
    st.divider()

st.divider()

# Introduction Section
col1, col2 = st.columns([2, 1])

with col1:
    st.markdown("## 👋 Hoş Geldiniz!")
    st.markdown("""
    **DentAI**, diş hekimliği öğrencileri için tasarlanmış interaktif bir klinik simülasyon platformudur.
    
    ### 🎯 Neler Yapabilirsiniz?
    
    - 🔬 **Gerçek Vakalarla Pratik:** Oral patoloji vakalarında tanı ve tedavi kararları alın
    - 📊 **Objektif Puanlama:** Her klinik adımınız profesyonel kurallara göre puanlanır
    - 🤖 **AI Destekli Öğrenme:** Yapay zeka size anında geri bildirim verir
    - 📈 **İlerleme Takibi:** Performansınızı analiz edin ve geliştirin
    
    ### 💡 Nasıl Çalışır?
    
    1. **Vaka Seçin:** Sol menüden bir oral patoloji vakası seçin
    2. **Anamnez Alın:** Hastayla konuşur gibi sorular sorun
    3. **Muayene Yapın:** Klinik muayene ve testler isteyin
    4. **Tanı Koyun:** Bulgularınıza göre tanı belirleyin
    5. **Puan Kazanın:** Her doğru adım size puan getirir!
    """)

with col2:
    st.markdown("## 📊 Sizin İstatistikleriniz")
    
    # Get real user stats from database
    if is_authenticated:
        from db.database import get_user_stats
        user_id = user_info.get("student_id", "web_user_default")
        stats = get_user_stats(user_id)
        
        total_points = stats.get("total_points", 0)
        total_solved = stats.get("total_solved", 0)
        avg_score = stats.get("avg_score", 0)
        user_level = stats.get("user_level", "Başlangıç")
    else:
        # Not logged in - show zeros
        total_points = 0
        total_solved = 0
        avg_score = 0
        user_level = "Giriş Yapın"
    
    # Display stats
    st.markdown(f"""
    <div class="stat-card">
        <p class="stat-number">{total_points}</p>
        <p class="stat-label">Toplam Puan</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="stat-card" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
        <p class="stat-number">{total_solved}</p>
        <p class="stat-label">Tamamlanan Vaka</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="stat-card" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
        <p class="stat-number">{avg_score}%</p>
        <p class="stat-label">Ortalama Başarı</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown(f"""
    <div class="stat-card" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
        <p class="stat-number">{user_level}</p>
        <p class="stat-label">Seviye</p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Available Cases Section
st.markdown("## 📚 Mevcut Vakalar")

case_data = [
    {
        "name": "Oral Liken Planus",
        "difficulty": "Orta",
        "icon": "🔵",
        "description": "45 yaşında hasta, ağızda beyaz çizgiler ve yanma hissi",
        "topics": ["Anamnez", "Mukoza Muayenesi", "Ayırıcı Tanı"]
    },
    {
        "name": "Kronik Periodontitis",
        "difficulty": "Zor",
        "icon": "🔴",
        "description": "55 yaşında hasta, dişetlerinde kanama ve diş sallantısı (Kalp pili!)",
        "topics": ["Risk Faktörleri", "Sistemik Durum", "Cihaz Güvenliği"]
    },
    {
        "name": "Primer Herpetik Gingivostomatitis",
        "difficulty": "Orta",
        "icon": "🟡",
        "description": "6 yaşında çocuk hasta, ateş ve oral ülserler",
        "topics": ["Viral Enfeksiyon", "Vital Bulgular", "Tedavi Seçimi"]
    },
    {
        "name": "Behçet Hastalığı",
        "difficulty": "Zor",
        "icon": "🔴",
        "description": "32 yaşında erkek hasta, tekrarlayan oral ülserler",
        "topics": ["Sistemik Hastalık", "Paterji Testi", "Multidisipliner Yaklaşım"]
    },
    {
        "name": "Sekonder Sifiliz",
        "difficulty": "Zor",
        "icon": "🔴",
        "description": "28 yaşında kadın hasta, ağızda beyaz lezyonlar",
        "topics": ["Cinsel Yolla Bulaşan Hastalık", "Serolojik Testler", "Müköz Plaklar"]
    }
]

cols = st.columns(3)
for idx, case in enumerate(case_data):
    with cols[idx % 3]:
        with st.container():
            st.markdown(f"""
            <div class="feature-box">
                <h3>{case['icon']} {case['name']}</h3>
                <p><strong>Zorluk:</strong> {case['difficulty']}</p>
                <p>{case['description']}</p>
                <p><small><strong>Konular:</strong> {', '.join(case['topics'])}</small></p>
            </div>
            """, unsafe_allow_html=True)

st.divider()

# Quick Start Section
st.markdown("## 🚀 Hemen Başlayın!")

col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("💬 Vaka Çalışmasına Başla", width="stretch", type="primary"):
        st.switch_page("pages/3_chat.py")

with col2:
    if st.button("📊 İstatistiklerimi Gör", width="stretch"):
        st.switch_page("pages/5_stats.py")

with col3:
    if st.button("👤 Hesabıma Git", width="stretch"):
        st.switch_page("pages/2_account.py")

with col4:
    if st.button("ℹ️ Kullanım Kılavuzu", width="stretch"):
        st.info("""
        **Hızlı İpuçları:**
        
        1. Net ve açık eylemler yazın: "Hastanın ateşini ölçüyorum"
        2. Sistematik ilerleyin: Anamnez → Muayene → Tanı
        3. Her puanı dikkatlice okuyun, geri bildirim önemli!
        4. Gerçek klinik gibi düşünün 🩺
        """)

st.divider()

# Footer
st.markdown("""
<div style="text-align: center; color: #757575; padding: 2rem 0;">
    <p>🦷 <strong>DentAI</strong> | Yapay Zeka Destekli Eğitim Platformu</p>
    <p><small>Hibrit Mimari: LLM + Kural Tabanlı Değerlendirme</small></p>
</div>
""", unsafe_allow_html=True)
