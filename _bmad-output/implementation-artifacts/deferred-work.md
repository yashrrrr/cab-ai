# Deferred Work

- source_spec: `spec-per-agent-recommendation-flags.md`
  summary: `rfc_number` collisions — `submit_rfc` derives `rfc_number` from the last 8 digits of `datetime.now().timestamp()`, so two RFCs submitted within the same second hit `UNIQUE constraint failed: change_requests.rfc_number` (HTTP 500).
  evidence: Pre-existing bug surfaced (not caused) while integration-testing the classify_rfc fix. `main.py` submit_rfc: `rfc_number = f"CHG{str(int(datetime.now().timestamp()))[-8:]}"`. Two rapid submissions collide. Fix idea: append a short uuid suffix or a per-second counter, or use a DB sequence. Out of scope for the flags feature.

## Resolved

- `classify_rfc` unpacking bug in `main.py` submit_rfc — FIXED 2026-07-26. `classify_rfc` returns a 4-tuple; submit_rfc now calls it once and unpacks `(classified_type, impact, priority, risk_level)`, converting the type to `ChangeTypeEnum` only when the requestor didn't supply one. Verified via FastAPI TestClient (auto-classify + explicit-type + GET round-trip).
