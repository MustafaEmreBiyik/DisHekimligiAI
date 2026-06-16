import json, re, sys
sys.stdout.reconfigure(encoding="utf-8")

with open("finetuning/finetune_dataset.jsonl", encoding="utf-8") as f:
    lines = [l for l in f if l.strip()]

print(f"{len(lines)} total examples\n")

for i, l in enumerate(lines, 1):
    obj = json.loads(l)
    user_content = obj["conversations"][0]["content"]
    asst_raw = obj["conversations"][1]["content"]
    try:
        asst = json.loads(asst_raw)
    except Exception:
        asst = {}

    m = re.search(r'"case_context":\s*"([^"]{0,80})', user_content)
    ctx = m.group(1) if m else user_content[:60]

    acc = asst.get("clinical_accuracy", "?")
    flags = ", ".join(asst.get("safety_flags", []) or []) or "none"
    missing = ", ".join(asst.get("missing_critical_steps", []) or []) or "none"

    print(f"{i:>2}. [{acc}] flags=[{flags}]")
    print(f"    ctx: {ctx[:75]}")
    print()
