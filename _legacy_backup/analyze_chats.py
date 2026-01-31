"""Chat logları detaylı incele"""
import sys
sys.path.insert(0, '.')
from db.database import SessionLocal, ChatLog, StudentSession

db = SessionLocal()

print("=== CHAT LOG ANALİZİ ===\n")
chats = db.query(ChatLog).all()
print(f"Toplam chat mesajı: {len(chats)}\n")

user_msgs = 0
assistant_msgs = 0
with_metadata = 0
without_metadata = 0

for c in chats:
    if c.role == "user":
        user_msgs += 1
    elif c.role == "assistant":
        assistant_msgs += 1
    
    if c.metadata_json is not None:
        with_metadata += 1
    else:
        without_metadata += 1
    
    print(f"Chat ID {c.id}:")
    print(f"  Role: {c.role}")
    print(f"  Session ID: {c.session_id}")
    print(f"  Has metadata: {c.metadata_json is not None}")
    print(f"  Content preview: {c.content[:100]}...")
    print()

print("\n=== ÖZET ===")
print(f"Kullanıcı mesajları: {user_msgs}")
print(f"Asistan mesajları: {assistant_msgs}")
print(f"Metadata'lı mesajlar: {with_metadata}")
print(f"Metadata'sız mesajlar: {without_metadata}")

# Session bilgisi
session = db.query(StudentSession).first()
if session:
    print(f"\n=== SESSION BİLGİSİ ===")
    print(f"ID: {session.id}")
    print(f"Öğrenci: {session.student_id}")
    print(f"Vaka: {session.case_id}")
    print(f"Mevcut Puan: {session.current_score}")
    print(f"Başlangıç: {session.start_time}")

db.close()
