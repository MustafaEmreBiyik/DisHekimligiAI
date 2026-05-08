"""Veritabanı yapısını ve içeriğini kontrol et"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from db.database import SessionLocal, StudentSession, ChatLog
from sqlalchemy import inspect
import json

db = SessionLocal()
inspector = inspect(db.bind)

print("=" * 60)
print("VERITABANI YAPISI KONTROLÜ")
print("=" * 60)

print("\n=== STUDENT_SESSIONS TABLOSU ===")
cols = inspector.get_columns('student_sessions')
for col in cols:
    print(f"  • {col['name']:20s} -> {col['type']}")

print("\n=== CHAT_LOGS TABLOSU ===")
cols = inspector.get_columns('chat_logs')
for col in cols:
    print(f"  • {col['name']:20s} -> {col['type']}")

print("\n" + "=" * 60)
print("VERITABANI İÇERİĞİ KONTROLÜ")
print("=" * 60)

# Sessions
sessions = db.query(StudentSession).all()
print(f"\n=== TOPLAM SESSION: {len(sessions)} ===")
for s in sessions[:5]:
    print(f"  ID: {s.id}, Öğrenci: {s.student_id}, Vaka: {s.case_id}, Puan: {s.current_score}")

# Chat logs with metadata
chats_with_metadata = db.query(ChatLog).filter(
    ChatLog.metadata_json.isnot(None)
).all()

print(f"\n=== METADATA'LI CHAT LOG: {len(chats_with_metadata)} / {db.query(ChatLog).count()} ===")

# Sample metadata structure
if chats_with_metadata:
    sample = chats_with_metadata[0]
    print(f"\nÖRNEK METADATA YAPISI (Chat ID: {sample.id}):")
    if sample.metadata_json:
        metadata = sample.metadata_json if isinstance(sample.metadata_json, dict) else json.loads(sample.metadata_json)
        print(json.dumps(metadata, indent=2, ensure_ascii=False))

# Check for scoring data
print("\n=== PUANLAMA VERİSİ KONTROLÜ ===")
scored_actions = 0
total_score = 0

for chat in chats_with_metadata:
    if chat.metadata_json:
        try:
            metadata = chat.metadata_json if isinstance(chat.metadata_json, dict) else json.loads(chat.metadata_json)
            assessment = metadata.get("assessment", {})
            score = assessment.get("score", 0)
            if score > 0:
                scored_actions += 1
                total_score += score
                print(f"  • Chat ID {chat.id}: Action={metadata.get('interpreted_action', 'N/A')}, Score={score}")
        except Exception as e:
            print(f"  ✗ Metadata parse hatası (Chat ID {chat.id}): {e}")

print(f"\n📊 Toplam puanlanmış eylem: {scored_actions}")
print(f"💯 Toplam puan: {total_score}")

# Check foreign key relationships
print("\n=== İLİŞKİ KONTROLÜ ===")
orphan_chats = db.query(ChatLog).filter(
    ~ChatLog.session_id.in_(db.query(StudentSession.id))
).count()
print(f"  • Yetim chat log (session'ı olmayan): {orphan_chats}")

db.close()

print("\n" + "=" * 60)
print("✅ KONTROL TAMAMLANDI")
print("=" * 60)
