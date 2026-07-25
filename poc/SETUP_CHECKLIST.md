# PoC Setup Checklist — Fast Track to Demo

## ✅ Pre-Flight Checklist

### 1. Prerequisites
- [ ] Anthropic API key (from https://console.anthropic.com/)
- [ ] Docker & Docker Compose installed, OR
- [ ] Python 3.11 + Node.js 18 installed locally
- [ ] 15 GB disk space for Docker images (or ~2 GB for local)

### 2. Environment Setup

#### Option A: Docker (Recommended)
```bash
cd poc
cp .env.example .env
# Edit .env and set your ANTHROPIC_API_KEY
docker-compose up --build
```

**Expected output:**
```
backend_1   | INFO:     Started server process [1]
backend_1   | INFO:     Uvicorn running on http://0.0.0.0:8000
frontend_1  | Ready on http://localhost:3000
```

#### Option B: Local (Manual)
```bash
# Terminal 1: Backend
cd poc/backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install fastapi uvicorn anthropic pydantic
export ANTHROPIC_API_KEY="sk-ant-..."  # Windows: set ANTHROPIC_API_KEY=...
python db_init.py
python main.py

# Terminal 2: Frontend
cd poc/frontend
npm install
npm start
```

**Expected result:**
- Backend running at http://localhost:8000 ✅
- Frontend running at http://localhost:3000 ✅
- Database initialized with 5 sample RFCs ✅

### 3. Verify System is Running

**Test backend health:**
```bash
curl http://localhost:8000/health
# Expected: {"status":"ok"}
```

**Check frontend:**
- Open http://localhost:3000 in browser
- Should see polished UI with RFC List tab

**Verify sample RFCs loaded:**
- Go to RFC List tab
- Should see 5 RFCs: CHG20260724001–005

### 4. Pre-Demo Configuration

**Optional: Pre-test a CAB session**
1. Click RFC CHG20260724002 (Database Migration)
2. Click "🎯 Trigger AI CAB Review"
3. Watch deliberation (30–60 seconds)
4. Verify decision appears in green box

**Optional: Customize sample RFCs**
- Edit `backend/db_init.py` → `insert_sample_rfcs()` to change titles/descriptions
- Delete `backend/rfc_poc.db` and re-run `python db_init.py` to reload

---

## 🎯 Demo Day Checklist

### Morning Of
- [ ] Backend is running (check logs)
- [ ] Frontend is running (check browser)
- [ ] Database is initialized (5 RFCs visible)
- [ ] Anthropic API key is valid (test one CAB session)
- [ ] Browser zoom is 100% (or 110% for visibility)
- [ ] Clear any browser cache (Ctrl+Shift+Delete)

### During Demo
- [ ] Start with "RFC List" tab (overview)
- [ ] Demo CHG20260724001 first (quick win: Standard auto-approval)
- [ ] Demo CHG20260724003 second (No Impact escalation)
- [ ] Demo CHG20260724002 third (main event: CAB deliberation)
- [ ] Have CHG20260724004 (Emergency) and CHG20260724005 (Critical) ready as backups
- [ ] Be ready to submit a new RFC if asked ("Let me show you how that works...")

### Troubleshooting During Demo
- **Backend seems slow?** → CAB session may be running. Click "Show Logs" to see progress.
- **Submit button is disabled?** → Fill in all required fields (marked with *)
- **CAB decision took >2 minutes?** → Claude API may have rate limits. Try again in 30 seconds.
- **Page is blank?** → Check browser console (F12) for CORS errors. Ensure backend URL is correct.

---

## 📋 What to Prepare (Slides/Talking Points)

**If presenting to executives:**
1. **Context slide**: UST ITIL v6.1 process complexity
2. **Problem slide**: Current pain points (manual, slow, inconsistent)
3. **Solution overview**: Deterministic + AI-augmented approach
4. **Demo** (15 min): Walk through the PoC
5. **Results slide**: Speed gains, consistency, compliance
6. **Roadmap slide**: Next steps (full PIR, ServiceNow integration, KPI dashboard)

**Talking points (see DEMO_WALKTHROUGH.md for full script):**
- "Standard changes auto-approve in seconds, not days"
- "Ambiguous decisions escalate to humans (no AI overreach)"
- "5 AI agents collaborate like a real CAB meeting"
- "Every rule traces to the ITIL process doc (compliance)"
- "Full audit trail for accountability"

---

## 🚀 After Demo Success

### If Leadership Approves Next Phase:
1. **Schedule architecture review** with engineering team
2. **Plan PIR lifecycle buildout** (Doc brief.md outlines this)
3. **Scope ServiceNow integration** (ITSM client interface ready)
4. **Plan KPI dashboard** (design in brief.md Section 11)
5. **Set timeline for pilot** (recommend real change data in Q4)

### Code Artifacts for Handoff:
- **PoC code**: In `poc/` (backend, frontend, Docker setup)
- **Business brief**: In `docs/brief.md` (all requirements + open questions)
- **Architecture blueprint**: Will be in `docs/architecture.md` (next phase)
- **Story backlog**: Will be in `docs/stories/` (next phase)

---

## 📞 Quick Troubleshooting

| Issue | Solution |
|-------|----------|
| "Can't reach http://localhost:3000" | Frontend not running. Check `npm start` output. |
| "Can't reach http://localhost:8000" | Backend not running. Check `python main.py` output. |
| "CAB session fails" | Check API key is set and valid. See `export ANTHROPIC_API_KEY=...` |
| "No sample RFCs visible" | Database not initialized. Run `python db_init.py` |
| "API returns 500 error" | Check backend logs for Python exceptions. May be missing dependency. |
| "CORS error in browser" | Backend CORS middleware may not be configured. Check `main.py` startup. |
| "Button submissions fail" | Validate form fields are filled. Check browser console for errors. |

---

## ✨ Final Polish Touches

- [ ] Zoom browser to 110% (easier to see in large room)
- [ ] Close unnecessary browser tabs (reduce distraction)
- [ ] Test microphone/speaker if remote demo
- [ ] Have internet connection backup (LTE hotspot)
- [ ] Have a local backup demo video in case of tech issues
- [ ] Print QR code to this repo (optional: let people clone and test themselves)

---

## 🎉 You're Ready!

**Estimated time to first demo:** 10–15 minutes (Docker) or 20–30 minutes (local)

**Demo duration:** 12–15 minutes

**Expected outcomes:**
- ✅ Leadership understands the PoC concept
- ✅ Clear business value ("faster, more consistent")
- ✅ Clear guardrails ("AI doesn't override humans")
- ✅ Clear roadmap ("this is phase 1 of 4")
- ✅ Go/no-go decision for next phase

---

**Ready to demonstrate the future of Change Management? Let's go!** 🚀

RFC Lifecycle PoC v1.0 | Setup Checklist | July 2026
