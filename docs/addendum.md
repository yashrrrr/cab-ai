---
title: Addendum — RFC Lifecycle Management System (RFC→CAB→PIR)
status: draft
created: 2026-07-29
updated: 2026-07-29
---

# Addendum

Supplementary context for `brief.md` — options considered and rejected during discovery, kept here because they matter for downstream PRD/architecture work but don't belong in the brief itself.

## Environment-Staged Predecessor Gate (Section 3.4) — Rejected Alternative Models

Two other models were considered and explicitly rejected while shaping Section 3.4:

**Rejected: sequential single-RFC gate chain.** Initial framing treated environment-staging as one RFC passing through three sequential CAB approval gates (Dev CAB → QA CAB → Production CAB) as it progressed, i.e., a single `ChangeRequest` row with three approval checkpoints. Rejected because the actual requirement is that an RFC has a fixed `environment` value for its lifetime — separate RFCs exist per environment, linked by predecessor, not one RFC advancing through gates.

**Rejected: implicit multi-RFC spawn per business change.** A second framing considered a "business change" super-entity that would automatically spawn three linked RFCs (Dev/QA/Prod) per change. Explicitly rejected by the user: there is no business-change entity to model — each RFC is independently created by a user, and the environment field plus the predecessor-linkage requirement (Section 3.4, 5.4) is the only mechanism enforcing the phased relationship. This keeps the object model simpler (one entity, `ChangeRequest`, with an `environment` field) rather than introducing a new parent entity.

**Adopted model**: `ChangeRequest.environment` (Dev/QA/Production) + `ChangeRequest.environment_predecessor_rfc_id`, gated by a cross-row trigger requiring the predecessor to be the same `type`, one environment stage lower, and at status **Completed**. See `brief.md` Sections 3.4, 5.4, 13.12, 15.6, 17.1, 17.2, and Open Question 7 for the adopted rule and its open sign-off items.
