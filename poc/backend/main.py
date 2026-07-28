"""
RFC Lifecycle PoC Backend — FastAPI + AI CAB Orchestration
Demonstrates deterministic classification + multi-agent CAB deliberation
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum
import json
import uuid
import sqlite3
import os
import shutil
import glob

from cab_orchestrator import run_ai_cab_session
from classification import classify_rfc, evaluate_no_impact, match_scc
from db_init import init_db, migrate_db, get_db_connection
from document_extraction import extract_document_text, extract_rfc_fields

# Supporting-document uploads: files land in uploads/tmp/{token}{ext} until
# the RFC they're paired with is created, then move to uploads/{rfc_id}/.
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
UPLOAD_TMP_DIR = os.path.join(UPLOAD_DIR, "tmp")
os.makedirs(UPLOAD_TMP_DIR, exist_ok=True)

# PDF, Word, PowerPoint, Excel — the modern Office Open XML formats. Legacy
# binary formats (.doc, .ppt, .xls) aren't supported; see document_extraction.py.
ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}

# ─────────────────────────────────────────────────────────────
# FastAPI App Setup
# ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="RFC Lifecycle PoC",
    description="AI-powered Change Management with Virtual CAB",
    version="1.0.0"
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# Data Models
# ─────────────────────────────────────────────────────────────

class ChangeTypeEnum(str, Enum):
    NORMAL = "Normal"
    EXPEDITED = "Expedited"
    EMERGENCY = "Emergency"
    STANDARD = "Standard"
    NO_IMPACT = "No Impact"

class ImpactEnum(str, Enum):
    HIGH = "1-High"
    MEDIUM = "2-Medium"
    LOW = "3-Low"

class PriorityEnum(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MODERATE = "Moderate"
    LOW = "Low"

class RFCSubmissionRequest(BaseModel):
    title: str
    description: str
    change_type: Optional[ChangeTypeEnum] = None  # Auto-classified if None
    business_justification: str
    implementation_plan: Optional[str] = None
    test_cases: Optional[str] = None
    back_out_plan: Optional[str] = None
    affected_systems: List[str]  # ["ServiceA", "ServiceB"]
    estimated_downtime_hours: Optional[float] = 0
    requestor_name: str
    document_token: Optional[str] = None  # from POST /rfc/upload-document, pairs the uploaded PDF with this RFC
    document_filename: Optional[str] = None  # original filename, echoed back from the upload response

class RFCResponse(BaseModel):
    id: str
    rfc_number: str
    title: str
    description: str
    change_type: ChangeTypeEnum
    impact: ImpactEnum
    priority: PriorityEnum
    risk_level: Optional[int]
    status: str
    created_at: str
    cab_decision: Optional[str] = None
    cab_reasoning: Optional[str] = None
    auto_approved: bool = False
    requestor_name: Optional[str] = None
    affected_systems: Optional[List[str]] = None
    estimated_downtime_hours: Optional[float] = 0
    business_justification: Optional[str] = None
    implementation_plan: Optional[str] = None
    test_cases: Optional[str] = None
    back_out_plan: Optional[str] = None
    cab_flags: Optional[List[dict]] = None
    document_filename: Optional[str] = None

class CABSessionRequest(BaseModel):
    rfc_id: str

# ─────────────────────────────────────────────────────────────
# Database Setup
# ─────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    """Initialize database on startup"""
    db_path = os.path.join(os.path.dirname(__file__), "rfc_poc.db")
    if not os.path.exists(db_path):
        init_db(db_path)
    # Apply idempotent migrations even when the DB already exists (adds cab_flags)
    migrate_db(db_path)

# ─────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check"""
    return {"status": "ok"}

@app.post("/rfc/upload-document")
async def upload_document(file: UploadFile = File(...)):
    """
    Upload a supporting document (PDF, Word, PowerPoint, or Excel) ahead of
    RFC submission. Extracts text and asks the LLM to suggest values for the
    submission form fields. Returns a document_token to pass back on
    /rfc/submit so the file gets paired with the created RFC.
    """
    filename = file.filename or "document"
    ext = os.path.splitext(filename.lower())[1]
    if ext not in ALLOWED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Please upload a PDF, Word (.docx), PowerPoint (.pptx), or Excel (.xlsx) document.",
        )

    document_token = str(uuid.uuid4())
    tmp_path = os.path.join(UPLOAD_TMP_DIR, f"{document_token}{ext}")

    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        document_text = extract_document_text(tmp_path, filename)
    except Exception:
        os.remove(tmp_path)
        raise HTTPException(status_code=400, detail="Could not read this document — it may be corrupt or unsupported.")

    extracted_fields = extract_rfc_fields(document_text)

    return {
        "document_token": document_token,
        "filename": filename,
        "extracted_fields": extracted_fields,
    }

@app.post("/rfc/submit", response_model=RFCResponse)
async def submit_rfc(req: RFCSubmissionRequest):
    """
    Submit a new RFC. System will:
    1. Auto-classify if type not provided
    2. Score impact/priority/risk
    3. Check against SCC (Standard changes)
    4. Evaluate No Impact criteria
    5. Route to CAB if needed
    """

    rfc_id = str(uuid.uuid4())
    rfc_number = f"CHG{str(int(datetime.now().timestamp()))[-8:]}"

    # Classify change type + score impact/priority/risk in a single pass
    classified_type, impact, priority, risk_level = classify_rfc(
        description=req.description,
        affected_systems=req.affected_systems,
        downtime=req.estimated_downtime_hours,
        test_cases=req.test_cases
    )

    # Auto-classify change type only if the requestor didn't specify one
    if req.change_type is None:
        req.change_type = ChangeTypeEnum(classified_type)

    # Check if Standard change (auto-approve if matched to SCC)
    scc_match = match_scc(req.title, req.affected_systems)
    auto_approved = False
    status = "Submitted"

    if req.change_type == ChangeTypeEnum.STANDARD and scc_match:
        auto_approved = True
        status = "Auto-Approved (Standard Change Catalogue)"

    # Evaluate No Impact
    if req.change_type == ChangeTypeEnum.NO_IMPACT:
        is_no_impact, reasons = evaluate_no_impact(
            description=req.description,
            downtime=req.estimated_downtime_hours,
            affected_systems=req.affected_systems,
            test_cases=req.test_cases
        )
        if not is_no_impact:
            # Ambiguous — escalate to CAB
            status = "Escalated to CAB (Ambiguous No Impact)"
            req.change_type = ChangeTypeEnum.NORMAL

    # Pair an uploaded supporting document (if any) with this RFC — moves the
    # temp file from uploads/tmp/ into a per-RFC folder and re-extracts text
    # (cheap, and avoids trusting a client-supplied cache of the text). The
    # temp file's extension isn't known here (PDF/Word/PowerPoint/Excel), so
    # find it by token rather than assuming .pdf.
    document_filename = None
    document_path = None
    document_text = None
    if req.document_token:
        matches = glob.glob(os.path.join(UPLOAD_TMP_DIR, f"{req.document_token}.*"))
        tmp_path = matches[0] if matches else None
        if tmp_path and os.path.exists(tmp_path):
            ext = os.path.splitext(tmp_path)[1]
            safe_name = os.path.basename(req.document_filename or f"document{ext}") or f"document{ext}"
            if not safe_name.lower().endswith(ext):
                safe_name += ext
            rfc_upload_dir = os.path.join(UPLOAD_DIR, rfc_id)
            os.makedirs(rfc_upload_dir, exist_ok=True)
            final_path = os.path.join(rfc_upload_dir, safe_name)
            shutil.move(tmp_path, final_path)
            document_filename = safe_name
            document_path = final_path
            try:
                document_text = extract_document_text(final_path, safe_name)
            except Exception:
                document_text = None
        # A missing/expired temp file (e.g. stale token) is not an error —
        # the RFC is simply submitted without a paired document.

    # Persist to DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO change_requests (
            id, rfc_number, title, description, change_type, impact, priority,
            risk_level, status, auto_approved, created_at, requestor_name,
            affected_systems, implementation_plan, test_cases, back_out_plan,
            business_justification, estimated_downtime_hours,
            document_filename, document_path, document_text
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rfc_id, rfc_number, req.title, req.description, req.change_type.value,
        impact.value, priority.value, risk_level, status, auto_approved,
        datetime.now().isoformat(), req.requestor_name,
        json.dumps(req.affected_systems), req.implementation_plan,
        req.test_cases, req.back_out_plan, req.business_justification,
        req.estimated_downtime_hours,
        document_filename, document_path, document_text
    ))
    conn.commit()

    created_at = datetime.now().isoformat()
    return RFCResponse(
        id=rfc_id,
        rfc_number=rfc_number,
        title=req.title,
        description=req.description,
        change_type=req.change_type,
        impact=impact,
        priority=priority,
        risk_level=risk_level,
        status=status,
        created_at=created_at,
        cab_decision=None,
        cab_reasoning=None,
        auto_approved=auto_approved,
        requestor_name=req.requestor_name,
        affected_systems=req.affected_systems,
        estimated_downtime_hours=req.estimated_downtime_hours,
        business_justification=req.business_justification,
        implementation_plan=req.implementation_plan,
        test_cases=req.test_cases,
        back_out_plan=req.back_out_plan,
        document_filename=document_filename
    )

@app.get("/rfc/{rfc_id}", response_model=RFCResponse)
async def get_rfc(rfc_id: str):
    """Retrieve RFC details"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM change_requests WHERE id = ?", (rfc_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="RFC not found")

    affected_systems = None
    if row[14]:
        try:
            affected_systems = json.loads(row[14])
        except Exception:
            affected_systems = [s.strip() for s in row[14].split(',') if s.strip()]

    cab_flags = []
    try:
        raw_flags = row["cab_flags"]
        if raw_flags:
            parsed_flags = json.loads(raw_flags)
            if isinstance(parsed_flags, list):
                cab_flags = parsed_flags
    except Exception:
        cab_flags = []

    return RFCResponse(
        id=row[0],
        rfc_number=row[1],
        title=row[2],
        description=row[3],
        change_type=ChangeTypeEnum(row[4]),
        impact=ImpactEnum(row[5]),
        priority=PriorityEnum(row[6]),
        risk_level=row[7],
        status=row[8],
        created_at=row[10],
        cab_decision=row[11],
        cab_reasoning=row[12],
        auto_approved=row[9] == 1,
        requestor_name=row[13],
        affected_systems=affected_systems,
        implementation_plan=row[15],
        test_cases=row[16],
        back_out_plan=row[17],
        business_justification=row[18],
        estimated_downtime_hours=row[19],
        cab_flags=cab_flags,
        document_filename=row["document_filename"]
    )

@app.post("/rfc/{rfc_id}/trigger-cab")
async def trigger_cab_review(rfc_id: str):
    """
    Trigger AI CAB session for RFC.
    Returns CAB decision and reasoning.
    """

    # Fetch RFC
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM change_requests WHERE id = ?", (rfc_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="RFC not found")

    affected_systems = []
    if row[14]:
        try:
            affected_systems = json.loads(row[14])
        except Exception:
            affected_systems = [s.strip() for s in row[14].split(',') if s.strip()]

    rfc_data = {
        "id": row[0],
        "rfc_number": row[1],
        "title": row[2],
        "description": row[3],
        "change_type": row[4],
        "impact": row[5],
        "priority": row[6],
        "risk_level": row[7],
        "affected_systems": affected_systems,
        "business_justification": row[18],
        "implementation_plan": row[15],
        "test_cases": row[16],
        "back_out_plan": row[17],
        "document_text": row["document_text"],
    }

    # Run AI CAB session
    try:
        cab_decision, cab_reasoning, agent_logs, cab_flags = run_ai_cab_session(rfc_data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CAB session failed: {str(e)}")

    # Update DB with decision + flags
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE change_requests
        SET status = ?, cab_decision = ?, cab_reasoning = ?, cab_flags = ?
        WHERE id = ?
    """, ("CAB Reviewed", cab_decision, cab_reasoning, json.dumps(cab_flags), rfc_id))
    conn.commit()
    conn.close()

    return {
        "rfc_id": rfc_id,
        "cab_decision": cab_decision,
        "cab_reasoning": cab_reasoning,
        "agent_logs": agent_logs,
        "cab_flags": cab_flags,
        "status": "CAB Reviewed"
    }

@app.get("/rfc-list")
async def list_rfcs():
    """List all RFCs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, rfc_number, title, change_type, status, created_at FROM change_requests ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    return {
        "rfcs": [
            {
                "id": row[0],
                "rfc_number": row[1],
                "title": row[2],
                "change_type": row[3],
                "status": row[4],
                "created_at": row[5]
            }
            for row in rows
        ]
    }

@app.get("/scc-list")
async def list_scc():
    """List Standard Change Catalogue"""
    return {
        "scc_entries": [
            {"name": "User Account Creation", "risk": "Low", "services": ["Active Directory", "Email"]},
            {"name": "Password Reset", "risk": "Low", "services": ["Active Directory"]},
            {"name": "Disk Space Extension", "risk": "Low", "services": ["Storage", "Infrastructure"]},
            {"name": "Application Log Rotation", "risk": "Low", "services": ["Applications"]},
            {"name": "Monitoring Threshold Update", "risk": "Low", "services": ["Monitoring"]},
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
