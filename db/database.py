"""
DentAI Database Setup
=====================
SQLAlchemy modelleri ve veritabanı konfigürasyonu.
Streamlit uygulaması için SQLite kullanır.
"""

import datetime
import os
from pathlib import Path
from urllib.parse import urlparse
from typing import Optional
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy import Boolean, Enum
import enum
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==================== VERİTABANI KONFIGÜRASYONU ====================

# SQLite veritabanı URL'i (proje kök dizininde oluşturulacak)
# Sprint 2: allow environment override for Alembic + runtime parity.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQLITE_DB_PATH = PROJECT_ROOT / "db" / "runtime" / "dentai_app.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_DB_PATH.as_posix()}"
DATABASE_URL = os.getenv("DENTAI_DATABASE_URL", DEFAULT_DATABASE_URL)

# Engine oluştur (Streamlit için check_same_thread=False kritik!)
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False  # True yaparsanız SQL sorgularını görebilirsiniz (debug için)
)

# Session factory (her veritabanı işlemi için yeni session)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base (tüm modeller bundan türeyecek)
Base = declarative_base()


# ==================== VERİTABANI MODELLERİ ====================

class UserRole(str, enum.Enum):
    """Role enum for authentication and authorization boundaries."""

    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"

class StudentSession(Base):
    """
    Öğrenci Oturumu Tablosu
    -----------------------
    Her öğrencinin bir vaka üzerindeki çalışma oturumunu takip eder.
    """
    __tablename__ = "student_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, nullable=False, index=True)  # Öğrenci kimliği
    case_id = Column(String, nullable=False)  # Hangi vaka üzerinde çalışıyor
    current_score = Column(Float, default=0.0)  # Anlık puan
    # Simulation state (JSON string). Stores patient context, revealed findings, progress, etc.
    state_json = Column(Text, default="{}")
    start_time = Column(DateTime, default=datetime.datetime.utcnow)  # Oturum başlangıç zamanı

    # İlişki: Bir oturumun birden fazla chat mesajı olabilir
    chat_logs = relationship("ChatLog", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StudentSession(id={self.id}, student={self.student_id}, case={self.case_id}, score={self.current_score})>"

class User(Base):
    """
    Application user table.
    Uses soft-delete fields so accounts can be archived instead of hard deleted.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, nullable=False, index=True)  # student_id for now
    display_name = Column(String, nullable=False)
    email = Column(String, nullable=True, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, role={self.role}, archived={self.is_archived})>"


class CaseDefinition(Base):
    """Canonical case catalog used for DB-backed content imports."""

    __tablename__ = "case_definitions"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, unique=True, nullable=False, index=True)
    schema_version = Column(String, nullable=False, default="2.0")
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    estimated_duration_minutes = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    learning_objectives = Column(JSON, nullable=False, default=list)
    prerequisite_competencies = Column(JSON, nullable=False, default=list)
    competency_tags = Column(JSON, nullable=False, default=list)
    initial_state = Column(String, nullable=False)
    states_json = Column(JSON, nullable=False, default=dict)
    patient_info_json = Column(JSON, nullable=False, default=dict)
    rules_json = Column(JSON, nullable=False, default=list)
    source_payload = Column(JSON, nullable=False, default=dict)
    is_archived = Column(Boolean, nullable=False, default=False, index=True)
    archived_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    def __repr__(self):
        return f"<CaseDefinition(id={self.id}, case_id={self.case_id}, schema={self.schema_version})>"


class CasePublishHistory(Base):
    """Versioned publish history snapshots for case catalog changes."""

    __tablename__ = "case_publish_history"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, nullable=False, index=True)
    version = Column(Integer, nullable=False)
    change_notes = Column(Text, nullable=False)
    published_by = Column(String, nullable=False, index=True)
    published_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)
    snapshot_json = Column(JSON, nullable=False, default=dict)

    def __repr__(self):
        return (
            f"<CasePublishHistory(id={self.id}, case_id={self.case_id}, "
            f"version={self.version}, published_by={self.published_by})>"
        )


class RecommendationSnapshot(Base):
    """Explainable recommendation records persisted for auditability."""

    __tablename__ = "recommendation_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    case_id = Column(String, nullable=False, index=True)
    reason_code = Column(String, nullable=False)
    reason_text = Column(Text, nullable=False)
    priority_score = Column(Integer, nullable=False)
    algorithm_version = Column(String, nullable=False)
    is_spotlight = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)

    def __repr__(self):
        return (
            f"<RecommendationSnapshot(id={self.id}, user_id={self.user_id}, "
            f"case_id={self.case_id}, reason_code={self.reason_code})>"
        )


class CoachHint(Base):
    """Stored coach hints for per-session usage limits and auditability."""

    __tablename__ = "coach_hints"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("student_sessions.id"), nullable=False, index=True)
    user_id = Column(String, nullable=False, index=True)
    hint_level = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)

    def __repr__(self):
        return (
            f"<CoachHint(id={self.id}, session_id={self.session_id}, "
            f"user_id={self.user_id}, hint_level={self.hint_level})>"
        )


class ValidatorAuditLog(Base):
    """Audit log for every validator invocation in chat flow."""

    __tablename__ = "validator_audit_log"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("student_sessions.id"), nullable=False, index=True)
    action = Column(String, nullable=False)
    validator_used = Column(String, nullable=False)
    safety_violation = Column(Boolean, nullable=False, default=False)
    clinical_accuracy = Column(String, nullable=True)
    response_time_ms = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)

    def __repr__(self):
        return (
            f"<ValidatorAuditLog(id={self.id}, session_id={self.session_id}, "
            f"validator_used={self.validator_used}, safety_violation={self.safety_violation})>"
        )

class ChatLog(Base):
    """
    Sohbet Geçmişi Tablosu
    ----------------------
    Öğrenci-AI arasındaki tüm mesajları kaydeder.
    MedGemma validasyon sonuçlarını metadata_json alanında saklar.
    """
    __tablename__ = "chat_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("student_sessions.id"), nullable=False)  # Hangi oturuma ait
    role = Column(String, nullable=False)  # 'user', 'assistant', veya 'system_validator'
    content = Column(Text, nullable=False)  # Mesaj içeriği
    metadata_json = Column(JSON, nullable=True)  # MedGemma analiz sonuçları (JSON formatında)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)  # Mesaj zamanı

    # İlişki: Her chat log bir oturuma aittir
    session = relationship("StudentSession", back_populates="chat_logs")

    def __repr__(self):
        return f"<ChatLog(id={self.id}, session_id={self.session_id}, role={self.role})>"


class ExamResult(Base):
    """
    Sınav Sonuçları Tablosu
    ------------------------
    Öğrencilerin tamamlanan vaka sonuçlarını ve detaylı skorlarını saklar.
    """
    __tablename__ = "exam_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)  # Öğrenci kimliği
    case_id = Column(String, nullable=False, index=True)  # Hangi vaka
    score = Column(Integer, nullable=False)  # Elde edilen puan
    max_score = Column(Integer, nullable=False)  # Maksimum olası puan
    completed_at = Column(DateTime, default=datetime.datetime.utcnow)  # Tamamlanma zamanı
    details_json = Column(Text, nullable=True)  # Detaylı breakdown (JSON string)

    def __repr__(self):
        return f"<ExamResult(id={self.id}, user={self.user_id}, case={self.case_id}, score={self.score}/{self.max_score})>"


class FeedbackLog(Base):
    """
    Geri Bildirim Tablosu
    ---------------------
    Öğrencilerin vaka tamamlama sonrası verdiği nitel geri bildirimleri saklar.
    Akademik araştırma için kritik veri.
    """
    __tablename__ = "feedback_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("student_sessions.id"), nullable=False)  # Hangi oturuma ait
    student_id = Column(String, nullable=False, index=True)  # Öğrenci kimliği
    case_id = Column(String, nullable=False, index=True)  # Hangi vaka
    rating = Column(Integer, nullable=False)  # 1-5 yıldız
    comment = Column(Text, nullable=True)  # Serbest metin yorumu
    submitted_at = Column(DateTime, default=datetime.datetime.utcnow)  # Gönderim zamanı

    def __repr__(self):
        return f"<FeedbackLog(id={self.id}, student={self.student_id}, case={self.case_id}, rating={self.rating})>"


# ==================== VERİTABANI FONKSİYONLARI ====================

def init_db():
    """
    Prepare the database path and verify schema readiness.
    Live schema creation and mutation are Alembic-only.
    """
    _ensure_sqlite_parent_dir()
    _ensure_schema_is_current()


def _sqlite_db_file_path() -> Optional[str]:
    """Resolve the SQLite file path from DATABASE_URL."""
    try:
        parsed = urlparse(DATABASE_URL)
        if parsed.scheme != "sqlite":
            return None

        # sqlite:///d:/path/to/db/runtime/dentai_app.db -> path like /d:/path/...
        path = parsed.path
        if not path:
            return None

        # Strip leading '/' on Windows paths like '/d:/path/to/file.db'
        while path.startswith("/"):
            path = path[1:]
        return os.path.normpath(path)
    except Exception:
        return None


def _ensure_sqlite_parent_dir() -> None:
    """Create the SQLite parent directory before the first connection attempt."""
    db_file = _sqlite_db_file_path()
    if not db_file:
        return

    Path(db_file).parent.mkdir(parents=True, exist_ok=True)


def _get_alembic_config() -> Config:
    """Build an Alembic config that matches the runtime database URL."""
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))
    return config


def _ensure_schema_is_current() -> None:
    """Fail fast when the runtime schema is not at Alembic head."""
    config = _get_alembic_config()
    script = ScriptDirectory.from_config(config)
    expected_heads = tuple(script.get_heads())

    with engine.connect() as connection:
        migration_context = MigrationContext.configure(connection)
        current_heads = tuple(migration_context.get_current_heads())

    if set(current_heads) == set(expected_heads):
        return

    current_display = ", ".join(current_heads) if current_heads else "uninitialized"
    expected_display = ", ".join(expected_heads) if expected_heads else "none"
    raise RuntimeError(
        "Database schema is not at the required Alembic revision. "
        f"Current revision(s): {current_display}. "
        f"Expected revision(s): {expected_display}. "
        "Run `..\\.venv\\Scripts\\python.exe -m alembic upgrade head` before starting the API."
    )


def get_db():
    """
    Veritabanı session generator (Dependency Injection için).
    
    Kullanım örneği:
    ---------------
    db = next(get_db())
    try:
        # Veritabanı işlemleri
        db.add(new_session)
        db.commit()
    finally:
        db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== TEST BLOĞU ====================

if __name__ == "__main__":
    """
    Bu dosyayı doğrudan çalıştırarak veritabanı hazırlığını doğrulayabilirsiniz:
    python app/db/database.py
    """
    print("Checking database schema readiness...")
    init_db()
    print("Database schema is at Alembic head.")
    print(f"Database URL: {DATABASE_URL}")


# ==================== HELPER FUNCTIONS ====================

def save_exam_result(user_id: str, case_id: str, score: int, max_score: int, details: dict = None):
    """
    Save completed exam result to database.
    
    Args:
        user_id: Student identifier
        case_id: Case identifier
        score: Points earned
        max_score: Maximum possible points
        details: Additional breakdown info (optional)
    
    Returns:
        ExamResult object or None if error
    """
    import json
    
    db = SessionLocal()
    try:
        result = ExamResult(
            user_id=user_id,
            case_id=case_id,
            score=score,
            max_score=max_score,
            details_json=json.dumps(details) if details else None
        )
        db.add(result)
        db.commit()
        db.refresh(result)
        return result
    except Exception as e:
        print(f"Error saving exam result: {e}")
        db.rollback()
        return None
    finally:
        db.close()


def get_user_stats(user_id: str):
    """
    Get comprehensive statistics for a user.
    
    Args:
        user_id: Student identifier
    
    Returns:
        dict with keys:
            - total_solved: Number of completed cases
            - avg_score: Average score percentage
            - user_level: Level based on performance
            - total_points: Total points earned
            - case_breakdown: List of individual case results
    """
    db = SessionLocal()
    try:
        # Get all exam results for this user
        results = db.query(ExamResult).filter_by(user_id=user_id).all()
        
        if not results:
            return {
                "total_solved": 0,
                "avg_score": 0,
                "user_level": "Başlangıç",
                "total_points": 0,
                "case_breakdown": []
            }
        
        # Calculate stats
        total_solved = len(results)
        total_points = sum(r.score for r in results)
        total_max = sum(r.max_score for r in results)
        avg_score = int((total_points / total_max * 100)) if total_max > 0 else 0
        
        # Determine user level
        if avg_score >= 90:
            user_level = "Uzman"
        elif avg_score >= 75:
            user_level = "İleri"
        elif avg_score >= 60:
            user_level = "Orta"
        else:
            user_level = "Başlangıç"
        
        # Case breakdown
        case_breakdown = [
            {
                "case_id": r.case_id,
                "score": r.score,
                "max_score": r.max_score,
                "percentage": int(r.score / r.max_score * 100) if r.max_score > 0 else 0,
                "completed_at": r.completed_at.strftime("%Y-%m-%d %H:%M")
            }
            for r in results
        ]
        
        return {
            "total_solved": total_solved,
            "avg_score": avg_score,
            "user_level": user_level,
            "total_points": total_points,
            "case_breakdown": case_breakdown
        }
    
    except Exception as e:
        print(f"Error getting user stats: {e}")
        return {
            "total_solved": 0,
            "avg_score": 0,
            "user_level": "Başlangıç",
            "total_points": 0,
            "case_breakdown": []
        }
    finally:
        db.close()


def get_student_detailed_history(user_id: str):
    """
    Get detailed action history for a student for analytics.
    This replaces the inline load_student_stats() logic in pages/5_stats.py.
    
    Args:
        user_id: Student identifier
    
    Returns:
        dict with keys:
            - action_history: List of action records with timestamp, case_id, action, score, outcome
            - total_score: Sum of all scores
            - total_actions: Count of actions
            - completed_cases: Set of unique case IDs
    """
    import json
    
    db = SessionLocal()
    try:
        # Get all sessions for this student
        sessions = db.query(StudentSession).filter_by(student_id=user_id).all()
        
        if not sessions:
            return {
                "action_history": [],
                "total_score": 0,
                "total_actions": 0,
                "completed_cases": set()
            }
        
        action_history = []
        total_score = 0
        total_actions = 0
        completed_cases = set()
        
        for session in sessions:
            # Get chat logs for this session (only assistant messages have evaluation metadata)
            logs = db.query(ChatLog).filter_by(
                session_id=session.id,
                role="assistant"
            ).all()
            
            for log in logs:
                if log.metadata_json:
                    try:
                        # Parse metadata
                        metadata = log.metadata_json if isinstance(log.metadata_json, dict) else json.loads(log.metadata_json)
                        
                        # Extract action info
                        interpreted_action = metadata.get("interpreted_action", "unknown")
                        assessment = metadata.get("assessment", {})
                        score = assessment.get("score", 0)
                        outcome = assessment.get("rule_outcome", "N/A")
                        
                        # Only count if it's an ACTION (not general chat)
                        if interpreted_action and interpreted_action not in ["general_chat", "error"]:
                            action_record = {
                                "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "N/A",
                                "case_id": metadata.get("case_id", session.case_id),
                                "action": interpreted_action,
                                "score": score,
                                "outcome": outcome
                            }
                            action_history.append(action_record)
                            total_score += score
                            total_actions += 1
                            completed_cases.add(session.case_id)
                    
                    except Exception as e:
                        print(f"Error parsing metadata: {e}")
                        continue
        
        return {
            "action_history": action_history,
            "total_score": total_score,
            "total_actions": total_actions,
            "completed_cases": completed_cases
        }
    
    except Exception as e:
        print(f"Database error in get_student_detailed_history: {e}")
        return {
            "action_history": [],
            "total_score": 0,
            "total_actions": 0,
            "completed_cases": set()
        }
    finally:
        db.close()
 
