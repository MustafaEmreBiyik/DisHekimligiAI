"""
Secure Login Page - Dental Tutor
Authenticates users against local JSON credentials file.
"""

import streamlit as st
import json
import os
import sys
from pathlib import Path

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app.frontend.components import render_sidebar

# Page config
st.set_page_config(
    page_title="Dental Tutor - Giriş",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==================== SIDEBAR ====================
render_sidebar(
    page_type="login",
    show_case_selector=False,
    show_model_selector=False
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    .login-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 15px;
        margin-bottom: 2rem;
    }
    .login-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
    }
    }
    .info-box {
        background: #e7f3ff;
        border-left: 4px solid #2196F3;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ====================

def load_student_profiles():
    """
    Load student profiles from JSON file.
    Returns dictionary of student profiles or None if error.
    """
    try:
        # Construct absolute path to student profiles file
        current_dir = Path(__file__).parent.absolute()
        profiles_path = current_dir.parent / "data" / "student_profiles.json"
        
        if not profiles_path.exists():
            st.error(f"❌ Öğrenci profilleri dosyası bulunamadı: {profiles_path}")
            return None
        
        with open(profiles_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Data is a dictionary with student_id as keys
        if not isinstance(data, dict):
            st.error("❌ Geçersiz profil dosyası formatı.")
            return None
        
        return data
    
    except json.JSONDecodeError as e:
        st.error(f"❌ JSON dosyası okunamadı: {e}")
        return None
    except Exception as e:
        st.error(f"❌ Beklenmeyen hata: {e}")
        return None


def authenticate_user(username: str, password: str, profiles_dict: dict) -> dict:
    """
    Authenticate user against student profiles.
    
    Args:
        username: User's student_id
        password: User's password
        profiles_dict: Dictionary of student profiles
    
    Returns:
        User info dictionary if authenticated, None otherwise
    """
    if not username or not password:
        return None
    
    # Check if username exists in profiles
    if username in profiles_dict:
        user = profiles_dict[username]
        
        # Verify password
        if user.get("password") == password:
            # Return user info (excluding password and history)
            return {
                "student_id": user.get("student_id"),
                "name": user.get("name"),
                "email": user.get("email", f"{username}@istun.edu.tr"),
                "role": user.get("role", "Öğrenci")
            }
    
    return None


def login_user(user_info: dict):
    """
    Set session state for authenticated user and redirect to account page.
    
    Args:
        user_info: Dictionary containing user details
    """
    # Set authentication status FIRST (critical for session persistence)
    st.session_state["authentication_status"] = True
    
    # Store user information SECOND
    st.session_state["user_info"] = user_info
    
    # Also set legacy flags for compatibility
    st.session_state["is_logged_in"] = True
    st.session_state["student_profile"] = user_info
    
    # Show success message
    st.success(f"✅ Hoş geldiniz, {user_info['name']}!")
    
    # Small delay for user to see success message
    import time
    time.sleep(1)
    
    # Redirect to Account page
    st.switch_page("pages/2_account.py")


# ==================== MAIN CONTENT ====================

# Header
st.markdown("""
<div class="login-header">
    <div class="login-icon">🦷</div>
    <h1>Dental Tutor </h1>
    <p style="font-size: 1.1rem; opacity: 0.9;">Yapay Zeka Destekli Eğitim Platformu</p>
</div>
""", unsafe_allow_html=True)

# Check if already logged in

if st.session_state.get("authentication_status"):
    st.info("✅ Zaten giriş yapmışsınız!")
    if st.button("🏠 Ana Sayfaya Git", width="stretch", type="primary"):
        st.switch_page("pages/0_home.py")
    st.stop()

# Login Form
st.markdown('<div class="login-form">', unsafe_allow_html=True)

st.markdown("### 🔐 Giriş Yap")

# Load student profiles
profiles = load_student_profiles()

if profiles is None:
    st.error("⚠️ Sistem şu anda kullanılamıyor. Lütfen sistem yöneticisine başvurun.")
    st.stop()

# Login Form (using st.form to prevent premature rerun)
with st.form("login_form", clear_on_submit=False):
    username = st.text_input(
        "Kullanıcı Adı / Öğrenci Numarası",
        placeholder="Örn: 220601026"
    )

    password = st.text_input(
        "Şifre",
        type="password",
        placeholder="Şifrenizi girin"
    )

    # Login button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        submitted = st.form_submit_button("🔓 Giriş Yap", type="primary", use_container_width=True)

# Handle form submission
if submitted:
    if not username or not password:
        st.warning("⚠️ Lütfen kullanıcı adı ve şifrenizi girin.")
    else:
        # Authenticate
        with st.spinner("Doğrulanıyor..."):
            user_info = authenticate_user(username, password, profiles)
        
        if user_info:
            login_user(user_info)
        else:
            st.error("❌ Kullanıcı adı veya şifre hatalı!")

st.markdown('</div>', unsafe_allow_html=True)

st.divider()



# Additional Info
with st.expander("❓ Şifremi Unuttum"):
    st.info("""
    Şifrenizi sıfırlamak için lütfen sistem yöneticinize başvurun.
    
    📧 E-posta: betul.danismaz@istun.edu.tr  
    📞 Telefon: +90 (XXX) XXX XX XX
    """)

with st.expander("📝 Yeni Hesap Oluştur"):
    st.info("""
    Yeni hesap oluşturmak için kayıt formunu doldurmanız gerekmektedir.
    
    🔗 [Kayıt Formuna Git](#) (Yakında aktif olacak)
    """)

st.divider()

# Footer
st.markdown("""
<div style="text-align: center; color: #757575; padding: 2rem 0;">
    <p>🔐 <strong>Güvenli Giriş</strong> | Tüm verileriniz güvenle korunur</p>
    <p><small>© 2025 DentAI - Tüm hakları saklıdır</small></p>
</div>
""", unsafe_allow_html=True)
