# RFC Lifecycle PoC — End-to-End Demo

**AI-Powered Change Management with Virtual CAB Deliberation**

## 🎯 What This PoC Demonstrates

- ✅ **Deterministic RFC Classification**: Change type, impact, priority, and risk scoring (no LLM guessing)
- ✅ **Standard Change Catalogue Matching**: Auto-approval for pre-approved routine changes
- ✅ **No Impact Evaluation**: Two-tier approval process with ambiguity detection
- ✅ **AI CAB Deliberation**: Multi-agent collaborative review (5 virtual CAB members)
- ✅ **Polished UI**: React dashboard for RFC submission and CAB decision viewing
- ✅ **End-to-End Workflow**: From RFC intake → classification → CAB review → decision

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (React)                       │
│         RFC Submission + CAB Deliberation Viewer            │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP
┌──────────────────────▼──────────────────────────────────────┐
│                 Backend (FastAPI)                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Classification Engine (Deterministic)                   ││
│  │ - Change Type, Impact, Priority, Risk Assessment       ││
│  │ - SCC Matching, No Impact Evaluation                    ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ CAB Orchestrator (Multi-Agent)                          ││
│  │ - Chair (Change Manager)                                ││
│  │ - Infrastructure Specialist                             ││
│  │ - Application Specialist                                ││
│  │ - Business & Service Owner                              ││
│  │ - Security & Compliance Officer                         ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │ SQLite Database                                         ││
│  │ - RFCs, CAB Decisions, Audit Logs                       ││
│  └─────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
                       │ API
┌──────────────────────▼──────────────────────────────────────┐
│              Claude API (Anthropic)                         │
│        Runs Multi-Agent CAB Deliberation Sessions          │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose (recommended)
- OR Python 3.11 + Node.js 18
- Anthropic API Key (for CAB agent deliberation)

### Option A: Docker (Recommended)

```bash
cd poc

# Set your Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Launch backend + frontend
docker-compose up --build

# Open browser
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000
```

### Option B: Local Setup

#### Backend (Python FastAPI)

```bash
cd poc/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn anthropic pydantic

# Set API key
export ANTHROPIC_API_KEY="sk-ant-..."

# Initialize database & run
python db_init.py
python main.py

# API available at http://localhost:8000
```

#### Frontend (React)

```bash
cd poc/frontend

# Install dependencies
npm install

# Start dev server
npm start

# Opens http://localhost:3000 automatically
```

## 📊 How to Use the PoC

### 1. **View Pre-Loaded RFCs**

The database comes with **5 sample RFCs** that showcase different change types:

- **CHG20260724001**: User Account Creation (Standard Change → Auto-Approved)
- **CHG20260724002**: Database Schema Migration (Normal → CAB Review)
- **CHG20260724003**: Application Logging Update (No Impact → Two-Tier Review)
- **CHG20260724004**: Production Cache Failure (Emergency → ECAB Review)
- **CHG20260724005**: Payment Service v2 Deployment (Normal + Critical → CAB Review)

**Steps:**
1. Open http://localhost:3000
2. Go to **"📋 RFC List"** tab
3. Click any RFC card to view details

### 2. **Trigger AI CAB Deliberation**

For Normal/Expedited/Emergency RFCs without auto-approval:

1. Select an RFC (e.g., CHG20260724002)
2. Click **"🎯 Trigger AI CAB Review"**
3. Watch agents deliberate in real-time:
   - **Infrastructure Specialist** reviews downtime & back-out
   - **Application Specialist** reviews test coverage
   - **Business Owner** reviews justification & SLA impact
   - **Security Officer** flags security requirements
   - **Change Manager (Chair)** synthesizes and decides

### 3. **Submit a New RFC**

1. Go to **"➕ Submit RFC"** tab
2. Fill in form:
   - **Title**: What's changing
   - **Description**: Why + how
   - **Affected Systems**: Which systems (comma-separated)
   - **Downtime**: Hours required
   - **Test Cases**: Evidence of testing
   - **Back-out Plan**: Recovery strategy
3. Click **"✅ Submit RFC"**
4. System auto-classifies and routes:
   - Standard match? → Auto-approved
   - No Impact + unambiguous? → Coordinator/Manager approval
   - Other types? → Pending CAB review

## 🧠 AI CAB Agent Team

The PoC includes 5 virtual CAB members that deliberate collaboratively:

| Agent | Role | Persona |
|-------|------|---------|
| **Change Manager (Chair)** | Orchestrates, synthesizes, decides | Pragmatic, accountable |
| **Infrastructure Specialist** | Downtime, back-out, availability | Conservative, detail-focused |
| **Application Specialist** | Tests, deployment, code risk | Quality-focused, skeptical |
| **Business & Service Owner** | Justification, SLA, value | Business-first, customer-focused |
| **Security & Compliance** | Security risk, VAPT, compliance | Risk-averse, thorough |

**Each agent:**
- Reviews the full RFC context
- Considers prior agent opinions
- Raises concerns and questions
- Makes recommendations

**Chair then:**
- Synthesizes all perspectives
- Identifies consensus/conflicts
- Makes final decision: Approved / Rejected / Conditional Approval

## 📝 Classification Rules

### Change Type (Auto-Detected)

```
Emergency   → 24–48 hour outage fix (keywords: emergency, outage, production issue)
Expedited   → Urgent but not emergency (keywords: urgent, asap)
Normal      → Planned change, full review needed (default)
Standard    → Matches SCC entry (pre-approved catalogue)
No Impact   → No downtime, no user impact, config/metadata only
```

### Impact (1-High, 2-Medium, 3-Low)

- **High**: 3+ systems, 4+ hour downtime, enterprise-wide scope
- **Medium**: 2 systems, 1–4 hour downtime
- **Low**: Single system, minimal/no downtime

### Priority (Critical, High, Moderate, Low)

- **Critical**: Service down OR security violation
- **High**: Service degraded OR security safeguards insufficient
- **Moderate**: Medium impact, can wait
- **Low**: Low impact, can defer

### Risk Level (1-5 scale, Normal changes only)

```
Criteria scored:
- Users impacted (500+ → L5, 100–500 → L3, <100 → L1)
- Outage required (outside window → L5, during window → L3, none → L1)
- Business impact (enterprise → L5, multiple LOB → L4, site → L3, none → L1)
- Others' performance (significant → L4, minimal → L2, none → L1)
- Implementation history (first time → L5, <3 times → L2, 3+ → L1)

Risk = max(all scores), capped at 5.
```

### Standard Change Catalogue

RFCs matching SCC entries auto-approve:

- User Account Creation
- Password Reset
- Disk Space Extension
- Application Log Rotation
- Monitoring Threshold Update

### No Impact Evaluation

Must meet **ALL** criteria:
1. ✅ No end-user impact
2. ✅ No service outage
3. ✅ No interdependent systems
4. ✅ Rollback simple
5. ✅ Non-code or fully tested
6. ✅ Minimal scope (config/metadata)
7. ✅ No audit/compliance impact

If any criterion ambiguous → escalate to CAB (downgrade to Normal).

## 📡 API Endpoints

### Submit RFC
```bash
POST /rfc/submit
{
  "title": "...",
  "description": "...",
  "affected_systems": ["ServiceA", "ServiceB"],
  "business_justification": "...",
  "estimated_downtime_hours": 2,
  "requestor_name": "..."
}

Returns:
{
  "id": "rfc-uuid",
  "rfc_number": "CHG...",
  "change_type": "Normal",
  "impact": "1-High",
  "priority": "Critical",
  "risk_level": 4,
  "status": "Submitted",
  "auto_approved": false
}
```

### Get RFC
```bash
GET /rfc/{rfc_id}

Returns: Full RFC details
```

### Trigger CAB Review
```bash
POST /rfc/{rfc_id}/trigger-cab

Returns:
{
  "rfc_id": "...",
  "cab_decision": "Approved",
  "cab_reasoning": "...",
  "agent_logs": ["Chair: ...", "Infra: ...", "..."]
}
```

### List RFCs
```bash
GET /rfc-list

Returns:
{
  "rfcs": [
    { "id": "...", "rfc_number": "...", "title": "...", "status": "..." },
    ...
  ]
}
```

## 🎓 Demo Script for Leadership

**Timing**: ~15 minutes

1. **Intro (1 min)**
   - "This PoC demonstrates an AI-enhanced Change Management system."
   - Show the process doc section references.

2. **RFC Submission (2 min)**
   - Go to Submit RFC tab.
   - Fill in a new RFC (or use pre-loaded).
   - Show deterministic classification output.

3. **Standard Change Auto-Approval (2 min)**
   - Click CHG20260724001 (User Account Creation).
   - Explain: "Standard changes are auto-approved if they match the catalogue."
   - Show SCC list endpoint.

4. **No Impact Two-Tier Approval (2 min)**
   - Click CHG20260724003 (Logging Update).
   - Show "escalated to CAB (ambiguous)" status.
   - Explain: "If criteria are ambiguous, we escalate to human judgment."

5. **AI CAB Deliberation (7 min)**
   - Click CHG20260724002 (Database Migration).
   - Trigger CAB review.
   - Watch agents deliberate live (or show recording).
   - Show agent logs and final decision.
   - Explain: "5 specialists review in parallel, chair synthesizes."

6. **Key Takeaways (1 min)**
   - Deterministic classification removes guesswork.
   - Auto-approval only for unambiguous, low-risk changes.
   - AI augments human CAB (not replaces).
   - Full audit trail for accountability.
   - Compliance-first: every rule traces to source doc.

## 🔧 Customization

### Add Your Own Standard Change Catalogue Entry

Edit `backend/classification.py`, `SCC_ENTRIES`:

```python
{
    "name": "Your Change",
    "keywords": ["keyword1", "keyword2"],
    "services": ["ServiceA", "ServiceB"],
    "risk_level": 1,
    "requires_test": False,
}
```

### Customize Agent Personas

Edit `backend/cab_orchestrator.py`, `AGENT_PERSONAS`:

```python
"your_agent": {
    "name": "Your Agent Name",
    "role": "...",
    "style": "...",
    "system_prompt": "..."
}
```

### Adjust Classification Thresholds

Edit `backend/classification.py`:
- Change impact cutoffs in `assess_impact()`
- Adjust risk matrix in `assess_risk()`
- Update priority rules in `assess_priority()`

## 📚 Source Document Alignment

Every rule in the PoC traces back to the UST ITIL v6.1 Change Management process:

- **Section 7.0**: Change Classification (5 types)
- **Section 8.0**: Impact & Prioritization (deterministic tables)
- **Section 11.0**: CAB + ARB
- **Section 17.0**: Standard Change Catalogue
- **Section 18.0**: No Impact Criteria
- **Section 19.0**: PIR Lifecycle (not in PoC, in future)
- **Section 20.0**: Validity & Grace Period (not in PoC, in future)
- **Section 23.0**: Risk Assessment (5-level matrix)

## 🐛 Troubleshooting

**"Can't connect to backend"**
- Ensure backend is running: `python main.py`
- Check: http://localhost:8000/health
- Frontend default expects backend at `http://localhost:8000`

**"CAB session failed"**
- Check `ANTHROPIC_API_KEY` is set
- Verify API key is valid
- Check Claude API status

**"Database locked"**
- Close other connections to `rfc_poc.db`
- Or delete `rfc_poc.db` and restart (it will reinitialize)

## 📋 Future Enhancements

- [ ] Full PIR lifecycle with Day 7, 9, 12, 16, 22, 29, 30 reminder cascade
- [ ] Grace period approval tiers (Change Manager → Service Owner → Functional Head)
- [ ] Real ServiceNow integration (abstract ITSM client)
- [ ] Email notifications (abstract EmailClient)
- [ ] KPI dashboard (success rate, emergency change trends, non-compliance tracking)
- [ ] Multi-user sessions with role-based approval
- [ ] RFC dependency graphing and FSC conflict detection
- [ ] Detailed audit trail viewer
- [ ] Change calendar (FSC visualization)

## 📞 Support

For questions or issues with the PoC:
1. Check the README sections above
2. Review backend logs: `docker logs <container_id>`
3. Check browser console for frontend errors (F12)
4. Verify API health: `curl http://localhost:8000/health`

---

**Built with ❤️ for polished PoC presentations**

RFC Lifecycle PoC v1.0 | July 2026
