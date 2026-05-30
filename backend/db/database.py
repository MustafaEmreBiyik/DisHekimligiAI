"""
DentAI Database Setup
=====================
SQLAlchemy models and database configuration.
Uses SQLite by default for local development.
"""

import datetime
import os
from pathlib import Path
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlparse, urlsplit, urlunsplit
from typing import Optional
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy import Boolean, Enum
import enum
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==================== DATABASE CONFIGURATION ====================

# SQLite database URL (created under the project root)
# Sprint 2: allow environment override for Alembic + runtime parity.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent

DEFAULT_SQLITE_DB_PATH = PROJECT_ROOT / "db" / "runtime" / "dentai_app.db"
DEFAULT_DATABASE_URL = f"sqlite:///{DEFAULT_SQLITE_DB_PATH.as_posix()}"
RAW_DATABASE_URL = os.getenv("DENTAI_DATABASE_URL") or os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


def _normalize_database_url(database_url: str) -> str:
    """Normalize DB URLs so hosted Postgres works with raw .env secrets."""
    if not database_url.startswith("postgresql"):
        return database_url

    parsed = urlsplit(database_url)
    scheme = parsed.scheme if "+" in parsed.scheme else "postgresql+psycopg"
    netloc = parsed.netloc

    if "@" in netloc:
        auth, host = netloc.rsplit("@", 1)
        if ":" in auth:
            username, password = auth.split(":", 1)
            auth = f"{username}:{quote(unquote(password), safe='')}"
        netloc = f"{auth}@{host}"

    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    query = dict(query_items)
    if "sslmode" not in query and (parsed.hostname or "").endswith(".supabase.co"):
        query_items.append(("sslmode", "require"))

    return urlunsplit(
        (
            scheme,
            netloc,
            parsed.path,
            urlencode(query_items),
            parsed.fragment,
        )
    )


DATABASE_URL = _normalize_database_url(RAW_DATABASE_URL)

# Create the engine. SQLite needs check_same_thread=False.
engine_kwargs = {"echo": False}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
elif DATABASE_URL.startswith("postgresql"):
    engine_kwargs["pool_pre_ping"] = True

engine = create_engine(DATABASE_URL, **engine_kwargs)

# Session factory (new session per database operation)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base (tüm modeller bundan türeyecek)
Base = declarative_base()


# ==================== VERİTABANI MODELLERİ ====================

class UserRole(str, enum.Enum):
    """Role enum for authentication and authorization boundaries."""

    STUDENT = "student"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"

class QuestionType(str, enum.Enum):
    MCQ = "MCQ"
    OPEN_ENDED = "OPEN_ENDED"

class GradingStatus(str, enum.Enum):
    PENDING = "PENDING"
    GRADED = "GRADED"
    PUBLISHED = "PUBLISHED"

class MappingType(str, enum.Enum):
    THEORY_SUPPORT = "theory_support"
    CASE_REINFORCEMENT = "case_reinforcement"
    ASSESSMENT_LINK = "assessment_link"

class ReviewStatus(str, enum.Enum):
    APPROVED = "approved"
    BLOCKED_REVIEW_NEEDED = "blocked_review_needed"
    UNMAPPED = "unmapped"

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


class RubricVersion(Base):
    """
    Rubric Version Snapshot (T-4B)
    --------------------------------
    Stores immutable snapshots of a question's rubric_guide and
    model_answer_outline each time an instructor publishes a rubric change.
    This lets us audit which rubric criteria were in effect when each
    student answer was graded.
    """

    __tablename__ = "rubric_versions"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    version = Column(Integer, nullable=False)          # per-question counter (1, 2, 3 …)
    rubric_guide = Column(Text, nullable=False)
    model_answer_outline = Column(Text, nullable=False)
    change_notes = Column(Text, nullable=True)          # optional instructor comment
    created_by = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)

    # Relationships
    question = relationship("Question", back_populates="rubric_versions")
    answers_graded_with = relationship("QuizAnswer", back_populates="rubric_version_snapshot")

    def __repr__(self):
        return (
            f"<RubricVersion(id={self.id}, question_id={self.question_id}, "
            f"version={self.version}, created_by={self.created_by})>"
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


class Question(Base):
    """
    Oral Pathology Question Bank (S8)
    ---------------------------------
    Stores MCQ and Open-Ended questions.
    """
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(String, unique=True, nullable=False, index=True)
    question_type = Column(Enum(QuestionType), nullable=False)
    question_text = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    is_archived = Column(Boolean, nullable=False, default=False)
    topic_id = Column(String, nullable=False, index=True)
    competency_areas = Column(JSON, nullable=False, default=list)
    bloom_level = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    safety_category = Column(String, nullable=False)
    unit_id = Column(String, nullable=True, index=True)   # e.g. "unit_1_immune_mediated"
    week_number = Column(Integer, nullable=True)           # e.g. 3

    # Protected authoring fields (never exposed to student API)
    options_json = Column(JSON, nullable=True)  # Used for MCQs
    correct_option = Column(String, nullable=True)
    instructor_explanation = Column(Text, nullable=True)
    rubric_guide = Column(Text, nullable=True)
    model_answer_outline = Column(Text, nullable=True)
    max_score = Column(Integer, nullable=False, default=1)
    
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # T-4B: tracks the current (latest) published rubric version for this question
    current_rubric_version = Column(Integer, nullable=True, default=None)

    # Relationships
    case_mappings = relationship("QuestionCaseMapping", back_populates="question", cascade="all, delete-orphan")
    answers = relationship("QuizAnswer", back_populates="question", cascade="all, delete-orphan")
    rubric_versions = relationship("RubricVersion", back_populates="question", cascade="all, delete-orphan", order_by="RubricVersion.version")

    def __repr__(self):
        return f"<Question(id={self.id}, type={self.question_type}, topic={self.topic_id})>"


class QuestionCaseMapping(Base):
    """
    Theory-to-Case Mapping (S8)
    ---------------------------
    Maps a question to multiple clinical cases.
    """
    __tablename__ = "question_case_mappings"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    case_id = Column(String, nullable=False, index=True)
    mapping_type = Column(Enum(MappingType), nullable=False)
    review_status = Column(Enum(ReviewStatus), nullable=False, default=ReviewStatus.UNMAPPED)

    question = relationship("Question", back_populates="case_mappings")

    def __repr__(self):
        return f"<QuestionCaseMapping(question_id={self.question_id}, case_id={self.case_id}, status={self.review_status})>"


class QuizAttempt(Base):
    """
    Quiz Attempt (S8)
    -----------------
    Tracks a student's attempt at a theory module/quiz.
    """
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    session_id = Column(String, nullable=True)
    schedule_id = Column(Integer, ForeignKey("exam_schedules.id"), nullable=True, index=True)
    total_score = Column(Integer, nullable=False, default=0)
    max_score = Column(Integer, nullable=False, default=0)
    time_limit_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    answers = relationship("QuizAnswer", back_populates="attempt", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QuizAttempt(id={self.id}, user_id={self.user_id}, score={self.total_score}/{self.max_score})>"


class QuizAnswer(Base):
    """
    Quiz Answer (S8)
    ----------------
    Stores a student's individual answer to a question.
    """
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    student_response_text = Column(Text, nullable=False)
    auto_score = Column(Integer, nullable=True)
    instructor_score = Column(Integer, nullable=True)
    instructor_feedback = Column(Text, nullable=True)
    grading_status = Column(Enum(GradingStatus), nullable=False, default=GradingStatus.PENDING)
    graded_by_id = Column(String, nullable=True)  # ID of instructor who graded
    graded_at = Column(DateTime, nullable=True)
    # T-4A: AI draft scoring fields
    ai_score_suggestion = Column(Float, nullable=True)   # LLM draft score (0–max_score)
    ai_score_rationale  = Column(Text, nullable=True)    # LLM explanation
    ai_scored_at        = Column(DateTime, nullable=True) # When AI scored

    # T-4B: rubric version snapshot that was in effect when graded
    rubric_version_id = Column(Integer, ForeignKey("rubric_versions.id"), nullable=True, index=True)

    # T-8C: inter-rater (secondary instructor) fields
    secondary_instructor_score = Column(Float, nullable=True)
    secondary_instructor_id = Column(String, nullable=True)
    secondary_graded_at = Column(DateTime, nullable=True)
    inter_rater_delta = Column(Float, nullable=True)

    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("Question", back_populates="answers")
    rubric_version_snapshot = relationship("RubricVersion", back_populates="answers_graded_with")

    def __repr__(self):
        return f"<QuizAnswer(attempt_id={self.attempt_id}, question_id={self.question_id}, status={self.grading_status})>"


class AIScoringLog(Base):
    """Audit log for AI scoring attempts (T-6D)."""
    __tablename__ = "ai_scoring_logs"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("quiz_answers.id"), nullable=False, index=True)
    model_id = Column(String, nullable=False)
    status = Column(String, nullable=False)  # "success" or "error"
    error_message = Column(Text, nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    suggested_score = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)

    def __repr__(self):
        return f"<AIScoringLog(id={self.id}, answer_id={self.answer_id}, status={self.status})>"


class LLMInteractionLog(Base):
    """Per-request audit trail for every LLM API call (S9-C).

    Tracks provider, model, call type, token usage, latency and estimated cost
    to support budget control, rate-limit monitoring and EU AI Act audit requirements.
    """

    __tablename__ = "llm_interaction_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("student_sessions.id"), nullable=True, index=True)
    provider = Column(String, nullable=False, index=True)      # "gemini" | "huggingface"
    model_id = Column(String, nullable=False)                  # exact model string used
    call_type = Column(String, nullable=False, index=True)     # "interpretation" | "coach" | "validation" | "scoring"
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    estimated_cost_usd = Column(Float, nullable=True)          # null when not computable
    success = Column(Boolean, nullable=False, default=True, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)

    def __repr__(self):
        return (
            f"<LLMInteractionLog(id={self.id}, provider={self.provider}, "
            f"model={self.model_id}, call_type={self.call_type}, "
            f"latency_ms={self.latency_ms}, success={self.success})>"
        )


class Notification(Base):
    """User notifications (T-7A)."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    type = Column(String, nullable=False)  # "score_published", etc.
    payload_json = Column(JSON, nullable=False, default=dict)
    is_read = Column(Boolean, nullable=False, default=False, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow, index=True)

    def __repr__(self):
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type}, is_read={self.is_read})>"


class ExamSchedule(Base):
    """Scheduled exam packages (T-8A)."""
    __tablename__ = "exam_schedules"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    question_ids = Column(JSON, nullable=False, default=list)
    opens_at = Column(DateTime, nullable=False)
    closes_at = Column(DateTime, nullable=False)
    time_limit_minutes = Column(Integer, nullable=True)
    created_by = Column(String, nullable=False, index=True)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<ExamSchedule(id={self.id}, title={self.title}, opens_at={self.opens_at})>"


class MiniCase(Base):
    """Lightweight clinical vignettes linked to theory questions (T-5B)."""
    __tablename__ = "mini_cases"

    id = Column(Integer, primary_key=True, index=True)
    mini_case_id = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    linked_topic_ids = Column(JSON, nullable=True)
    clinical_vignette = Column(Text, nullable=False)
    key_findings = Column(JSON, nullable=True)
    question_ids = Column(JSON, nullable=True)
    learning_objectives = Column(JSON, nullable=True)
    difficulty = Column(String, nullable=False, default="medium")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<MiniCase(mini_case_id={self.mini_case_id}, title={self.title})>"


class ReviewSchedule(Base):
    """SM-2 spaced repetition schedule for a student's question (S10-C).

    Tracks interval, ease factor and due date so the student is reminded to
    review weak questions at optimal spacing intervals.
    """

    __tablename__ = "review_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    due_date = Column(DateTime, nullable=False, index=True)
    interval_days = Column(Integer, nullable=False, default=1)
    ease_factor = Column(Float, nullable=False, default=2.5)
    repetitions = Column(Integer, nullable=False, default=0)
    last_reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)

    question = relationship("Question", foreign_keys=[question_id])

    def __repr__(self):
        return (
            f"<ReviewSchedule(id={self.id}, user_id={self.user_id}, "
            f"question_id={self.question_id}, due_date={self.due_date}, "
            f"interval_days={self.interval_days})>"
        )


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
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", DATABASE_URL.replace("%", "%%"))
    return config


def _connection_guidance_message(exc: Exception) -> Optional[str]:
    """Return actionable guidance for known hosted Postgres connectivity failures."""
    message = str(exc)
    hostname = urlsplit(DATABASE_URL).hostname or ""

    if not DATABASE_URL.startswith("postgresql"):
        return None

    is_supabase_direct_host = hostname.endswith(".supabase.co") and ".pooler.supabase.com" not in hostname
    if is_supabase_direct_host and "Network is unreachable" in message:
        return (
            "Supabase direct connections resolve to IPv6 by default, and this Docker runtime "
            f"cannot reach the resolved IPv6 address for {hostname}. "
            "Use the Supabase Session pooler connection string from Dashboard > Connect "
            "(host like `aws-0-<region>.pooler.supabase.com`, port `5432`) or enable the "
            "Supabase IPv4 add-on for the direct `db.<project-ref>.supabase.co` hostname."
        )

    return None


def _ensure_schema_is_current() -> None:
    """Fail fast when the runtime schema is not at Alembic head."""
    config = _get_alembic_config()
    script = ScriptDirectory.from_config(config)
    expected_heads = tuple(script.get_heads())

    try:
        with engine.connect() as connection:
            migration_context = MigrationContext.configure(connection)
            current_heads = tuple(migration_context.get_current_heads())
    except Exception as exc:
        guidance = _connection_guidance_message(exc)
        if guidance:
            raise RuntimeError(guidance) from exc
        raise

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
                            total_score += score
                            total_actions += 1
                            completed_cases.add(session.case_id)
                    except (json.JSONDecodeError, AttributeError, TypeError):
                        pass

        return {
            "action_history": action_history,
            "total_score": total_score,
            "total_actions": total_actions,
            "completed_cases": completed_cases,
        }
    finally:
        db.close()
