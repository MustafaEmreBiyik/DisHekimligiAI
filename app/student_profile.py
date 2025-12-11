"""
Öğrenci Profil Sistemi - Dental Tutor AI
"""

import streamlit as st
import json
import os
from datetime import datetime

# Profile data file path
PROFILES_FILE = "data/student_profiles.json"

def load_profiles():
    """Load student profiles from JSON file"""
    if os.path.exists(PROFILES_FILE):
        try:
            with open(PROFILES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_profiles(profiles):
    """Save student profiles to JSON file"""
    os.makedirs(os.path.dirname(PROFILES_FILE), exist_ok=True)
    with open(PROFILES_FILE, 'w', encoding='utf-8') as f:
        json.dump(profiles, f, ensure_ascii=False, indent=2)

def init_student_profile():
    """Initialize student profile in session state"""
    if "student_profile" not in st.session_state:
        st.session_state.student_profile = None
    
    if "is_logged_in" not in st.session_state:
        st.session_state.is_logged_in = False

def create_profile(name, student_id):
    """Create a new student profile"""
    profiles = load_profiles()
    
    profile = {
        "name": name,
        "student_id": student_id,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "last_login": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_score": 0,
        "total_actions": 0,
        "completed_cases": [],
        "action_history": []
    }
    
    profiles[student_id] = profile
    save_profiles(profiles)
    return profile

def login_student(student_id):
    """Login existing student"""
    profiles = load_profiles()
    
    if student_id in profiles:
        profile = profiles[student_id]
        profile["last_login"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        profiles[student_id] = profile
        save_profiles(profiles)
        return profile
    return None

def update_profile_stats(student_id, action_data):
    """Update student profile with new action"""
    profiles = load_profiles()
    
    if student_id in profiles:
        profile = profiles[student_id]
        profile["total_score"] = profile.get("total_score", 0) + action_data.get("score", 0)
        profile["total_actions"] = profile.get("total_actions", 0) + 1
        
        # Add to action history
        if "action_history" not in profile:
            profile["action_history"] = []
        profile["action_history"].append(action_data)
        
        # Update completed cases
        case_id = action_data.get("case_id")
        if case_id and case_id not in profile.get("completed_cases", []):
            if "completed_cases" not in profile:
                profile["completed_cases"] = []
            profile["completed_cases"].append(case_id)
        
        profiles[student_id] = profile
        save_profiles(profiles)
        return profile
    return None

def show_login_form():
    """Display login/register form"""
    st.markdown("### 👤 Öğrenci Girişi")
    
    tab1, tab2 = st.tabs(["🔑 Giriş Yap", "📝 Kayıt Ol"])
    
    with tab1:
        st.markdown("**Mevcut Hesabınızla Giriş Yapın**")
        login_id = st.text_input("Öğrenci Numaranız:", key="login_id", placeholder="Örn: 2021001")
        
        if st.button("Giriş Yap", type="primary", width="stretch"):
            if login_id:
                profile = login_student(login_id)
                if profile:
                    st.session_state.student_profile = profile
                    st.session_state.is_logged_in = True
                    
                    # Load profile stats to session state
                    st.session_state.total_score = profile.get("total_score", 0)
                    st.session_state.total_actions = profile.get("total_actions", 0)
                    st.session_state.completed_cases = set(profile.get("completed_cases", []))
                    st.session_state.action_history = profile.get("action_history", [])
                    
                    st.success(f"✅ Hoş geldiniz, {profile['name']}!")
                    st.rerun()
                else:
                    st.error("❌ Öğrenci numarası bulunamadı. Lütfen kayıt olun.")
            else:
                st.warning("⚠️ Lütfen öğrenci numaranızı girin.")
    
    with tab2:
        st.markdown("**Yeni Hesap Oluşturun**")
        new_name = st.text_input("Adınız Soyadınız:", key="new_name", placeholder="Örn: Ahmet Yılmaz")
        new_id = st.text_input("Öğrenci Numaranız:", key="new_id", placeholder="Örn: 2021001")
        
        if st.button("Kayıt Ol", type="primary", width="stretch"):
            if new_name and new_id:
                profiles = load_profiles()
                if new_id in profiles:
                    st.error("❌ Bu öğrenci numarası zaten kayıtlı. Lütfen giriş yapın.")
                else:
                    profile = create_profile(new_name, new_id)
                    st.session_state.student_profile = profile
                    st.session_state.is_logged_in = True
                    
                    # Initialize session state
                    st.session_state.total_score = 0
                    st.session_state.total_actions = 0
                    st.session_state.completed_cases = set()
                    st.session_state.action_history = []
                    
                    st.success(f"✅ Hesabınız oluşturuldu! Hoş geldiniz, {new_name}!")
                    st.rerun()
            else:
                st.warning("⚠️ Lütfen tüm alanları doldurun.")

def show_profile_card():
    """Display student profile card in sidebar"""
    if st.session_state.get("is_logged_in") and st.session_state.get("student_profile"):
        profile = st.session_state.student_profile
        
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 👤 Profil")
        st.sidebar.info(f"""
**{profile['name']}**  
Öğrenci No: {profile['student_id']}  
Son Giriş: {profile.get('last_login', 'N/A')}
        """)
        
        if st.sidebar.button("🚪 Çıkış Yap", width="stretch"):
            # Save current stats before logout
            if "student_profile" in st.session_state:
                student_id = st.session_state.student_profile["student_id"]
                profiles = load_profiles()
                if student_id in profiles:
                    profiles[student_id]["total_score"] = st.session_state.get("total_score", 0)
                    profiles[student_id]["total_actions"] = st.session_state.get("total_actions", 0)
                    profiles[student_id]["completed_cases"] = list(st.session_state.get("completed_cases", set()))
                    profiles[student_id]["action_history"] = st.session_state.get("action_history", [])
                    save_profiles(profiles)
            
            st.session_state.student_profile = None
            st.session_state.is_logged_in = False
            st.rerun()
