"""Metadata içeriğini incele"""
import sys
sys.path.insert(0, '.')
from db.database import SessionLocal, ChatLog
import json

db = SessionLocal()

print("=== METADATA İÇERİK ANALİZİ ===\n")

chats_with_meta = db.query(ChatLog).filter(
    ChatLog.metadata_json.isnot(None)
).all()

print(f"Metadata'lı chat sayısı: {len(chats_with_meta)}\n")

for c in chats_with_meta:
    print(f"\n{'='*60}")
    print(f"CHAT ID: {c.id} (Role: {c.role})")
    print(f"{'='*60}")
    
    metadata = c.metadata_json
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    
    if not metadata:
        print("❌ Metadata boş!")
        continue
    
    print(f"Metadata tipi: {type(metadata)}")
    print(f"Metadata anahtarları: {list(metadata.keys())}")
    print(f"\nİçerik:")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))

db.close()
