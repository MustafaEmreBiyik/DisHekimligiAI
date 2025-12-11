"""
Silent Evaluator Chat Interface
================================
Clean messaging UI with background evaluation saving.
Students see ONLY the conversation - no scores or warnings during chat.
"""

import os
import sys
import json
import logging
from typing import Optional, List, Tuple, Any, Dict
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from app.student_profile import init_student_profile, show_profile_card
from db.database import SessionLocal, StudentSession, ChatLog, init_db

# Initialize systems
init_student_profile()
init_db()

# Try optional imports
try:
    from app.agent import DentalEducationAgent
except Exception as e:
    DentalEducationAgent = None
    print(f"⚠️ DentalEducationAgent import error: {e}")

LOGGER = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ==================== DATABASE HELPERS ====================

def get_or_create_session(student_id: str, case_id: str) -> int:
    """Get existing session or create new one for student+case combination."""
    db = SessionLocal()
    try:
        # Try to find existing session
        existing = db.query(StudentSession).filter_by(
            student_id=student_id,
            case_id=case_id
        ).first()
        
        if existing:
            return existing.id
        
        # Create new session
        new_session = StudentSession(
            student_id=student_id,
            case_id=case_id,
            current_score=0.0
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return new_session.id
    except Exception as e:
        LOGGER.error(f"Session creation failed: {e}")
        db.rollback()
        return -1
    finally:
        db.close()


def save_message_to_db(
    session_id: int,
    role: str,
    content: str,
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Save chat message to database with optional metadata.
    
    Args:
        session_id: Database session ID
        role: 'user' or 'assistant'
        content: Message text
        metadata: Evaluation results (saved silently, not shown to user)
    """
    if session_id < 0:
        return False
    
    db = SessionLocal()
    try:
        chat_log = ChatLog(
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=metadata,
            timestamp=datetime.utcnow()
        )
        db.add(chat_log)
        db.commit()
        return True
    except Exception as e:
        LOGGER.error(f"Failed to save message: {e}")
        db.rollback()
        return False
    finally:
        db.close()


# ==================== UI CONFIGURATION ====================

CASE_OPTIONS = {
    "Oral Liken Planus (Orta)": "olp_001",
    "Kronik Periodontitis (Zor)": "perio_001",
    "Primer Herpes (Orta)": "herpes_primary_01",
    "Behçet Hastalığı (Zor)": "behcet_01",
    "Sekonder Sifiliz (Zor)": "syphilis_02"
}

DEFAULT_MODEL = "models/gemini-2.5-flash-lite"

# Available model options
MODEL_OPTIONS = [
    "models/gemini-2.5-flash-lite",
    "models/gemini-2.0-flash-lite",
    "models/gemini-1.5-flash"
]


# ==================== MAIN INTERFACE ====================

def main() -> None:
    st.set_page_config(
        page_title="Oral Patoloji Sohbet",
        page_icon="💬",
        layout="centered"
    )
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # ==================== SIDEBAR ====================
    with st.sidebar:
        st.header("📂 Vaka Seçimi")
        
        # Profile card
        show_profile_card()
        
        # Case selector
        selected_case_name = st.selectbox(
            "Aktif Vaka:",
            list(CASE_OPTIONS.keys()),
            key="case_selector"
        )
        selected_case_id = CASE_OPTIONS[selected_case_name]
        
        # Initialize or update current case
        if "current_case_id" not in st.session_state:
            st.session_state.current_case_id = selected_case_id
        
        # Handle case change
        if st.session_state.current_case_id != selected_case_id:
            st.session_state.current_case_id = selected_case_id
            st.session_state.messages = []
            st.session_state.db_session_id = None
            st.success(f"✅ Yeni vaka: {selected_case_name}")
            st.rerun()
        
        st.divider()
        
        # Model selection
        st.header("🤖 Model Ayarları")
        
        # Initialize selected_model if not exists
        if "selected_model" not in st.session_state:
            st.session_state.selected_model = DEFAULT_MODEL
        
        # selectbox widget'ını oluştur; session_state otomatik güncellenecek
        # index'i önceden ayarlanmış değere göre belirle (varsayılan 0)
        try:
            idx = MODEL_OPTIONS.index(st.session_state.selected_model)
        except Exception:
            idx = 0
        st.selectbox("🤖 Model Seçin", MODEL_OPTIONS, index=idx, key="selected_model")
        
        # Controls
        if st.button("🔄 Yeni Sohbet Başlat", width="stretch"):
            st.session_state.messages = []
            st.session_state.db_session_id = None
            st.rerun()
        
        st.markdown("---")
        st.info(f"**API Durumu:** {'✅ Aktif' if GEMINI_API_KEY else '❌ Eksik'}")
        
        # Debug: Agent import durumu
        if DentalEducationAgent is not None:
            st.success("**Agent entegre:** ✅ Başarılı")
        else:
            st.error("**Agent entegre:** ❌ Import hatası (Terminale bakın)")
        
        st.info(f"**Aktif Vaka:** {st.session_state.get('current_case_id', 'Seçilmedi')}")
        st.info(f"**Model:** {st.session_state.selected_model}")
        st.info(f"**Mesaj Sayısı:** {len(st.session_state.get('messages', []))}")

    # ==================== CHAT AREA ====================
    st.title("💬 Oral Patoloji Sohbet")
    st.caption("Eğitimsel bir konuşma deneyimi")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "Merhaba! Size nasıl yardımcı olabilirim?"
            }
        ]
    
    # Initialize or get database session
    if "db_session_id" not in st.session_state or st.session_state.db_session_id is None:
        profile = st.session_state.get("student_profile") or {}
        student_id = profile.get("student_id", "web_user_default")
        st.session_state.db_session_id = get_or_create_session(
            student_id=student_id,
            case_id=st.session_state.current_case_id
        )

    # Initialize agent
    agent_instance = None
    if DentalEducationAgent and GEMINI_API_KEY:
        try:
            # Use selected model from session state
            selected_model = st.session_state.get("selected_model", DEFAULT_MODEL)
            agent_instance = DentalEducationAgent(
                api_key=GEMINI_API_KEY,
                model_name=selected_model
            )
        except Exception as e:
            LOGGER.error(f"Agent initialization failed: {e}")
            st.error("⚠️ Sistem başlatılamadı. Lütfen yöneticinize başvurun.")
            st.stop()
    else:
        st.error("❌ Agent veya API key mevcut değil.")
        st.stop()

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ==================== USER INPUT ====================
    if user_input := st.chat_input("Mesajınızı yazın..."):
        # Display user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
        
        # Save user message to DB (no metadata for user messages)
        save_message_to_db(
            session_id=st.session_state.db_session_id,
            role="user",
            content=user_input,
            metadata=None
        )

        # Process with agent
        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("✍️ Düşünüyor...")

            try:
                # Update agent state with current case
                profile = st.session_state.get("student_profile") or {}
                student_id = profile.get("student_id", "web_user_default")
                
                # Process input through agent
                result = agent_instance.process_student_input(
                    student_id=student_id,
                    raw_action=user_input,
                    case_id=st.session_state.current_case_id
                )
                
                # Extract response text
                response_text = result.get("llm_interpretation", {}).get("explanatory_feedback", "")
                
                if not response_text:
                    response_text = "Üzgünüm, şu anda yanıt veremiyorum."
                
                # Display ONLY the conversation text (no scores, no warnings)
                placeholder.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
                
                # ==================== SILENT SAVE ====================
                # Save evaluation to database WITHOUT showing it to the user
                evaluation_metadata = {
                    "interpreted_action": result.get("llm_interpretation", {}).get("interpreted_action"),
                    "assessment": result.get("assessment", {}),
                    "silent_evaluation": result.get("silent_evaluation", {}),
                    "timestamp": datetime.utcnow().isoformat(),
                    "case_id": st.session_state.current_case_id
                }
                
                save_message_to_db(
                    session_id=st.session_state.db_session_id,
                    role="assistant",
                    content=response_text,
                    metadata=evaluation_metadata
                )
                
                # Log silently (for admin/debug purposes only)
                LOGGER.info(
                    f"[Silent Eval] Action: {evaluation_metadata['interpreted_action']}, "
                    f"Accurate: {evaluation_metadata['silent_evaluation'].get('is_clinically_accurate', 'N/A')}"
                )

            except Exception as e:
                LOGGER.exception(f"Chat processing failed: {e}")
                error_text = "⚠️ Bir hata oluştu. Lütfen tekrar deneyin."
                placeholder.markdown(error_text)
                st.session_state.messages.append({"role": "assistant", "content": error_text})


if __name__ == "__main__":
    main()
