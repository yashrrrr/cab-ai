# PoC Demo Walkthrough — For Leadership Presentation

**Duration**: ~12-15 minutes  
**Audience**: Executive/Leadership team  
**Goal**: Demonstrate AI-enhanced Change Management with human-in-the-loop guardrails

---

## 📊 Pre-Demo Checklist

- [ ] Backend running: `python main.py` (or Docker)
- [ ] Frontend running: `npm start` or Docker
- [ ] Firefox/Chrome developer tools ready (optional)
- [ ] Anthropic API key set and valid
- [ ] Sample RFCs pre-loaded in database
- [ ] Test CAB session pre-run (optional, to show recorded result)
- [ ] Slides ready (optional business context)

---

## Demo Flow

### 1. **Opening Statement** (1 min)

**Say:**
> "We're going to walk through a proof-of-concept that reimagines how UST manages IT changes. Today, change management is manual, slow, and prone to errors. This PoC shows three things:
>
> 1. **Deterministic classification** — No AI guessing; rules from the ITIL process doc
> 2. **Intelligent routing** — Auto-approve low-risk changes, escalate the uncertain ones
> 3. **Virtual CAB** — Five AI agents that think like your actual CAB team does
>
> Most importantly: **The human stays in charge**. AI speeds things up, humans make the calls."

---

### 2. **Show the System** (1 min)

**Navigate to**: http://localhost:3000

**Point out:**
- Header: "RFC Lifecycle PoC"
- Three main sections: "📋 RFC List", "➕ Submit RFC", (and detailed view once selected)
- Clean, polished UI suitable for executive demos

---

### 3. **Standard Change Auto-Approval** (2 min)

**Click**: RFC List → Select **CHG20260724001** (User Account Creation)

**What you're showing:**
```
RFC NUMBER: CHG20260724001
TITLE: User Account Creation Batch
TYPE: Standard ← This is key
STATUS: Auto-Approved (Standard Change Catalogue)
```

**Say:**
> "This change was **automatically approved** because:
>
> 1. Type is 'Standard' — routine, pre-approved change
> 2. It matched the Standard Change Catalogue (user account creation is common)
> 3. Risk is minimal (only IT operations affected)
> 4. No CAB meeting needed
>
> **Key guardrail**: Auto-approval only happens when EVERY criterion is unambiguous. If anything is fuzzy, it escalates to a human."

**Show**:
- Click on the card
- Show the "Auto-Approved" badge
- Explain: "This took 30 seconds from submission to decision. Human CAB? 2–3 days."

---

### 4. **No Impact Evaluation (Two-Tier Approval)** (2 min)

**Click**: RFC List → Select **CHG20260724003** (Logging Update)

**What you're showing:**
```
RFC NUMBER: CHG20260724003
TITLE: Update Application Logging Level
TYPE: No Impact
STATUS: Escalated to CAB (Ambiguous No Impact)
```

**Say:**
> "This is a 'No Impact' change — just updating internal logging config, no users affected. But the system flagged it as **ambiguous**:
>
> ✅ No downtime
> ✅ No user impact
> ⚠️ Uncertain: Is this really low-risk?
>
> **Our guardrail**: When ambiguous, escalate to human. Here, it goes to the Change Coordinator and Manager for two-person review. No guessing."

**Show**:
- Impact: 3-Low ✅
- Priority: Low ✅
- Status shows escalation reason

---

### 5. **AI CAB Deliberation — THE STAR OF THE SHOW** (7–8 min)

**Click**: RFC List → Select **CHG20260724002** (Database Schema Migration)

**What you're showing:**
```
RFC NUMBER: CHG20260724002
TITLE: Production Database Schema Migration
TYPE: Normal
IMPACT: 1-High
PRIORITY: High
RISK LEVEL: 3/5
STATUS: Submitted
```

**Say:**
> "This is a **Normal change** — not emergency, but significant. It affects the production database and requires CAB review.
>
> Here's where the AI comes in. Instead of waiting for the human CAB to meet, we'll simulate what they'd discuss."

**Click**: **"🎯 Trigger AI CAB Review"**

**Watch the agents deliberate** (usually takes 30–60 seconds):

**Agent 1: Infrastructure Specialist**
> "The 2-hour downtime is during the maintenance window ✅. Back-out plan is solid ✅. Infrastructure impact is moderate — we can handle it. **Concern:** Database rollback under load could be risky if something breaks."

**Agent 2: Application Specialist**
> "Test cases are comprehensive ✅. But I see regression testing coverage is 85%, not 100%. **Concern:** Could miss edge cases. Recommend expanding test suite before proceeding."

**Agent 3: Business Owner**
> "Business justification is strong ✅ — marketing team needs the new fields. SLA impact is documented ✅. Downtime window is pre-communicated ✅. **Condition:** Ensure release notes are finalized."

**Agent 4: Security Officer**
> "No new privilege escalation ✅. No data exposure ✅. Recommend VAPT? No, this is schema-only, low risk. ✅"

**Agent 5: Change Manager (Chair)**
> "Synthesizing... Infrastructure flagged rollback risk. Application flagged test coverage gap. Both are addressable. **Decision: CONDITIONAL APPROVAL**
>
> - Condition 1: Expand regression test suite to 100%
> - Condition 2: Prepare detailed rollback runbook
> - Once conditions met, proceed with implementation.
>
> This is a sound change with manageable risk."

**Final Result (in green box)**:
```
🎯 Final Decision: Conditional Approval

Key concerns: Test coverage, rollback complexity
Conditions: Complete test suite, finalize runbook
Recommendation: Proceed once conditions cleared
```

**Say (after CAB session completes):**
> "That entire CAB deliberation happened in under a minute. Each agent:
> - Reviewed the full RFC context
> - Considered what others said
> - Raised specific concerns
> - Made recommendations
>
> The Chair synthesized everything and issued a **conditional approval**. A human Change Manager would now validate those conditions. That human stays in control of the decision."

---

### 6. **Show Classification Rules** (1 min)

**Navigate to**: RFC List

**Point out the diversity:**

| RFC | Type | Auto-Approved? | Why? |
|-----|------|---|---|
| CHG20260724001 | Standard | ✅ Yes | Matches SCC, low-risk |
| CHG20260724002 | Normal | ❌ No | Needs CAB review |
| CHG20260724003 | No Impact | ❌ No | Ambiguous → escalate |
| CHG20260724004 | Emergency | ❌ No | Always human-approved |
| CHG20260724005 | Normal | ❌ No | Critical + complex |

**Say:**
> "The system uses deterministic rules — no LLM judgment — to classify each change:
>
> - **Change Type**: Emergency / Expedited / Normal / Standard / No Impact
> - **Impact**: High / Medium / Low (based on systems affected, downtime, scope)
> - **Priority**: Critical / High / Moderate / Low (based on service impact, security, urgency)
> - **Risk**: 1–5 scale (based on users impacted, outage, implementation history)
>
> Every rule comes from Section 8 and Section 23 of the UST ITIL process doc. **No guessing, no hallucinations.**"

---

### 7. **Show the Process Flow** (1 min)

**Open** (optional): README.md → Architecture section

**Say:**
> "Here's the full flow:
>
> 1. **RFC Submitted** → Deterministic classification
> 2. **Standard/No-Impact logic** → Auto-approve or escalate
> 3. **For Normal/Expedited/Emergency** → Trigger AI CAB
> 4. **5 agents review** → Chair synthesizes → Decision
> 5. **Human validates** → Proceed or address conditions
>
> The AI is the **intake, briefing, and routing layer**. Humans make the **approval decisions**."

---

### 8. **Key Guardrails** (1 min)

**Say:**
> "Three non-negotiable guardrails:
>
> 1. **Normal/Expedited/Emergency changes NEVER auto-approve.** These carry risk. A human must sign off.
> 2. **Audit trail is insert-only.** Every decision is logged: who, when, why. No erasures. This is accountability.
> 3. **Ambiguous classifications escalate.** We never guess. If the system can't decide with certainty, a human makes the call."

---

### 9. **Submit a New RFC** (Optional; if time allows — 2 min)

**Navigate to**: Submit RFC tab

**Fill in a sample:**
```
Title: New Report Service Deployment
Description: Deploy new analytics microservice to production
Affected Systems: Analytics, Database, API Gateway
Estimated Downtime: 0.5 hours
Requestor: Your Name
```

**Click**: Submit RFC

**System output:**
```
✅ RFC submitted: CHG20260724006
Change Type: Normal
Impact: 2-Medium
Priority: Moderate
Risk Level: 2/5
Status: Submitted
```

**Say:**
> "The system instantly classified this as Normal, Medium impact, Moderate priority, Risk 2. It would route to CAB for review. In the full system, we'd trigger a CAB session next."

---

### 10. **Closing Statement** (1–2 min)

**Say:**
> "Let's recap what we just saw:
>
> ✅ **Speed**: Standard changes approved in seconds, not days  
> ✅ **Consistency**: Rules-based, not people-based; every RFC classified the same way  
> ✅ **Intelligence**: AI briefings let CAB members make informed decisions faster  
> ✅ **Safety**: Humans stay in control; auto-approval only for genuinely low-risk changes  
> ✅ **Traceability**: Every decision logged, every rule documented, source-aligned with ITIL  
>
> **Next steps:**
> - Build out the full PIR lifecycle (Post-Implementation Review)
> - Add grace period approval tiers
> - Integrate with real ServiceNow
> - Deploy KPI dashboard
> - Production hardening & load testing
>
> This PoC proves the concept works. Questions?"

---

## 🎯 Talking Points for Q&A

**Q: "Will this replace our CAB team?"**  
A: "No. This augments them. Humans make all risky decisions. AI handles intake, classification, and briefing. CAB moves from 'read 50 RFCs in a meeting' to 'decide on 5 briefed changes.' Speed without loss of control."

**Q: "How does it handle edge cases?"**  
A: "If uncertain, it escalates. For No Impact changes, ambiguous rules go to human coordinators. For normal changes, fuzzy criteria trigger human CAB review. We never guess."

**Q: "What about compliance?"**  
A: "Every rule traces to the UST ITIL process doc (Section references in code). Audit trail is immutable. Decisions are logged with actors. Full non-repudiation."

**Q: "How long does a CAB session take?"**  
A: "For the AI to run, ~30–60 seconds. For a human CAB, a full deliberation might take 1–2 hours. The AI accelerates the information phase; humans focus on judgment."

**Q: "What if the AI makes a bad recommendation?"**  
A: "It's just a recommendation. The human Change Manager reads it, questions it if needed, and approves or rejects. The human is accountable."

**Q: "Can we test this with our actual RFCs?"**  
A: "Yes. Bring any sample RFCs; we can feed them through the system. The classifier will work on real data. The CAB simulator is a PoC; integrating real ServiceNow comes next."

---

## 📸 Screenshot Ideas (Optional for Slides)

1. **RFC List** — Grid of colorful RFC cards
2. **Submit Form** — Clean form with all fields
3. **CAB Session** — Agent logs scrolling, decision at bottom
4. **Architecture Diagram** — Frontend → Backend → Claude API

---

## ⏱️ Timing Reference

- **Opening**: 1 min
- **System overview**: 1 min
- **Standard Change demo**: 2 min
- **No Impact demo**: 2 min
- **CAB Deliberation (MAIN DEMO)**: 7–8 min
- **Classification rules**: 1 min
- **Process flow**: 1 min
- **Guardrails**: 1 min
- **New RFC (optional)**: 2 min
- **Closing + Q&A**: 2–3 min

**Total: 12–15 minutes** (flexible)

---

**Ready to present!** 🚀

RFC Lifecycle PoC v1.0 | Demo Script | July 2026
