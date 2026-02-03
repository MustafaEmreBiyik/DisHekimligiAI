"""
DentAI Database Setup
=====================
SQLAlchemy models and database configuration.
Supports SQLite (Local) and PostgreSQL (Production).
"""

import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# ==================== VERİTABANI KONFIGÜRASYONU ====================

# Environment variable'dan DB URL'i al. Yoksa default SQLite kullan.
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # Render/Heroku gibi platformlar 'postgres://' verebilir, SQLAlchemy için 'postgresql://' olmalı
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    
    # PostgreSQL için connect_args gerekmez (veya SSL vs için gerekebilir)
    engine_kwargs = {}
else:
    # Lokal geliştirme için SQLite
    DATABASE_URL = "sqlite:///./dentai_app.db"
    # Streamlit + SQLite için check_same_thread=False kritik!
    engine_kwargs = {"connect_args": {"check_same_thread": False}}

# Engine oluştur
engine = create_engine(
    DATABASE_URL,
    echo=False,  # True yaparsanız SQL sorgularını görebilirsiniz (debug için)
    **engine_kwargs
)

# Session factory (her veritabanı işlemi için yeni session)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative Base (tüm modeller bundan türeyecek)
Base = declarative_base()


# ==================== VERİTABANI MODELLERİ ====================

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
    start_time = Column(DateTime, default=datetime.datetime.utcnow)  # Oturum başlangıç zamanı

    # İlişki: Bir oturumun birden fazla chat mesajı olabilir
    chat_logs = relationship("ChatLog", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StudentSession(id={self.id}, student={self.student_id}, case={self.case_id}, score={self.current_score})>"


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


# ==================== VERİTABANI FONKSİYONLARI ====================

def init_db():
    """
    Veritabanını başlat (tüm tabloları oluştur).
    Uygulama ilk çalıştırıldığında çağrılmalı.
    """
    Base.metadata.create_all(bind=engine)


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
    Bu dosyayı doğrudan çalıştırarak veritabanını oluşturabilirsiniz:
    python app/db/database.py
    """
    print("🚀 Veritabanı oluşturuluyor...")
    init_db()
    print("✅ Database created successfully!")
    print(f"📁 Dosya konumu: {DATABASE_URL}")
    
    # Test: Örnek bir session oluştur
    db = SessionLocal()
    try:
        test_session = StudentSession(
            student_id="test_student_001",
            case_id="olp_001",
            current_score=0.0
        )
        db.add(test_session)
        db.commit()
        db.refresh(test_session)
        
        print(f"✅ Test session oluşturuldu: {test_session}")
        
        # Test: Örnek bir chat log ekle
        test_chat = ChatLog(
            session_id=test_session.id,
            role="user",
            content="Hastanın tıbbi geçmişini öğrenmek istiyorum.",
            metadata_json=None
        )
        db.add(test_chat)
        db.commit()
        
        print(f"✅ Test chat log oluşturuldu: {test_chat}")
        print("\n🎉 Veritabanı testi başarılı!")
        
    except Exception as e:
        print(f"❌ Test sırasında hata: {e}")
        db.rollback()
    finally:
        db.close()
 