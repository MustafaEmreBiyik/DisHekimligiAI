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
from pathlib import Path

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from app.student_profile import init_student_profile
from app.frontend.components import render_sidebar, DEFAULT_MODEL
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

# ==================== UI STYLING ====================

def apply_custom_css():
    """Apply custom CSS for professional UI"""
    st.markdown("""
    <style>
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Chat message styling */
    .stChatMessage[data-testid="user-message"] {
        background-color: #f0f0f0 !important;
        border-left: 4px solid #888 !important;
    }
    
    .stChatMessage[data-testid="assistant-message"] {
        background-color: #e3f2fd !important;
        border-left: 4px solid #2196F3 !important;
    }
    
    /* Patient card styling */
    .patient-card {
        padding: 1rem;
        border-radius: 8px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-bottom: 1rem;
    }
    
    .patient-info {
        font-size: 0.9rem;
        margin: 0.3rem 0;
    }
    
    .critical-info {
        background-color: #ff5252;
        padding: 0.5rem;
        border-radius: 4px;
        margin: 0.5rem 0;
        font-weight: bold;
    }
    
    /* Clinical image container */
    .stImage {
        border: 2px solid #2196F3;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        padding: 0.5rem;
    }
    
    /* Button styling */
    .stButton>button {
        border-radius: 8px;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)


def render_patient_card(case_id: str):
    """Render persistent patient information card in sidebar"""
    case_data = load_case_data(case_id)
    
    if not case_data:
        st.sidebar.warning("⚠️ Hasta bilgisi yüklenemedi")
        return
    
    # Handle both Turkish and English keys
    patient = case_data.get("patient") or case_data.get("hasta_profili") or {}
    
    # Extract patient info with fallbacks
    age = patient.get("age") or patient.get("yas") or "Bilinmiyor"
    gender = patient.get("gender") or patient.get("cinsiyet") or "Bilinmiyor"
    complaint = patient.get("chief_complaint") or patient.get("sikayet") or "Belirtilmemiş"
    medical_history = patient.get("medical_history") or patient.get("tibbi_gecmis") or []
    allergies = patient.get("allergies") or patient.get("alerjiler") or []
    medications = patient.get("medications") or patient.get("ilaclar") or []
    
    # Render card in sidebar
    with st.sidebar:
        with st.expander("📋 HASTA KARTI", expanded=True):
            # Basic info
            st.markdown(f"**Yaş/Cinsiyet:** {age} / {gender}")
            st.markdown(f"**Şikayet:** {complaint}")
            
            st.markdown("---")
            
            # Critical: Allergies
            if allergies and len(allergies) > 0 and allergies[0] != "Yok":
                st.error("⚠️ **ALERJİ VAR!**")
                for allergy in allergies:
                    st.markdown(f"🔴 {allergy}")
            else:
                st.success("✅ Bilinen alerji yok")
            
            # Medical History
            if medical_history and len(medical_history) > 0 and medical_history[0] != "Yok":
                st.warning("📋 **Tıbbi Geçmiş:**")
                for condition in medical_history:
                    # Highlight critical conditions
                    if any(keyword in str(condition).lower() for keyword in ["diyabet", "diabetes", "kalp", "pacemaker", "hipertansiyon"]):
                        st.markdown(f"🔴 **{condition}**")
                    else:
                        st.markdown(f"• {condition}")
            
            # Medications
            if medications and len(medications) > 0 and medications[0] != "Yok":
                st.info("💊 **İlaçlar:**")
                for med in medications:
                    st.markdown(f"• {med}")


# ==================== HELPER FUNCTIONS ====================

def load_case_data(case_id: str) -> Optional[Dict[str, Any]]:
    """Load case data from case_scenarios.json"""
    try:
        case_file = Path(parent_dir) / "data" / "case_scenarios.json"
        with open(case_file, "r", encoding="utf-8") as f:
            cases = json.load(f)
        for case in cases:
            if case.get("case_id") == case_id:
                return case
        return None
    except Exception as e:
        LOGGER.error(f"Failed to load case data: {e}")
        return None


def get_finding_media(case_data: Dict[str, Any], finding_ids: List[str]) -> Optional[str]:
    """
    Get media path for revealed findings.
    Returns the first media path found in the revealed findings.
    """
    if not case_data or not finding_ids:
        return None
    
    hidden_findings = case_data.get("hidden_findings", [])
    if not hidden_findings:
        # Try Turkish key name
        hidden_findings = case_data.get("gizli_bulgular", [])
    
    for finding in hidden_findings:
        finding_id = finding.get("finding_id") or finding.get("bulgu_id")
        if finding_id in finding_ids:
            media_path = finding.get("media")
            if media_path:
                # Check if file exists
                full_path = Path(parent_dir) / media_path
                if full_path.exists():
                    return str(full_path)
    return None


# ==================== DATABASE HELPERS ====================

def get_or_create_session(student_id: str, case_id: str) -> int:
    """
    Get existing session or create new one for student+case combination.
    ALWAYS returns the most recent session for this student+case.
    """
    db = SessionLocal()
    try:
        # Find the most recent session for this student+case
        existing = db.query(StudentSession).filter_by(
            student_id=student_id,
            case_id=case_id
        ).order_by(StudentSession.start_time.desc()).first()
        
        if existing:
            LOGGER.info(f"Reusing session {existing.id} for {student_id} on {case_id}")
            return existing.id
        
        # Create new session only if none exists
        new_session = StudentSession(
            student_id=student_id,
            case_id=case_id,
            current_score=0.0
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        LOGGER.info(f"Created new session {new_session.id} for {student_id} on {case_id}")
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
    Updates session score if metadata contains assessment.
    
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
        # Save chat log
        chat_log = ChatLog(
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=metadata,
            timestamp=datetime.utcnow()
        )
        db.add(chat_log)
        # NOTE:
        # Session score is now updated centrally by ScenarioManager (via agent.process_student_input).
        # Avoid double-counting here.
        
        db.commit()
        return True
    except Exception as e:
        LOGGER.error(f"Failed to save message: {e}")
        db.rollback()
        return False
    finally:
        db.close()


# ==================== MAIN INTERFACE ====================

def main() -> None:
    st.set_page_config(
        page_title="Oral Patoloji Sohbet",
        page_icon="💬",
        layout="centered"
    )
    
    # Apply custom CSS
    apply_custom_css()
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # ==================== SIDEBAR ====================
    def reset_chat():
        """Callback to reset chat state"""
        st.session_state.messages = []
        st.session_state.db_session_id = None
        st.rerun()
    
    def finish_case():
        """Callback to finish case and save results"""
        from db.database import save_exam_result, SessionLocal, StudentSession
        
        # Get current session score
        if st.session_state.db_session_id:
            db = SessionLocal()
            try:
                session = db.query(StudentSession).filter_by(id=st.session_state.db_session_id).first()
                if session:
                    # Save exam result
                    profile = st.session_state.get("student_profile") or {}
                    user_id = profile.get("student_id", "web_user_default")
                    
                    result = save_exam_result(
                        user_id=user_id,
                        case_id=st.session_state.current_case_id,
                        score=int(session.current_score),
                        max_score=100,  # You can adjust this based on case
                        details={"session_id": session.id}
                    )
                    
                    if result:
                        st.session_state.case_completed = True
                        st.success(f"✅ Vaka tamamlandı! Skorunuz: {int(session.current_score)} puan kaydedildi!")
                    else:
                        st.error("❌ Skor kaydedilemedi.")
            finally:
                db.close()
    
    # Render reusable sidebar
    sidebar_data = render_sidebar(
        page_type="chat",
        show_case_selector=True,
        show_model_selector=True,
        custom_actions={
            "🔄 Yeni Sohbet": reset_chat,
            "✅ Vakayı Bitir": finish_case
        }
    )
    
    # Render patient card (CRITICAL: Always visible)
    current_case = st.session_state.get("current_case_id", "olp_001")
    render_patient_card(current_case)

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
    # CRITICAL: Always verify session exists for current case
    profile = st.session_state.get("student_profile") or {}
    student_id = profile.get("student_id", "web_user_default")
    
    # Check if we need to refresh session ID
    need_new_session = (
        "db_session_id" not in st.session_state or 
        st.session_state.db_session_id is None or
        st.session_state.db_session_id < 0
    )
    
    if need_new_session:
        st.session_state.db_session_id = get_or_create_session(
            student_id=student_id,
            case_id=st.session_state.current_case_id
        )
        LOGGER.info(f"Session initialized: {st.session_state.db_session_id} for case {st.session_state.current_case_id}")

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
            
            # Display clinical image if this message revealed findings with media
            if msg["role"] == "assistant" and "metadata" in msg:
                metadata = msg.get("metadata", {})
                revealed = metadata.get("revealed_findings", [])
                
                if revealed:
                    # Load current case data
                    case_data = load_case_data(st.session_state.current_case_id)
                    media_path = get_finding_media(case_data, revealed)
                    
                    if media_path:
                        st.image(media_path, caption="🔬 Klinik Görünüm", width=400)

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
                
                # ==================== EXTRACT REVEALED FINDINGS ====================
                # Extract revealed findings from assessment for image display
                revealed_findings = []
                assessment = result.get("assessment", {})
                
                # DEBUG: Log full result structure
                LOGGER.info(f"[DEBUG] Full result keys: {result.keys()}")
                LOGGER.info(f"[DEBUG] Assessment: {assessment}")
                
                if assessment and "state_updates" in assessment:
                    revealed_findings = assessment["state_updates"].get("revealed_findings", [])
                    LOGGER.info(f"[DEBUG] Revealed findings: {revealed_findings}")
                else:
                    LOGGER.warning("[DEBUG] No state_updates in assessment!")
                
                # Create evaluation metadata
                evaluation_metadata = {
                    "interpreted_action": result.get("llm_interpretation", {}).get("interpreted_action"),
                    "assessment": assessment,
                    "silent_evaluation": result.get("silent_evaluation", {}),
                    "revealed_findings": revealed_findings,
                    "timestamp": datetime.utcnow().isoformat(),
                    "case_id": st.session_state.current_case_id
                }
                
                # Store message with metadata for image display
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": response_text,
                    "metadata": evaluation_metadata
                })
                
                # Display clinical image if findings were revealed
                if revealed_findings:
                    LOGGER.info(f"[DEBUG] Attempting to display image for findings: {revealed_findings}")
                    case_data = load_case_data(st.session_state.current_case_id)
                    LOGGER.info(f"[DEBUG] Case data loaded: {case_data is not None}")
                    media_path = get_finding_media(case_data, revealed_findings)
                    LOGGER.info(f"[DEBUG] Media path: {media_path}")
                    if media_path:
                        st.image(media_path, caption="🔬 Klinik Görünüm", width=400)
                        LOGGER.info(f"[DEBUG] Image displayed successfully!")
                    else:
                        LOGGER.warning(f"[DEBUG] No media path found for findings: {revealed_findings}")
                else:
                    LOGGER.warning("[DEBUG] No revealed findings to display image")
                
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
