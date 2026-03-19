"""
Öğrenci Profili & Hesap Sayfası - DentAI
"""

import streamlit as st
import os
import sys
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.student_profile import init_student_profile
from app.frontend.components import render_sidebar
from db.database import SessionLocal, StudentSession, ChatLog, init_db
import json

# Initialize systems
init_db()
init_student_profile()

# Page config
st.set_page_config(
    page_title="DentAI - Hesabım",
    page_icon="👤",
    layout="wide"
)

# ==================== SIDEBAR ====================
render_sidebar(
    page_type="account",
    show_case_selector=False,
    show_model_selector=False
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    .profile-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin-bottom: 2rem;
    }
    .profile-avatar {
        font-size: 5rem;
        margin-bottom: 1rem;
    }
    .stat-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        border: 2px solid #e9ecef;
    }
    .stat-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #667eea;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #6c757d;
        margin-top: 0.5rem;
    }
    .settings-section {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid #dee2e6;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ====================

def get_user_statistics():
    """Get user statistics from database"""
    user_info = st.session_state.get("user_info") or {}
    student_id = user_info.get("student_id", "web_user_default")
    
    db = SessionLocal()
    try:
        # Get all sessions for this student
        sessions = db.query(StudentSession).filter_by(student_id=student_id).all()
        
        total_sessions = len(sessions)
        completed_cases = len(set(s.case_id for s in sessions))
        
        # Calculate statistics from chat logs
        total_actions = 0
        total_score = 0
        
        for session in sessions:
            logs = db.query(ChatLog).filter_by(
                session_id=session.id,
                role="assistant"
            ).all()
            
            for log in logs:
                if log.metadata_json:
                    try:
                        metadata = log.metadata_json if isinstance(log.metadata_json, dict) else json.loads(log.metadata_json)
                        interpreted_action = metadata.get("interpreted_action", "")
                        
                        if interpreted_action and interpreted_action not in ["general_chat", "error"]:
                            assessment = metadata.get("assessment", {})
                            score = assessment.get("score", 0)
                            total_actions += 1
                            total_score += score
                    except:
                        continue
        
        avg_score = (total_score / total_actions) if total_actions > 0 else 0
        
        return {
            "total_sessions": total_sessions,
            "completed_cases": completed_cases,
            "total_actions": total_actions,
            "total_score": total_score,
            "average_score": round(avg_score, 1)
        }
    except Exception as e:
        st.error(f"İstatistikler yüklenirken hata: {e}")
        return {
            "total_sessions": 0,
            "completed_cases": 0,
            "total_actions": 0,
            "total_score": 0,
            "average_score": 0
        }
    finally:
        db.close()


# ==================== MAIN CONTENT ====================

# Check if user is logged in
if "user_info" not in st.session_state or st.session_state.user_info is None:
    st.warning("⚠️ Bu sayfayı görüntülemek için giriş yapmalısınız.")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("🔐 Giriş Sayfasına Git", width="stretch", type="primary"):
            st.switch_page("pages/1_login.py")
    
    st.stop()

# Get user information from session state
user_info = st.session_state.user_info
student_name = user_info.get("name", "Kullanıcı")
student_role = user_info.get("role", "Öğrenci")
student_email = user_info.get("email", "kullanici@example.com")
student_id = user_info.get("student_id", "N/A")

# Profile Header
st.markdown(f"""
<div class="profile-header">
    <div class="profile-avatar">👤</div>
    <h1>{student_name}</h1>
    <p style="font-size: 1.2rem; opacity: 0.9;">🎓 {student_role}</p>
</div>
""", unsafe_allow_html=True)

# Statistics Section
st.markdown("## 📊 Performans İstatistikleri")

stats = get_user_statistics()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{stats['total_sessions']}</div>
        <div class="stat-label">Toplam Oturum</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{stats['completed_cases']}</div>
        <div class="stat-label">Tamamlanan Vaka</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{stats['total_actions']}</div>
        <div class="stat-label">Toplam Eylem</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{stats['average_score']}</div>
        <div class="stat-label">Ortalama Puan</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# Account Information Section
st.markdown("## 📋 Hesap Bilgileri")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="settings-section">
        <h3 style="color: #000080;">👤 Kişisel Bilgiler</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.text_input("Ad Soyad", value=student_name, disabled=True)
    st.text_input("Öğrenci Numarası", value=student_id, disabled=True)
    st.text_input("E-posta", value=student_email, disabled=True)
    
    if st.button("✏️ Bilgilerimi Güncelle", width="stretch"):
        st.info("Bu özellik yakında aktif olacak!")

with col2:
    st.markdown("""
    <div class="settings-section">
        <h3 style="color: #000080;" >🔐 Güvenlik</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.text_input("Mevcut Şifre", type="password", disabled=True, placeholder="••••••••")
    st.text_input("Yeni Şifre", type="password", disabled=True, placeholder="••••••••")
    st.text_input("Yeni Şifre (Tekrar)", type="password", disabled=True, placeholder="••••••••")
    
    if st.button("🔒 Şifremi Değiştir", width="stretch"):
        st.info("Bu özellik yakında aktif olacak!")

st.divider()

# Settings Section
st.markdown("## ⚙️ Ayarlar")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    <div class="settings-section">
        <h3 style="color: #000080;" >🔔 Bildirim Tercihleri</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.checkbox("E-posta bildirimleri", value=True, disabled=True)
    st.checkbox("Haftalık ilerleme raporu", value=True, disabled=True)
    st.checkbox("Yeni vaka bildirimleri", value=False, disabled=True)
    
    if st.button("💾 Bildirimleri Kaydet", width="stretch"):
        st.info("Bu özellik yakında aktif olacak!")

with col2:
    st.markdown("""
    <div class="settings-section">
        <h3 style="color: #000080;" >🎨 Görünüm Ayarları</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.selectbox("Tema", ["Açık", "Koyu", "Sistem"], disabled=True)
    st.selectbox("Dil", ["Türkçe", "English"], disabled=True)
    st.slider("Font Boyutu", 12, 20, 14, disabled=True)
    
    if st.button("💾 Ayarları Kaydet", width="stretch"):
        st.info("Bu özellik yakında aktif olacak!")

st.divider()

# Activity Log Section
st.markdown("## 📅 Son Aktiviteler")

with st.expander("🕐 Aktivite Geçmişi", expanded=False):
    st.markdown("""
    - **10 Aralık 2025, 14:23** - "Oral Liken Planus" vakası tamamlandı
    - **10 Aralık 2025, 13:45** - "Kronik Periodontitis" vakasına başlandı
    - **9 Aralık 2025, 16:10** - Profil bilgileri güncellendi
    - **9 Aralık 2025, 11:30** - "Primer Herpes" vakası tamamlandı
    - **8 Aralık 2025, 15:20** - Sistem giriş yapıldı
    """)

st.divider()

# Danger Zone
st.markdown("## ⚠️ Tehlikeli Bölge")

with st.expander("🗑️ Hesap Yönetimi", expanded=False):
    st.warning("**Dikkat:** Bu işlemler geri alınamaz!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Tüm İlerlememi Sıfırla", width="stretch", type="secondary"):
            st.error("Bu özellik henüz aktif değil.")
    
    with col2:
        if st.button("❌ Hesabımı Sil", width="stretch", type="secondary"):
            st.error("Bu özellik henüz aktif değil.")

st.divider()

# Footer
st.markdown("""
<div style="text-align: center; color: #757575; padding: 2rem 0;">
    <p>📧 Destek: betul.danismaz@istun.edu.tr | 🔐 Gizlilik Politikası | 📜 Kullanım Koşulları</p>
    <p><small>Son güncelleme: Aralık 2025</small></p>
</div>
""", unsafe_allow_html=True)
