"""
Quiz Page - Clinical Knowledge Assessment
==========================================
Standalone theoretical test with embedded MCQ bank.
"""

import os
import sys
import json
import logging
from typing import Dict, List, Any
from pathlib import Path

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import streamlit as st

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def load_questions() -> Dict[str, List[Dict[str, Any]]]:
    """Load MCQ questions from JSON file"""
    try:
        questions_file = Path(parent_dir) / "data" / "mcq_questions.json"
        with open(questions_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        LOGGER.error(f"Failed to load questions: {e}")
        return {}


def main() -> None:
    st.set_page_config(
        page_title="Klinik Bilgi Testi",
        page_icon="📝",
        layout="centered"
    )
    
    st.title("📝 Diş Hekimliği Klinik Bilgi Testi")
    st.caption("Teorik bilginizi ölçün ve güçlü/zayıf alanlarınızı keşfedin")
    
    # Load questions
    all_questions = load_questions()
    
    if not all_questions:
        st.error("❌ Soru bankası yüklenemedi. Lütfen yöneticinize başvurun.")
        st.stop()
    
    # Sidebar: Topic selection
    st.sidebar.header("📚 Konu Seçimi")
    
    topic_map = {
        "Oral Patoloji": "oral_pathology",
        "Enfeksiyöz Hastalıklar": "infectious_diseases",
        "Travmatik Lezyonlar": "traumatic",
        "Tümü (Karma)": "all"
    }
    
    selected_topic = st.sidebar.selectbox(
        "Test konusunu seçin:",
        options=list(topic_map.keys()),
        index=0
    )
    
    topic_key = topic_map[selected_topic]
    
    # Gather questions based on selection
    if topic_key == "all":
        questions = []
        for category_questions in all_questions.values():
            questions.extend(category_questions)
    else:
        questions = all_questions.get(topic_key, [])
    
    if not questions:
        st.warning("⚠️ Bu konu için henüz soru eklenmedi.")
        st.stop()
    
    st.info(f"📊 **{len(questions)} soru** yüklenmiş ({selected_topic})")
    
    # Initialize session state for answers
    if "quiz_answers" not in st.session_state:
        st.session_state.quiz_answers = {}
    
    if "quiz_submitted" not in st.session_state:
        st.session_state.quiz_submitted = False
    
    # Display questions
    st.markdown("---")
    
    for idx, q in enumerate(questions, 1):
        q_id = q.get("id", f"q_{idx}")
        question_text = q.get("question", "")
        options = q.get("options", [])
        correct_option = q.get("correct_option", "")
        explanation = q.get("explanation", "")
        
        st.markdown(f"### Soru {idx}")
        st.markdown(f"**{question_text}**")
        
        # Radio button for options
        selected = st.radio(
            label=f"Seçenekler (Soru {idx})",
            options=options,
            key=f"radio_{q_id}",
            label_visibility="collapsed"
        )
        
        # Store answer
        st.session_state.quiz_answers[q_id] = selected
        
        # Show feedback if submitted
        if st.session_state.quiz_submitted:
            if selected == correct_option:
                st.success("✅ Doğru!")
            else:
                st.error(f"❌ Yanlış! Doğru cevap: **{correct_option}**")
                st.info(f"💡 **Açıklama:** {explanation}")
        
        st.markdown("---")
    
    # Submit button
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if not st.session_state.quiz_submitted:
            if st.button("🔍 Cevapları Kontrol Et", use_container_width=True, type="primary"):
                st.session_state.quiz_submitted = True
                st.rerun()
        else:
            if st.button("🔄 Testi Sıfırla", use_container_width=True):
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.rerun()
    
    # Show score if submitted
    if st.session_state.quiz_submitted:
        correct_count = 0
        total_count = len(questions)
        
        for q in questions:
            q_id = q.get("id", "")
            correct_option = q.get("correct_option", "")
            user_answer = st.session_state.quiz_answers.get(q_id, "")
            
            if user_answer == correct_option:
                correct_count += 1
        
        score_percentage = int((correct_count / total_count) * 100) if total_count > 0 else 0
        
        st.markdown("---")
        st.markdown("## 🎯 Sonuçlar")
        
        # Color-coded score display
        if score_percentage >= 80:
            st.success(f"### 🏆 Mükemmel! Puanınız: **{correct_count}/{total_count}** ({score_percentage}%)")
        elif score_percentage >= 60:
            st.info(f"### 👍 İyi! Puanınız: **{correct_count}/{total_count}** ({score_percentage}%)")
        else:
            st.warning(f"### 📚 Daha fazla çalışma gerekli. Puanınız: **{correct_count}/{total_count}** ({score_percentage}%)")
        
        # Performance breakdown
        st.markdown("#### 📊 Detaylı Analiz")
        st.progress(score_percentage / 100)
        
        st.markdown(f"""
        - **Doğru:** {correct_count} soru
        - **Yanlış:** {total_count - correct_count} soru
        - **Başarı Oranı:** {score_percentage}%
        """)
        
        # Recommendations
        if score_percentage < 80:
            st.markdown("#### 💡 Öneriler")
            st.markdown("""
            - Yanlış cevapladığınız soruların açıklamalarını dikkatlice okuyun
            - İlgili vaka senaryolarını tekrar çözün
            - Zayıf olduğunuz konuları öncelikli çalışın
            """)


if __name__ == "__main__":
    main()
