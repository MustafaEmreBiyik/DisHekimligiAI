# DENTAI ORCHESTRATOR LOG
> Bu dosya her Orchestrator oturumuna başlarken yapıştırılmalıdır.
> Her Completion Block sonrası güncel halini buraya kaydet.
> Son güncelleme: 2026-04-01

---

## DECISION LOG

```
[2026-04-01] [DECISION-001] RBAC: Three roles confirmed — student, instructor, admin. JWT payload standardized.
[2026-04-01] [DECISION-002] MedGemma: Validator-only role confirmed. Never used as patient persona.
[2026-04-01] [DECISION-003] Soft delete pattern mandatory for all entities.
[2026-04-01] [DECISION-004] JSON files = seed/import source only. DB is source of truth for live content.
[2026-04-01] [DECISION-005] Coach endpoint (/api/chat/coach) must not expose diagnosis in v1.
[2026-04-01] [DECISION-006] Sprint 1 execution order: Test infrastructure first, RBAC parallel,
              merge gated by stabilized pytest baseline.
[2026-04-01] [DECISION-007] Default pytest profile must be network-independent. External AI and
              live API tests run only as explicitly marked integration/e2e jobs.
[2026-04-01] [DECISION-008] E2E tests skip (not fail) when FastAPI server unreachable.
              Prevents false negatives in dev/CI environments.
[2026-04-01] [DECISION-009] test_auth.py 403 scenarios added by AGENT-2 and confirmed.
              AGENT-5 second pass not required — coverage already in place.
[2026-04-01] [DECISION-010] Old JWT tokens (sub-only payload) are invalidated by new auth layer.
              All active sessions must be cleared before Sprint 1 deployment.
[2026-04-01] [DECISION-011] SECRET_KEY must move to environment variable before any deployment.
              Currently hardcoded placeholder — CRITICAL finding by AGENT-7.
[2026-04-01] [DECISION-012] Alembic migration setup assigned to Sprint 2 start.
              Current create_all acceptable for Sprint 1 only.
[2026-04-01] [DECISION-013] JSON seed import runs once on empty DB.
              DB is sole live source of truth for users after first run.
[2026-04-01] [DECISION-014] Token response keeps legacy fields (student_id, name) for frontend
              compatibility alongside new (user_id, role, display_name).
[2026-04-01] [DECISION-015] Sprint 1 closure BLOCKED — 4 CRITICAL findings open.
              Deployment gated on AGENT-2 security fixes + AGENT-7 re-approval.
[2026-04-01] [DECISION-016] Token revocation (jti blacklist) HIGH severity.
              Sprint 1 içinde çözülmesi önerilir, deployment blocker sayılmaz.
[2026-04-01] [DECISION-017] /api/chat/coach audit Sprint 4 scope.
              Endpoint henüz implement edilmemiş. AGENT-7 Sprint 4'te tekrar devreye girecek.
[2026-04-01] [DECISION-018] MedGemma fail-open davranışı CRITICAL.
              Belirsizlikte fail-closed zorunlu. Deterministic fallback her durumda çalışmalı.
[2026-04-01] [DECISION-019] Deterministic safety katmanı eksik kapsam CRITICAL.
              Tüm kritik kurallar versioned JSON'a taşınmalı.
              Vaka bazında zorunlu kategori ve deterministic pre-check gerekli.
[2026-04-01] [DECISION-020] Chat response hidden evaluation verisi sızdırıyor HIGH.
              Student-safe response modeli zorunlu. Internal analytics ayrı role-guarded
              endpoint'e taşınmalı.
[2026-04-01] [DECISION-021] Quiz answer key öğrenciye dönüyor HIGH.
              Server-side validation zorunlu. correct_option ve explanation
              student response'tan çıkarılmalı.
[2026-04-01] [DECISION-022] Prompt injection riski tespit edildi HIGH.
              Öğrenci girdisi doğrudan LLM promptlarına ham enjekte ediliyor.
              Sprint 4'te AGENT-6 ele alacak. Prompt isolation ve sanitizasyon gerekli.
[2026-04-01] [DECISION-023] CORS wildcard + credentials kombinasyonu MEDIUM.
              allow_credentials=True ile wildcard origin riski. Kesin origin allowlist zorunlu.
```

---

## AGENT STATUS TABLE

```
═══════════════════════════════════════════
DENTAI AGENT STATUS — Sprint: 1
═══════════════════════════════════════════

| Agent   | Task ID           | Status   | Waiting On                         |
|---------|------------------|----------|------------------------------------|
| AGENT-1 | —                | IDLE     | —                                  |
| AGENT-2 | SPRINT-1-TASK-2  | DONE     | —                                  |
| AGENT-2 | SPRINT-1-TASK-5A | READY    | SECRET_KEY env var fix             |
| AGENT-2 | SPRINT-1-TASK-5B | READY    | BOLA fix (chat history endpoint)   |
| AGENT-2 | SPRINT-1-TASK-5C | READY    | Analytics export role guard        |
| AGENT-2 | SPRINT-1-TASK-5D | READY    | Chat response evaluation leak fix  |
| AGENT-3 | —                | IDLE     | —                                  |
| AGENT-4 | —                | IDLE     | Sprint 4 (MedGemma fallback)       |
| AGENT-5 | SPRINT-1-TASK-1  | DONE     | —                                  |
| AGENT-5 | SPRINT-1-TASK-3  | PENDING  | AGENT-2 fix'leri tamamlansın       |
| AGENT-6 | —                | IDLE     | Sprint 4 (Prompt injection)        |
| AGENT-7 | SPRINT-1-TASK-4A | DONE     | —                                  |
| AGENT-7 | SPRINT-1-TASK-4B | PENDING  | AGENT-2 fix'leri + re-approval     |
═══════════════════════════════════════════
```

---

## SPRINT 1 CLOSURE VERDICT

**Status: BLOCKED**

Deployment öncesi kapatılması zorunlu bulgular:

| Öncelik | Bulgu | Owner |
|---------|-------|-------|
| CRITICAL | SECRET_KEY hardcoded in deps.py | AGENT-2 |
| CRITICAL | BOLA: /api/chat/history/{student_id}/{case_id} unauthenticated | AGENT-2 |
| CRITICAL | MedGemma fail-open: safety_violation=False on error | AGENT-2 + AGENT-4 |
| CRITICAL | Deterministic safety katmanı eksik kapsam | AGENT-2 |
| HIGH | Analytics export role guard yok | AGENT-2 |
| HIGH | Chat response hidden evaluation sızıntısı | AGENT-2 |

---

## COMPLETION BLOCKS ARŞİVİ

### AGENT-5 — SPRINT-1-TASK-1 (DONE)

```
Status: DONE
Deliverable: Pytest baseline restore edildi. Script-style testler pytest
uyumlu hale getirildi. Default profil deterministik/offline.

FILES CHANGED:
- pytest.ini: marker stratejisi, default addopts, norecursedirs eklendi
- conftest.py: shared network/Gemini/MedGemma mock fixture'ları eklendi
- requirements.txt: pytest bağımlılığı eklendi
- test_agent_import.py: script akışı kaldırılıp smoke testlere dönüştürüldü
- test_auth.py: canlı localhost çağrıları kaldırılıp TestClient testlere çevrildi
- test_analytics_sprint3.py: demo script unit testlere dönüştürüldü
- test_pathergy.py: Gemini mock ile deterministik yorumlama testi eklendi
- test_e2e_flow.py: e2e marker'lı opt-in senaryoya dönüştürüldü, sys.exit kaldırıldı
- tests/test_rules_integration.py: integration marker'lı, mocklanmış MedGemma ile dönüştürüldü

TEST EXECUTION MATRIX:
- Default:      python -m pytest -q                          → 9 passed, 4 deselected
- Integration:  python -m pytest -q -o addopts='' -m integration → 3 passed
- E2E:          python -m pytest -q -o addopts='' -m e2e         → 1 skipped (server yok)

DECISIONS MADE:
- Varsayılan koşuda integration/e2e dışlandı
- Script-style testler tamamen test fonksiyonu yapısına taşındı
- E2E testinde sunucu yoksa fail yerine skip

DEPENDENCIES UNLOCKED:
- Sprint 1 pytest baseline açıldı
- Integration/e2e katmanları marker bazlı ayrıştı
```

### AGENT-2 — SPRINT-1-TASK-2 (DONE)

```
Status: DONE
Deliverable: DB-backed User model, RoleEnum, JWT standardizasyonu,
role guard altyapısı, soft archive, 8 auth testi geçiyor.

FILES CHANGED:
- db/database.py: UserRole enum, User SQLAlchemy modeli, soft archive alanları
- app/api/deps.py: TokenPayload, AuthenticatedUser, get_current_user_context,
                   require_roles dependency, legacy get_current_user korundu
- app/api/routers/auth.py: DB-backed auth, JSON seed import (one-time),
                            /me endpoint, user listing (instructor/admin),
                            archive/unarchive (admin)
- app/api/main.py: startup'ta tablo oluşturma eklendi
- scripts/init_db.py: users tablosu çıktıya eklendi
- test_auth.py: local SQLite fixture, JWT payload testi, 403 RBAC testleri

DECISIONS MADE:
- Auth tamamen SQLAlchemy ORM'e taşındı
- JSON files sadece empty DB için one-time seed
- Token response legacy fields korundu (student_id, name)
- Soft delete/archive pattern uygulandı

WARNINGS:
- [WARNING] Eski sub-only token'lar geçersiz — deploy öncesi session temizliği gerekli
- [WARNING] SECRET_KEY hardcoded — AGENT-7 CRITICAL olarak işaretledi

DEPENDENCIES UNLOCKED:
- AGENT-7 Sprint 1 security audit başlayabilir
```

### AGENT-7 — SPRINT-1-TASK-4A (DONE)

```
Status: DONE
Sprint 1 Closure Verdict: BLOCKED

DOMAIN A — APPLICATION SECURITY FINDINGS:

[CRITICAL] Hardcoded JWT signing secret
- Affected: app/api/deps.py
- Vector: Repo erişimi olan saldırgan geçerli token üretebilir
- Fix: SECRET_KEY env var'a taşı, key rotation ekle
- Owner: AGENT-2

[CRITICAL] BOLA: Chat history unauthenticated
- Affected: app/api/routers/chat.py
  GET /api/chat/history/{student_id}/{case_id}
- Vector: student_id tahmini ile başka öğrenci verisi okunabilir
- Fix: Route seviyesinde auth + owner kontrolü, 403
- Owner: AGENT-2

[HIGH] JWT rotation/revocation stratejisi yok
- Affected: app/api/deps.py, app/api/routers/auth.py
- Vector: Çalınan token TTL bitene kadar geçerli
- Fix: Kısa ömürlü token + refresh + jti blacklist
- Owner: AGENT-2

[HIGH] Route-level RBAC kapsamı eksik
- Affected: Tüm routers
- Vector: Fonksiyon seviyesi yetki kırıkları
- Fix: Tüm route'lara role policy matrisi uygula
- Owner: AGENT-2

[HIGH] Analytics export tüm authenticated user'a açık
- Affected: app/api/routers/analytics.py
- Vector: Öğrenci toplu veri indirebilir
- Fix: instructor/admin role guard
- Owner: AGENT-2

[HIGH] Chat response hidden evaluation sızdırıyor
- Affected: app/api/routers/chat.py
- Vector: Öğrenci scoring sinyallerini görüp sistemi oyunlaştırabilir
- Fix: Student-safe response modeli, internal data ayrı endpoint
- Owner: AGENT-2

[MEDIUM] Quiz answer key öğrenciye dönüyor
- Affected: app/api/routers/quiz.py
- Vector: Sınav bütünlüğü bozulur
- Fix: correct_option/explanation student response'tan çıkar
- Owner: AGENT-2

[MEDIUM] İç hata detayları istemciye yansıyor
- Affected: chat.py, analytics.py
- Vector: İç sistem topolojisi sızabilir
- Fix: Generic client error, detaylar sadece log'da
- Owner: AGENT-2

[MEDIUM] Audit log tamper-evident değil
- Affected: db/database.py
- Vector: DB düzeyinde kayıt değişikliği tespit edilemez
- Fix: Append-only audit tablo veya hash-chain log
- Owner: AGENT-2

[LOW] CORS wildcard + credentials
- Affected: app/api/main.py
- Vector: Cross-origin saldırı yüzeyi genişler
- Fix: Kesin origin allowlist
- Owner: AGENT-2

DOMAIN B — CLINICAL SAFETY FINDINGS:

[CRITICAL] MedGemma fail-open davranışı
- Affected: app/services/med_gemma_service.py, app/api/routers/chat.py
- Vector: Servis kesintisinde safety_violation=False dönüyor,
          kritik ihlaller kaçabiliyor
- Fix: Fail-closed zorunlu, belirsizlikte CRITICAL safety flag üret
- Owner: AGENT-2 (rule coverage), AGENT-4 (Sprint 4)

[CRITICAL] Deterministic safety katmanı eksik kapsam
- Affected: app/rules/clinical_rules.py, app/services/rule_service.py
- Vector: Kategori eksik vakalarda generic kurala düşülüyor,
          kritik hatalar yakalanmayabilir
- Fix: Tüm kritik kurallar versioned JSON'a, zorunlu kategori zorunluluğu
- Owner: AGENT-2

[HIGH] Allergy/contraindication hard-block yok
- Affected: app/assessment_engine.py, data/scoring_rules.json
- Vector: Penisilin alerjisinde yanlış antibiyotik her durumda bloklanmıyor
- Fix: Case-context aware deterministic hard-block kuralları
- Owner: AGENT-2

[HIGH] Prompt injection riski
- Affected: app/agent.py, app/services/med_gemma_service.py
- Vector: Öğrenci girdisi ham prompt'a enjekte ediliyor
- Fix: Prompt isolation, sanitizasyon, response validator
- Owner: AGENT-6 (Sprint 4)

[MISSING CONTEXT] /api/chat/coach — Sprint 4 scope, henüz implement edilmemiş.

DEPENDENCIES UNLOCKED:
- AGENT-2 security fix görevi başlayabilir (SPRINT-1-TASK-5A/B/C/D)
- AGENT-7 SPRINT-1-TASK-4B, AGENT-2 fix'leri sonrası re-approval için bekliyor
```

---

## KULLANIM TALİMATLARI

Her yeni Orchestrator oturumunda şu adımları izle:

1. Bu dosyanın içeriğini kopyala
2. Yeni Claude/Copilot oturumunu Orchestrator sistem promptuyla aç
3. İlk mesaj olarak yapıştır:

```
DENTAI ORCHESTRATOR LOG yapıştırılıyor — lütfen mevcut durumu yükle
ve ne üzerinde çalışacağımızı sor.

[DOSYA İÇERİĞİNİ BURAYA YAPISTIR]
```

4. Her Completion Block sonrası bu dosyayı güncelle:
   - AGENT STATUS TABLE'da ilgili satırı güncelle
   - Yeni kararları DECISION LOG'a ekle
   - Completion Block'u ARŞİV bölümüne ekle
