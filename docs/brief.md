# Business Brief: RFC Lifecycle Management System (RFC→CAB→PIR)

**Document Version**: 1.0  
**Date**: 2026-07-24  
**Project**: ITG Change Management Process Automation (v6.1 Implementation)  
**Source of Truth**: UST Change Management Process Document v6.1 (07-08-2026)  
**Status**: Ready for PM review before PRD creation

---

## 1. Executive Summary

Build a backend + dashboard system that automates the UST ITIL-aligned Change Management lifecycle from RFC (Request for Change) intake through CAB (Change Advisory Board) decision-making and PIR (Post Implementation Review) compliance tracking. The system must deterministically classify, score, and route changes while enforcing strict guardrails: only Standard and No Impact changes with unambiguous criteria may auto-approve; Normal, Expedited, and Emergency changes always require human decision-maker accountability.

**Non-Negotiable Principle**: The agent is responsible for *intake, validation, classification, scoring, briefing, and routing*. The **human** is responsible for *approval and risk accountability*. No bypass of this boundary.

---

## 2. Business Context & Drivers

### Why This System?
- **Current State**: Manual RFC triage, CAB scheduling, and PIR follow-up creates delays, inconsistent classification, and compliance gaps (especially PIR overdue non-conformances).
- **Target State**: Deterministic classification → automated routing → LLM-assisted briefing for CAB → full PIR cascade enforcement → compliance dashboard.
- **Key Constraint**: UST operates under ITIL governance; every rule, table, and threshold traces to the source document (Section reference provided below).

### Stakeholders & Roles
- **Change Requestor**: Initiates RFC via ITSM tool (iSolve ServiceNow).
- **Change Coordinator**: First-level reviewer (assess feasibility, filter unfeasible RFCs). *(Section 7.0, 15.0)*
- **Change Manager**: Reviewer, approver, CAB chair, final authority on change status transitions.
- **CAB (Change Advisory Board)**: Cross-functional reviewers (Infrastructure, Application, Business, Enterprise Architect). Formal weekly meetings; ad-hoc for urgent changes.
- **ECAB (Emergency CAB)**: Subset of CAB for Emergency changes; can approve out-of-hours via email.
- **Service Owner / Technical Lead**: Subject-matter approval tier for grace period extensions and PIR sign-off.
- **Functional Head / Account Manager**: Top-tier approval for grace period extensions (60+ days).
- **Architecture Review Board (ARB)**: Formal panel within CAB for design/architectural vetting. *(Section 11.0 note)*

---

## 3. Change Classification & Deterministic Routing

### 3.1 Five Change Types *(Section 7.0, Section 17.0, Section 18.0)*

| **Type** | **Definition** | **Auto-Approve?** | **Approver Path** | **PIR Required?** | **Validity Period** |
|----------|---------------|-------------------|-------------------|-------------------|-------------------|
| **Standard** | Pre-approved routine low-risk changes in the Standard Change Catalogue (SCC) | **YES** — if matched to active SCC entry | None (auto-approved in ITSM) | **NO** | 20 calendar days *(Section 20.0)* |
| **No Impact** | Low-risk, no user/system/service impact; metadata/config/monitoring updates | **ONLY if both Coordinator AND Manager unambiguously approve** | Coordinator → Manager (2-tier) | **NO** | 30 calendar days *(Section 20.0)* |
| **Normal** | Major planned changes; full assessment needed | **NO** | Coordinator → Manager → CAB → Implementation → PIR | **YES** | 45 calendar days *(Section 20.0)* |
| **Expedited** | Urgent changes (not emergencies); fast-tracked Normal path | **NO** | Coordinator → Manager → CAB (ad-hoc) → Implementation → PIR | **YES** | 45 calendar days *(Section 20.0)* |
| **Emergency** | 24–48 hour repairs for service outage; minimal upfront approvals | **NO** | Coordinator → Manager → ECAB/CIO email → Implementation → PIR | **YES** | 10 calendar days *(Section 20.0)* |

**Key Guardrail** *(Section 15.0, Section 18.0)*:
- Standard and No Impact may auto-approve **only** when every qualifying criterion is unambiguously met.
- If ambiguous (e.g., "is this really no impact?"), escalate to human, never guess.
- Normal, Expedited, Emergency: **must always be routed to a human**; no auto-approval ever.

### 3.2 Impact & Priority Scoring *(Section 8.0)*

All RFCs assigned **Impact** and **Priority** (deterministic lookup tables, never LLM).

#### Impact (Section 8.0):
- **1-High**: Extensive business impact, multiple services affected.
- **2-Medium**: Moderate business impact, single service or limited scope.
- **3-Low**: Minimal business impact, isolated, non-critical area.

#### Priority (Section 8.0 table):
Determined by **highest** of: service availability, security, business reaction urgency.

| **Criteria** | **Critical** | **High** | **Moderate** | **Low** |
|---|---|---|---|---|
| **Service Availability** | Service down, business affected | Service degraded, not usable | Service degraded but usable | Available, can wait |
| **Security** | Violation in progress | Safeguards insufficient | Safeguards need strengthening | Strong safeguards in place |
| **Business Reaction** | Immediate action needed | Very small window | Augment capabilities | No effect on capabilities |

### 3.3 Risk Scoring *(Section 23.0)* — Normal Changes Only

Risk assessed via deterministic lookup matrix (not LLM):

| **Criteria** | **Level 5** | **Level 3** | **Level 1** |
|---|---|---|---|
| **Users Impacted** | ≥500 | 100–500 | ≤100 |
| **Service Outage** | Outside maintenance window | During maintenance window | None required |
| **Business Impact** | Enterprise-wide, mission-critical | Entire/multiple lines of business | Site/office or no impact |
| **Performance Impact on Others** | Significant/unknown | Minimal | None |
| **Implementation History** | First time | <3 times | ≥3 times |

**System assigns**: highest level from any criterion.

---

## 4. Standard Change Catalogue *(Section 17.0)* — New Epic

A **Standard Change** is only valid if it matches an entry in the SCC with **Active** status. The SCC itself requires governance:

### SCC Lifecycle *(Section 17.0)*:
1. **Propose New / Modify / Retire**: Requestor submits proposal in ITSM (Template Management).
2. **CAB Review**: Change Manager assesses frequency, success rate, risk, and compliance.
3. **Status Transition**:
   - **New → In Progress → Closed**: Proposal approved → SCC entry goes **Active**.
   - **Retire Proposal**: SCC entry goes **Inactive** (existing RFCs can finish, no new RFCs use it).
4. **Periodic Review**: CAB reviews SCC every year; all Active entries valid for 12 months *(Section 17.0)*.

**System Responsibility**:
- Persist the SCC (template, parameters, validity dates).
- Check incoming RFC against Active SCC entries; match → auto-approve if all criteria met.
- Track SCC change proposals (New/Modify/Retire) as a separate workflow.

---

## 5. Auto-Approval Engine Constraints *(Section 17.0, Section 18.0, Section 14.0)*

### 5.1 Standard Change Auto-Approval

**Condition**: RFC type = Standard AND matched to Active SCC entry.

**Action**: ITSM auto-moves to "In Progress" state; no human approval required.

**Data Requirements**:
- `standard_change_catalogue_entry_id` (FK to SCC).
- `auto_approved_timestamp` (audit).
- `auto_approved_reason` (e.g., "Matched SCC entry XXX, all criteria met").

### 5.2 No Impact Auto-Approval

**Condition**: RFC type = No Impact AND all criteria met (Section 18.0):
1. No end-user/customer impact.
2. No service outage (even momentary).
3. No interdependent systems affected.
4. Rollback simple/unnecessary.
5. Non-code or fully tested in lower env.
6. Minimal scope (config/metadata/monitoring only).
7. No audit/compliance/security posture change.

**Action**: System routes to Coordinator → Manager for 2-level approval.

**Decision Logic**:
- If **all** criteria unambiguous → recommend auto-approval to Coordinator/Manager.
- If **any** criterion ambiguous → escalate to CAB or Change Manager for manual judgment.

**Data Model** (Two-Tier Approval):
- `no_impact_coordinator_approval` (timestamp, actor_id).
- `no_impact_coordinator_approval_comment` (justification).
- `no_impact_manager_approval` (timestamp, actor_id).
- `no_impact_manager_approval_comment` (justification).
- Both fields non-null before state moves to "In Progress."

### 5.3 Enforcement Guardrail *(Non-Negotiable)*

**Architectural Constraint**: At the data-access layer (not just API), no code path may set state to `in_progress` for Standard/No Impact changes without:
1. For Standard: `standard_change_catalogue_entry_id` is non-null and the SCC entry status is "Active."
2. For No Impact: Both `no_impact_coordinator_approval` and `no_impact_manager_approval` are non-null, and `actor_id` in both audit log entries are **not** "agent" (i.e., a human signed off).
3. Every approval decision logged in AuditLogEntry with actor, timestamp, decision, reason.

**Regression Test Suite** (`test_guardrails.py`):
- Fuzz 100+ RFC shapes across all 5 types.
- Assert: Normal/Expedited/Emergency never reach `in_progress` without human_approver_id non-null.
- Assert: Standard never reached `in_progress` without active SCC entry.
- Assert: No Impact never reached `in_progress` without both coord + manager approval non-null and human actors.
- Run on every commit; block deployment if any fail.

---

## 6. RFC Intake & Document Validation *(Section 14.0 & Section 15.0 – Initiate Stage)*

### 6.1 Required Documents by Type

**Normal/Expedited** *(Section 15.0 – Initiate Stage)*:
- Implementation plan.
- Test cases (Application) or use cases/requirement success criteria (Infrastructure/PoC).
- Test results (for Application).
- Email approvals: AUP, Budget/Cost (Account Mgr), Service/Env Owner, Enterprise Architect.
- Expedited only: Expedited questionnaire + account manager approval of business justification.

**Emergency** *(Section 16.0 – Initiate Stage)*:
- Back-out plan.
- Incident ticket (tagged to RFC).
- Test cases (if time permits).
- Service Owner impact email approval.
- If out-of-hours: email approval from ECAB or CIO office (attached retroactively).

**No Impact** *(Section 18.0 – Initiate Stage)*:
- No implementation plan/test cases **if** a procedure document is provided.
- Service Owner approval email.

**Standard** *(Section 17.0 – Initiate Stage)*:
- Matched SCC entry ID.
- Any additional artefacts noted in SCC template.

### 6.2 Validation Rules (System Enforces)

- RFC cannot move past Initiate state until all required documents attached.
- Change Coordinator filters unfeasible RFCs at Review stage *(Section 15.0)*.
- No auto-approval without all artifacts present.

---

## 7. CAB Process & Briefing *(Section 11.0, Section 12.0, Section 14.0 – Plan & Schedule Stage)*

### 7.1 CAB Meetings & Agenda

**Formal Meetings** *(Section 11.0)*:
- Weekly scheduled CAB for routine changes.
- Ad-hoc CAB or ECAB for expedited/emergency.
- Pre-CAB (Section 12.0) for complex, high-risk, or contentious changes.

**CAB Agenda Items**:
- Failed/backed-out/unauthorized changes (review).
- RFCs for assessment and approval.
- No Impact changes (pre-approved by CAB, then per Section 18.0 logic).
- Post-Implementation Review (PIR) results.
- Process improvements.
- Wins/accomplishments.

### 7.2 LLM-Assisted CAB Briefing *(Not in Source Doc; Inferred)*

**Open Question 1**: *Source doc does not specify how CAB briefings are generated (summary, risk narrative, impact assessment). System will use Claude API to generate:*
- RFC summary (what, why, when, who).
- Risk narrative (combining deterministic risk level + contextual nuance).
- Impact on Forward Schedule of Changes (FSC).
- ARB applicability (yes/no + reason).
- Dependencies and conflicts with other RFCs.

**Implementation Constraint**: LLM output is advisory only; Change Manager reviews and approves before presenting to CAB.

### 7.3 Forward Schedule of Changes (FSC) *(Section 10.0)*

**Data Entity Required**: Track each approved change's:
- Affected Configuration Items (CIs).
- Implementation time window (start, end).
- Planned downtime (if any).
- Related changes (conflicts, dependencies).

**System Responsibility**:
- Build FSC view (approved changes by date).
- Query FSC to detect conflicts when new RFCs arrive.
- Include conflict analysis in CAB briefing.

### 7.4 Architecture Review Board (ARB) *(Section 11.0 note)*

**ARB Required If**:
- New solution.
- Architectural change involved.
- Interfaces/interconnects with other UST IT systems.

**Process**:
- Change requestor reviews with concerned architect.
- Architect decides: ARB discussion in CAB forum vs. separate meeting.
- System tracks: `arb_required` (boolean), `arb_reviewed_by` (name), `arb_review_date`.

---

## 8. Post Implementation Review (PIR) Lifecycle *(Section 19.0)* — Two-Stage Approval

### 8.1 PIR Trigger & Timeline

**Trigger**: Automatic on Day 7 after RFC moves to "Completed" state. *(Section 19.0)*

**Assessment Instance ID**: System auto-generates and notifies requestor.

### 8.2 Notification & Escalation Cascade *(Section 19.0 – PIR Timeline)*

| **Day** | **Actor** | **Action** | **Recipients** |
|---|---|---|---|
| **7** | System | Initial PIR notification | Requestor, Change Management DL |
| **9** | System | 1st Reminder | Requestor, Manager, CM DL |
| **12** | System | 2nd Reminder | Requestor, Manager, CM DL |
| **16** | System | 3rd Reminder | Requestor, Manager, CM DL |
| **22** | System | 1st Escalation | Manager (to), Requestor (cc), CM DL (cc) |
| **29** | System | Final Escalation | Manager (to), Requestor (cc), CM DL (cc) |
| **30+** | System | Auto-cancel survey, initiate non-conformance | Requestor, Manager, CM DL |

### 8.3 Two-Stage PIR Approval *(Section 19.0)*

**Stage 1: Requestor Submits PIR**
- Requestor completes PIR questionnaire (change status: Successful/Unsuccessful/Rolled Back).
- Questionnaire routed to Change Manager for review.

**Data Fields**:
- `pir_submitted_date` (timestamp).
- `pir_submitted_by` (requestor).
- `change_status` (Successful/Unsuccessful/Rolled Back).
- `pir_questionnaire_id` (FK to survey response).

**Stage 2: Manager Reviews + Ad-Hoc Approver Signs Off**
- Change Manager reviews PIR; can approve or reject.
- If approved, Change Manager nominates an **Ad-Hoc Approver** (senior team lead from concerned team).
- Ad-Hoc Approver receives email, reviews, approves or rejects.
- **Only after Ad-Hoc Approver approval** can Change Manager close the RFC.

**Data Fields**:
- `pir_manager_review_date` (timestamp).
- `pir_manager_approval` (boolean).
- `pir_manager_comments` (text).
- `pir_adhoc_approver_id` (FK to User).
- `pir_adhoc_approver_review_date` (timestamp).
- `pir_adhoc_approver_approval` (boolean).
- `pir_adhoc_approver_comments` (text).

**Close Condition**: Both Manager AND Ad-Hoc Approver must approve before RFC moves to Closed.

### 8.4 PIR Non-Conformance *(Section 19.0 – Auto-cancel Logic)*

**Trigger**: PIR survey not completed by Day 30.

**Process**:
1. System auto-cancels PIR survey link.
2. Change Manager creates incident ticket (non-conformance).
3. Notification sent to requestor's manager + CM DL with non-conformance template.
4. Manager analyzes reason for delay and documents remediation plan.
5. Manager submits template + analysis to ITG Head for review/approval.
6. Once approved, Change Manager attaches approval email to incident.
7. Change Manager reactivates new PIR survey link.
8. Requestor completes new PIR.
9. Change Manager closes incident.
10. **Future RFCs from this requestor held until non-conformance is resolved.**

**System Responsibility**:
- Persist non-conformance incident record.
- Track requestor blocks (no new RFCs until cleared).
- Link incident to original RFC.

---

## 9. Change Request Validity & Grace Period *(Section 20.0)*

### 9.1 Validity Periods

| **Type** | **Validity (Calendar Days)** | **Grace Period Available?** |
|---|---|---|
| Normal | 45 | Yes |
| Expedited | 45 | Yes |
| No Impact | 30 | Yes |
| Standard | 20 | **No** |
| Emergency | 10 | **No** |

### 9.2 Grace Period Approval Tiers *(Section 20.0)*

Once validity expires, requestor must get approval to extend:

| **Type** | **< 10 Days** | **< 30 Days** | **< 60 Days** |
|---|---|---|---|
| Normal | Change Manager | Service Owner/PM | Functional Head/Account Mgr |
| Expedited | Change Manager | Service Owner/PM | Functional Head/Account Mgr |
| No Impact | Service Owner/PM | Functional Head/Account Mgr | — |

**Process**:
- Requestor submits grace period request in ITSM before/at validity expiry.
- System routes to appropriate approver tier.
- Approver approves/rejects.
- If approved: `validity_extension_date` updated; change can continue.
- If rejected or expired without approval: change marked Non-Compliant (Section 25.0).

### 9.3 Enforcement

- Standard and Emergency **no grace period allowed**.
- At validity expiry + 10 days: if grace not obtained, system initiates non-conformance.
- System prevents new tasks from being created on expired RFCs.

---

## 10. Generic Non-Compliance *(Section 25.0)* — Separate from PIR Non-Conformance

**Trigger**: Change implemented in violation of process (e.g., no approval obtained, no Change Manager sign-off, proceeded without proper documentation).

**Process** *(Section 25.0)*:
1. RFC tagged "Non-Compliance" and marked "Cancelled."
2. Change Manager sends email to CIO office + respective manager, cc CAB.
3. CIO office must provide email override to avoid/remediate.
4. **No PIR conducted** on non-compliant change.
5. Tracked for 90 days post-implementation; impact assessment report shared with CIO.

**System Responsibility**:
- Detect violations: missing approvals, unauthorized state transitions, unlinked PIR.
- Create non-compliance record with audit trail.
- Flag in compliance dashboard (Section 11.0 – KPIs).
- Route notification to CIO office.

**Distinction from PIR Non-Conformance**:
- **PIR Non-Conformance** (Section 19.0): Requestor failed to complete PIR within 30 days of completion.
- **Generic Non-Compliance** (Section 25.0): Change was implemented without following process steps at all (no approval chain, no CAB, etc.).

---

## 11. KPI Dashboard & Compliance Tracking *(Section 24.0)*

### 11.1 Tracked KPIs *(Section 24.0)*

| **KPI** | **Objective** | **Tracking** | **Notes** |
|---|---|---|---|
| Reduction in unauthorized changes | Effectiveness | Monthly (CSI Call) | — |
| Reduction in unplanned/emergency changes | Effectiveness | Monthly (CSI Call) | — |
| Change success rate | Effectiveness | Monthly (CSI Call) | % successful RFCs / total approved |
| Reduction in failed changes | Efficiency | Monthly (CSI Call) | — |
| Average time to implement (by type/priority) | Efficiency | When CMDB ready | — |
| Incidents attributable to changes | Efficiency | When CMDB ready | — |
| Restrict changes with exceptional approvals | Effectiveness | Monthly (CSI Call) | Minimize grace period approvals |

### 11.2 Non-Goals (Explicit Out-of-Scope) *(Section 24.0 footnote)*

**Backlog Trend Tracking**: Intentionally not tracked due to change validity policy (RFCs not allowed to stay open >30 days without valid extension). Dashboard will NOT include RFC backlog trends; this is a documented non-goal to prevent agent "helpful" additions.

### 11.3 Exceptional Approvals *(Section 24.0)*

Track (and minimize) changes approved via grace period extensions at the highest tier (Functional Head/Account Manager). These are legitimate but resource-intensive; the KPI flags when they spike (possible process friction).

### 11.4 Dashboard Views

**For Change Managers**:
- RFC queue (by status, type, priority).
- Overdue RFCs (past validity without extension).
- Non-compliant changes (awaiting CIO remediation).
- PIR overdue (past Day 30).
- KPI summary (monthly).

**For CAB**:
- CAB agenda (weekly RFC list + FSC conflicts).
- ARB flagged changes (awaiting architect review).
- Failed/backed-out changes (post-review).

**For Requestors**:
- My RFCs (status, next approver, PIR status).
- PIR reminders (countdown to Day 30).

---

## 12. Tech Stack & Integration Points

### 12.1 Backend
- **Language**: Python (FastAPI) or Node.js (NestJS/Express).
  - *Recommendation*: Python + FastAPI for deterministic rule engines (decision tables, state machines).
- **Database**: PostgreSQL (production); SQLite (local dev).
- **Scheduler**: APScheduler (Python) or node-cron (Node) for PIR cascade (Day 7, 9, 12, 16, 22, 29, 30).

### 12.2 ITSM Integration
- **Abstraction Layer**: `ITSMClient` interface.
  - Methods: `create_rfc()`, `update_rfc_state()`, `attach_document()`, `query_rfc()`, etc.
- **First Implementation**: In-memory mock (no external ServiceNow calls).
- **Future**: Swap mock for real ServiceNow/iSolve client.

### 12.3 Notifications
- **Abstraction Layer**: `EmailClient` interface.
  - Methods: `send_email()`, `send_bulk()`, etc.
- **First Implementation**: Log to console/DB (mocked).
- **Future**: Real SMTP or SendGrid.

### 12.4 LLM Integration
- **Claude API**: For CAB briefings, ambiguous No-Impact classification review, non-compliance summaries.
- **Never for Scoring**: Risk levels, priority, impact classification are **deterministic lookup tables**, never LLM.

### 12.5 Frontend
- **Simple React Dashboard** or plain HTML/JS (minimum viable).
- **Views**: RFC queue, CAB agenda, PIR status, KPI charts.

---

## 13. Scope Inclusions (Traced to Source Doc)

### 13.1 Standard Change Catalogue Lifecycle *(Section 17.0)*
- Propose New / Modify / Retire workflow.
- CAB review and approval.
- Active/Inactive status tracking.
- Annual validity review.

### 13.2 No Impact Change Management *(Section 18.0)*
- Deterministic criteria validation.
- Two-tier approval (Coordinator + Manager).
- Parent/child CR linking (for phased releases).
- Automated routing based on criteria match.

### 13.3 PIR Two-Stage Approval *(Section 19.0)*
- Requestor submission → Manager review → Ad-Hoc Approver sign-off.
- Both decisions logged with actor + timestamp.
- Only after both approvals can CR close.

### 13.4 PIR Reminder & Escalation Cascade *(Section 19.0 – Days 7, 9, 12, 16, 22, 29, 30)*
- 6 notifications to requestor/manager.
- Auto-cancel survey on Day 30; trigger non-conformance process.

### 13.5 Generic Non-Compliance *(Section 25.0)*
- Separate trigger from PIR non-conformance.
- CIO office override required.
- 90-day post-implementation tracking.
- Distinct from process-violation non-compliance.

### 13.6 Grace Period Enforcement *(Section 20.0)*
- Tier-based approvers (Change Manager → Service Owner → Functional Head).
- Standard/Emergency: no grace period.
- System blocks new tasks after validity expiry.

### 13.7 Forward Schedule of Changes (FSC) *(Section 10.0)*
- Persist affected CI + time window per change.
- Query for conflicts in CAB briefing.
- Enable "Projected Service Availability (PSA)" conflict detection.

### 13.8 Architecture Review Board (ARB) Applicability *(Section 11.0 note)*
- Track `arb_required` (boolean) + `arb_reviewed_by` + `arb_review_date`.
- Criteria: new solution, architectural change, interfaces with other UST systems.

### 13.9 Parent/Related CR Linking *(Section 7.0 – No Impact narrative)*
- `parent_change_request_id` (FK).
- `related_change_request_id` (FK array for dependencies).
- Link unsuccessful → backed-out changes to correction CR.
- Link No Impact child CRs to parent Normal CR (phased releases).

### 13.10 KPI Dashboard *(Section 24.0)*
- Track 7 core KPIs (listed in Section 11.1).
- Minimize exceptional approvals (grace period escalations).
- **Explicitly NOT track backlog trends** (non-goal per Section 24.0 footnote).

### 13.11 Client Requirements & PoC Approval *(Section 26.0)*
- **Scope Decision**: Build minimal `client_managed` flag + placeholder for client PoC window approval, OR explicitly mark out-of-scope for v1.
- *(See Open Question 2 below.)*

---

## 14. Scope Exclusions (Explicit Out-of-Scope)

- **Change Advisory Board (CAB) voting/consensus mechanics**: Assumed Change Manager chairs and makes final call post-CAB deliberation.
- **Configuration Management Database (CMDB)** integration: Time-to-implement and incident trends tied to CMDB. System will track changes but not build CMDB; CMDB assumed to exist independently.
- **Backlog Trend Tracking** *(Section 24.0 footnote)*: Intentionally omitted due to validity policy.
- **Business CAB** (legacy): Removed per Section 14.0 amendment history.

---

## 15. Guardrails (Architectural Constraints, Non-Negotiable)

### 15.1 Approval Accountability
- Normal, Expedited, Emergency: **never auto-approved**. Change Manager or CAB retains decision accountability.
- Standard: auto-approved only if SCC entry matched.
- No Impact: auto-approved only if all criteria unambiguous AND both Coordinator + Manager sign off.

### 15.2 Audit Trail (Insert-Only)
- AuditLogEntry: immutable record of every decision (who, when, decision, inputs).
- Substitutes for human sign-off on auto-decisions (e.g., Standard auto-approval → logged as "matched SCC XXX").

### 15.3 Idempotency
- All scheduled jobs (PIR cascade, grace period check, non-conformance initiation) must be idempotent.
- Safe to re-run without double-sending, double-deciding, or orphaning records.

### 15.4 Separation of Read/Simulate from Irreversible Actions
- Code path for "preview CAB briefing" isolated from "submit RFC to CAB."
- Code path for "evaluate No Impact" isolated from "approve No Impact."
- Enables safe testing in sandbox before touching real ITSM.

### 15.5 RBAC Enforcement (Data-Access Layer)
- Role-gated approval: only user with "Change Manager" role can approve at Change Manager tier.
- Only user with "Service Owner" role can approve grace periods < 30 days.
- Enforced at DB constraint and API handler.

---

## 16. Open Questions & Ambiguities

### **Open Question 1**: CAB Briefing Generation
**Source Gap**: Section 14.0 (Plan & Schedule stage) states CAB reviews RFCs and impact/risk, but does not specify how briefing documents are generated (summary, AI-assisted, manual).

**System Assumption**: Claude API generates briefing (RFC summary, risk narrative, FSC conflicts, ARB flag) as **advisory**. Change Manager reviews and approves before presentation.

**Confirmation Needed**: Is LLM-assisted briefing acceptable? Should we template briefing format? Any security/compliance constraints on LLM processing of change details?

### **Open Question 2**: Client Requirements & PoC Approval *(Section 26.0)*
**Source Doc**: Section 26.0 mandates client-managed infrastructure approval (change window + emergency approval). No detail on **how** PoC approval is obtained or tracked.

**Options**:
1. **Minimal v1**: Add `client_managed` (boolean), `client_poc_id` (FK), `client_approval_date` (timestamp). Requests with `client_managed=true` route to Change Manager, who obtains PoC email approval and attaches it.
2. **Explicit out-of-scope for v1**: Note that client PoC integration is not covered; system assumes internal-only RFCs.

**Confirmation Needed**: Which option fits the project scope? If out-of-scope, can we note it explicitly in brief so no agent "helpfully" builds it later?

### **Open Question 3**: Unsuccessful / Backed-Out Change Linkage
**Source Gap**: Section 15.0 states "new CR shall be related to the parent change request" for unsuccessful/backed-out changes. Does not specify whether this is parent_id (1:1) or a "related" array (M:M).

**System Assumption**: `parent_change_request_id` (FK, nullable) for unsuccessful/backed-out CRs pointing to the failed change. Separate `related_change_request_ids` (array) for general dependencies.

**Confirmation Needed**: Is this model correct? Should we enforce that unsuccessful CRs have non-null parent_id?

### **Open Question 4**: Emergency Change Retrospective Logging
**Source Doc**: Section 16.0 states "Logging of the change can occur prior to implementation, but **restoring of service takes precedence**" and "change is fully processed and documented **after already implemented**."

**System Implication**: RFC can be created post-implementation (state = "Retrospective Initiated"). Do we allow API to accept RFCs with `change_type=Emergency` and `logged_date` in the past, or does the ITSM tool (ServiceNow) handle retroactive logging?

**Confirmation Needed**: Should the system accept retrospectively-logged Emergency RFCs, or route all RFC creation through ITSM only?

### **Open Question 5**: CAB Pre-Approval of No Impact Changes
**Source Doc**: Section 11.0 states "List of No Impact changes shall be reviewed and **pre-approved by CAB**." Unclear: does every No Impact change get pre-approved, or only a batch at regular CAB meetings?

**System Assumption**: No Impact changes reviewed/approved by Coordinator + Manager (Section 18.0 formal process). CAB pre-approves a list of **no-impact change categories** at annual review, not individual RFCs.

**Confirmation Needed**: Is this reading correct, or should every No Impact RFC go to CAB before auto-approval?

### **Open Question 6**: Exceptional Approvals KPI
**Source Doc**: Section 24.0 KPI "Restrict the changes with the exceptional approvals" is tracked but not defined. What threshold is "restricted"? >5% of RFCs? >2 per month?

**System Assumption**: Dashboard will show count + % of RFCs approved via grace period (exceptional). No hard threshold; flagged for Change Manager review if spike occurs.

**Confirmation Needed**: Should the system auto-flag or alert if exceptional approvals exceed a threshold, or is dashboard visibility sufficient?

---

## 17. Data Model Skeleton (High-Level)

### 17.1 Core Entities

```
ChangeRequest
  - id (UUID, PK)
  - rfc_number (string, unique)
  - title, description
  - type (enum: Normal, Expedited, Emergency, Standard, No Impact)
  - status (enum: Draft, Review, Schedule For Approval, In Progress, Completed, Closed, Cancelled, Non-Compliant)
  - created_date, submitted_date, completed_date
  - impact (enum: 1-High, 2-Medium, 3-Low)
  - priority (enum: Critical, High, Moderate, Low)
  - risk_level (int 1-5, Normal changes only)
  - requestor_id (FK User)
  - change_manager_id (FK User)
  - change_coordinator_id (FK User)
  - human_approver_id (FK User, NOT NULL for Normal/Expedited/Emergency in In Progress)
  - parent_change_request_id (FK ChangeRequest, nullable)
  - validity_date (calendar days per type)
  - validity_extension_date (nullable)
  - grace_period_approver_id (FK User, nullable)
  - grace_period_extended_until (date, nullable)
  
  -- Standard Change fields
  - standard_change_catalogue_entry_id (FK StandardChangeCatalogueEntry, nullable)
  - auto_approved_timestamp (datetime, nullable)
  - auto_approved_reason (string, nullable)
  
  -- No Impact fields
  - no_impact_coordinator_approval (datetime, nullable)
  - no_impact_coordinator_comment (text, nullable)
  - no_impact_manager_approval (datetime, nullable)
  - no_impact_manager_comment (text, nullable)
  
  -- PIR fields
  - pir_assessment_instance_id (FK PIRAssessment)
  - pir_submitted_date (datetime, nullable)
  - pir_submitted_by_id (FK User, nullable)
  - pir_change_status (enum: Successful, Unsuccessful, Rolled Back, nullable)
  - pir_manager_review_date (datetime, nullable)
  - pir_manager_approval (boolean, nullable)
  - pir_manager_comments (text, nullable)
  - pir_adhoc_approver_id (FK User, nullable)
  - pir_adhoc_approver_review_date (datetime, nullable)
  - pir_adhoc_approver_approval (boolean, nullable)
  - pir_adhoc_approver_comments (text, nullable)
  
  -- ARB fields
  - arb_required (boolean)
  - arb_reviewed_by_id (FK User, nullable)
  - arb_review_date (datetime, nullable)
  
  -- FSC/Conflict fields
  - planned_start_date, planned_end_date
  - affected_cis (JSON array of CI identifiers)
  - fsc_conflicts (JSON array of conflicting CR ids)
  
  -- Client management
  - client_managed (boolean, default false)
  - client_poc_id (nullable, placeholder)
  - client_approval_date (datetime, nullable)

StandardChangeCatalogueEntry
  - id (UUID, PK)
  - name (string, unique)
  - description
  - status (enum: Active, Inactive)
  - validity_start_date, validity_end_date
  - proposed_by_id (FK User)
  - approved_by_id (FK User)
  - proposal_type (enum: New, Modify, Retire)
  - frequency_estimate (string: "frequently", "occasionally", etc.)
  - success_rate_pct (int)
  - risk_level (int 1-5)
  - template_details (JSON: parameters, checklists)
  - created_date, last_modified_date

AuditLogEntry
  - id (UUID, PK)
  - rfc_id (FK ChangeRequest)
  - action (string: "auto_approved", "approved", "rejected", "submitted", etc.)
  - actor_id (FK User, nullable; "agent" if system action)
  - timestamp (datetime)
  - inputs (JSON: decision parameters, rules applied)
  - decision (string: approval outcome)
  - reason (text: explanation)
  - [immutable, insert-only]

PIRAssessment
  - id (UUID, PK)
  - rfc_id (FK ChangeRequest)
  - assessment_instance_id (string, unique)
  - created_date (datetime)
  - survey_link (string, unique)
  - survey_status (enum: Open, Submitted, Approved, Rejected, Cancelled)
  - cancelled_date (datetime, nullable)
  - submitted_date (datetime, nullable)
  - reminder_sent_dates (datetime array)
  - escalation_sent_dates (datetime array)

NonComplianceRecord
  - id (UUID, PK)
  - rfc_id (FK ChangeRequest)
  - incident_ticket_id (string, FK external ITSM)
  - violation_type (enum: "PIR_Overdue", "Process_Violation", "Grace_Period_Expired")
  - created_date (datetime)
  - cio_override_email_date (datetime, nullable)
  - cio_override_approved (boolean, nullable)
  - remediation_plan (text, nullable)
  - resolved_date (datetime, nullable)
  - impact_assessment (text, nullable)
  - [tracked for 90 days post-implementation]

RelatedChangeRequest
  - id (UUID, PK)
  - rfc_id (FK ChangeRequest)
  - related_rfc_id (FK ChangeRequest)
  - relationship_type (enum: "parent", "child", "dependency", "conflict")
```

### 17.2 Validation Constraints (Data Layer)

```
-- Standard auto-approval enforcement
ALTER TABLE ChangeRequest
  ADD CONSTRAINT chk_standard_auto_approved
  CHECK (
    (type != 'Standard') OR 
    (type = 'Standard' AND standard_change_catalogue_entry_id IS NOT NULL)
  );

-- No Impact two-tier approval
ALTER TABLE ChangeRequest
  ADD CONSTRAINT chk_no_impact_approval
  CHECK (
    (type != 'No Impact') OR 
    (type = 'No Impact' AND (
      (status != 'In Progress') OR
      (no_impact_coordinator_approval IS NOT NULL AND no_impact_manager_approval IS NOT NULL)
    ))
  );

-- Human approver for Normal/Expedited/Emergency
ALTER TABLE ChangeRequest
  ADD CONSTRAINT chk_human_approver
  CHECK (
    (type NOT IN ('Normal', 'Expedited', 'Emergency')) OR
    (type IN ('Normal', 'Expedited', 'Emergency') AND (
      (status != 'In Progress') OR
      (human_approver_id IS NOT NULL)
    ))
  );

-- Audit log is immutable
ALTER TABLE AuditLogEntry
  ADD CONSTRAINT no_update_audit
  GENERATED ALWAYS AS ROW START hidden,
  ADD CONSTRAINT no_delete_audit
  WITH (IOCTL = 0);  -- or equivalent immutability per DB
```

---

## 18. Testing & Regression Strategy

### 18.1 Guardrail Test Suite (`test_guardrails.py`)

Run continuously; blocks deployment on failure.

**Test Cases**:
1. Fuzz 100+ RFC shapes (all 5 types, all combinations of impact/priority/risk).
2. Assert: No RFC of type Normal/Expedited/Emergency ever reaches `in_progress` without `human_approver_id` non-null.
3. Assert: No Standard RFC reaches `in_progress` without active SCC entry matched.
4. Assert: No No Impact RFC reaches `in_progress` without both Coordinator + Manager approval non-null and actors are human (not "agent").
5. Assert: Every auto-approval logged to AuditLogEntry with inputs and decision.
6. Assert: Validity enforcement (no tasks created after expiry unless grace granted).
7. Assert: PIR cascade (Day 7, 9, 12, 16, 22, 29, 30 notifications and auto-cancel).
8. Assert: Non-compliance initiation on validity expiry + 10 days.

### 18.2 Integration Tests

- Standard Change Catalogue lifecycle (Propose/Modify/Retire → approval → Active/Inactive).
- No Impact auto-approval when all criteria met.
- No Impact escalation to CAB when ambiguous.
- PIR two-stage approval (Requestor → Manager → Ad-Hoc).
- Grace period routing (Manager < 10 → Service Owner < 30 → Functional Head < 60).
- Non-compliance email to CIO + CAB.

### 18.3 E2E User Stories

- Requestor submits Standard CR → auto-approved → in_progress.
- Requestor submits Normal CR → Coordinator reviews → Manager reviews → CAB briefs (LLM-generated) → CAB approves → in_progress → completed → PIR → Manager approves → Ad-Hoc approves → closed.
- Requestor submits No Impact CR with ambiguous impact → escalated to CAB manually.

---

## 19. Handoff Sequence

1. **PM**: Review this brief, confirm scope/open questions → green-light for PRD.
2. **PM** (docs/prd.md): Write epics + stories with acceptance criteria.
3. **Architect** (docs/architecture.md): Design data model, RBAC, interfaces (ITSMClient, EmailClient, LLMClient), deployment model.
4. **Dev Team** (docs/stories/*.md): Shard epics into dev-ready stories per architecture.

---

## 20. Appendix: Source Document Index

| **Section** | **Topic** | **Key Constraint** |
|---|---|---|
| 7.0 | Change Classification | 5 types (Normal, Expedited, Emergency, Standard, No Impact) |
| 8.0 | Impact & Prioritization | Deterministic lookup tables (Impact 1-3, Priority C/H/M/L) |
| 9.0 | Approval SLA | Response times by type (5d / 4h / 2d / 6.75h / N/A) |
| 11.0 | Change Advisory Board | CAB + ECAB + ARB (new solution / arch change / interfaces) |
| 14.0 | Change Lifecycle Stages | Initiate → Review & Authorize → Plan & Schedule → Implement → Closed |
| 15.0 | Normal Change | Full lifecycle, PIR required, 45-day validity |
| 16.0 | Emergency Change | 24–48 hr, email approval, PIR required, 10-day validity |
| 17.0 | Standard Change | SCC lifecycle (Propose/Modify/Retire), auto-approve if matched, 20-day validity |
| 18.0 | No Impact Change | 2-tier approval (Coordinator + Manager), 30-day validity |
| 19.0 | PIR Lifecycle | 2-stage approval (Manager + Ad-Hoc), Day 7–30 cascade, auto-cancel + non-conformance |
| 20.0 | Validity & Grace Period | Validity by type; grace period tiers (CM < 10d, SO < 30d, FH < 60d) |
| 23.0 | Risk Assessment | 5-level matrix (users, outage, impact, others' performance, history) |
| 24.0 | KPIs | 7 tracked metrics; backlog trend explicitly NOT tracked |
| 25.0 | Non-Compliance | Process violation → CIO email override → 90-day tracking (distinct from PIR NC) |
| 26.0 | Client Requirements | Client PoC approval for client-managed infrastructure changes |

---

**Brief Status**: ✅ Ready for PM review.  
**Next Step**: Confirm all open questions; PM proceeds to PRD (docs/prd.md).