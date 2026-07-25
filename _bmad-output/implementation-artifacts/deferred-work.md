# Deferred Work

- source_spec: `spec-per-agent-recommendation-flags.md`
  summary: `classify_rfc` is misused in `main.py` submit_rfc — it returns a 4-tuple but is assigned to `change_type` and separately unpacked into 3 vars, raising ValueError on any RFC submitted without an explicit change_type.
  evidence: Pre-existing bug surfaced (not caused) during flags work. `classification.py:classify_rfc` returns `(change_type, impact, priority, risk_level)`; `main.py` `submit_rfc` does `req.change_type = classify_rfc(...)` then `impact, priority, risk_level = classify_rfc(...)`. The second line unpacks 4 values into 3 → `ValueError: too many values to unpack`. Pre-loaded/seeded RFCs work (inserted directly), masking it. Explicitly out of scope for the flags feature.
