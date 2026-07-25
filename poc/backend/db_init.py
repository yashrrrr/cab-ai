"""
Database initialization and connection management for RFC PoC
"""

import sqlite3
import os

def init_db(db_path: str = "rfc_poc.db"):
    """Initialize SQLite database with schema"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create change_requests table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS change_requests (
            id TEXT PRIMARY KEY,
            rfc_number TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            change_type TEXT NOT NULL,
            impact TEXT NOT NULL,
            priority TEXT NOT NULL,
            risk_level INTEGER,
            status TEXT NOT NULL,
            auto_approved BOOLEAN DEFAULT 0,
            created_at TEXT NOT NULL,
            cab_decision TEXT,
            cab_reasoning TEXT,
            requestor_name TEXT,
            affected_systems TEXT,
            implementation_plan TEXT,
            test_cases TEXT,
            back_out_plan TEXT,
            business_justification TEXT,
            estimated_downtime_hours REAL,
            cab_flags TEXT
        )
    """)

    # Create CAB decisions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cab_decisions (
            id TEXT PRIMARY KEY,
            rfc_id TEXT NOT NULL,
            decision TEXT NOT NULL,
            reasoning TEXT NOT NULL,
            agent_logs TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY(rfc_id) REFERENCES change_requests(id)
        )
    """)

    # Create audit log table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id TEXT PRIMARY KEY,
            rfc_id TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT,
            FOREIGN KEY(rfc_id) REFERENCES change_requests(id)
        )
    """)

    conn.commit()
    conn.close()

    print(f"[OK] Database initialized: {db_path}")

def migrate_db(db_path: str = "rfc_poc.db"):
    """
    Apply idempotent schema migrations to an existing database.
    Safe to run on every startup — only adds what is missing.
    """

    if not os.path.isabs(db_path):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(script_dir, db_path)

    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()

        existing_columns = [row[1] for row in cursor.execute("PRAGMA table_info(change_requests)")]
        if not existing_columns:
            # Table missing (empty/partial DB file) — create the full schema, then done
            conn.close()
            init_db(db_path)
            return

        # Add cab_flags column if it does not exist yet
        if "cab_flags" not in existing_columns:
            try:
                cursor.execute("ALTER TABLE change_requests ADD COLUMN cab_flags TEXT")
                print("[OK] Migration: added cab_flags column")
            except sqlite3.OperationalError:
                # Another process added it concurrently ("duplicate column name") — safe to ignore
                pass

        conn.commit()
    finally:
        conn.close()

def get_db_connection(db_path: str = "rfc_poc.db") -> sqlite3.Connection:
    """Get database connection"""
    # Get the directory where db_init.py is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    full_db_path = os.path.join(script_dir, db_path)

    conn = sqlite3.connect(full_db_path)
    conn.row_factory = sqlite3.Row  # Return rows as dicts
    return conn

def insert_sample_rfcs():
    """Insert sample RFCs for testing"""

    conn = get_db_connection()
    cursor = conn.cursor()

    sample_rfcs = [
        {
            "id": "rfc-001",
            "rfc_number": "CHG20260724001",
            "title": "User Account Creation Batch",
            "description": "Create 10 new user accounts in Active Directory for Q3 onboarding. Standard routine operation.",
            "change_type": "Standard",
            "impact": "3-Low",
            "priority": "Low",
            "risk_level": 1,
            "status": "Auto-Approved (Standard Change Catalogue)",
            "auto_approved": 1,
            "created_at": "2026-07-24T10:00:00",
            "requestor_name": "Alice Johnson",
            "affected_systems": "Active Directory",
            "business_justification": "Q3 hiring requires new user accounts",
        },
        {
            "id": "rfc-002",
            "rfc_number": "CHG20260724002",
            "title": "Production Database Schema Migration",
            "description": "Add new columns to customer table (name, email, phone). Requires 2-hour downtime during maintenance window. Includes comprehensive test cases and rollback procedure.",
            "change_type": "Normal",
            "impact": "1-High",
            "priority": "High",
            "risk_level": 3,
            "status": "Submitted",
            "auto_approved": 0,
            "created_at": "2026-07-24T11:30:00",
            "requestor_name": "Bob Smith",
            "affected_systems": "Production Database, Customer Portal, Mobile App",
            "business_justification": "Support new data collection requirements for marketing team. Marketing team needs additional customer data fields to enable personalized email campaigns. Expected to increase email open rates by 15-20% based on industry benchmarks.",
            "implementation_plan": """1. Pre-change validation (30 min):
   - Backup production database
   - Verify all customer-related services are in read-only mode
   - Confirm all team members are on standby

2. Schema migration (45 min):
   - Execute ALTER TABLE customer ADD COLUMN (name VARCHAR(255), email VARCHAR(255), phone VARCHAR(20))
   - Create indexes on new columns for query optimization
   - Update table statistics

3. Post-change verification (30 min):
   - Validate schema changes in production
   - Run sample queries against new columns
   - Verify application connectivity
   - Resume normal operations

4. Monitoring (2 hours post-change):
   - Monitor database performance metrics
   - Check application logs for errors
   - Verify data integrity""",
            "test_cases": """Test Environment (Staging):
1. Schema validation: Verify columns exist with correct data types
2. Data insertion: Insert 10,000 sample records with new fields
3. Query performance: Run benchmark queries on new columns (target: <100ms)
4. Index effectiveness: Validate index usage and query plans
5. Application integration: Test all CRUD operations through API
6. Concurrent access: Simulate 100 concurrent users adding customer records
7. Rollback test: Execute rollback procedure and verify data consistency

Results: All tests PASSED ✅
- Query performance: Avg 45ms (target: <100ms)
- Data insertion rate: 5000 records/sec
- Concurrent access: No lock contention
- Rollback time: 2 minutes""",
            "back_out_plan": """ROLLBACK PROCEDURE (If Issues Detected):
1. Immediate actions (First 5 minutes):
   - Switch customer portal to read-only mode
   - Notify all dependent services
   - Begin data restoration from pre-migration backup

2. Rollback execution (Next 30 minutes):
   - Execute: ALTER TABLE customer DROP COLUMN name, email, phone
   - Verify data integrity with checksums
   - Restore table statistics from pre-migration state
   - Revalidate indexes

3. Service restoration (Next 25 minutes):
   - Resume customer portal write operations
   - Clear application caches
   - Verify application health checks pass
   - Send all-clear notification to stakeholders

TOTAL ROLLBACK TIME: ~1 hour (well within 2-hour maintenance window)
RISK: Low (tested and validated in staging)""",
            "estimated_downtime_hours": 2,
        },
        {
            "id": "rfc-003",
            "rfc_number": "CHG20260724003",
            "title": "Update Application Logging Level",
            "description": "Change logging threshold from INFO to DEBUG for troubleshooting. Internal config only, no user-facing impact, no downtime required.",
            "change_type": "No Impact",
            "impact": "3-Low",
            "priority": "Low",
            "risk_level": 1,
            "status": "Submitted",
            "auto_approved": 0,
            "created_at": "2026-07-24T13:00:00",
            "requestor_name": "Carol White",
            "affected_systems": "Application Logging Infrastructure",
            "business_justification": "Improve troubleshooting capability for support team",
            "estimated_downtime_hours": 0,
        },
        {
            "id": "rfc-004",
            "rfc_number": "CHG20260724004",
            "title": "Emergency: Production Cache Cluster Failure",
            "description": "URGENT: Redis cache cluster experiencing critical failures causing application timeouts. Production service severely degraded. Emergency replacement required within 24 hours.",
            "change_type": "Emergency",
            "impact": "1-High",
            "priority": "Critical",
            "risk_level": 5,
            "status": "Submitted",
            "auto_approved": 0,
            "created_at": "2026-07-24T15:45:00",
            "requestor_name": "David Chen",
            "affected_systems": "Production Cache, API Gateway, Core Services",
            "business_justification": "Production outage—immediate action required",
            "estimated_downtime_hours": 1,
        },
        {
            "id": "rfc-005",
            "rfc_number": "CHG20260724005",
            "title": "New Microservice Deployment: Payment Processing v2",
            "description": "Deploy new payment processing microservice (rewritten with improved security, 40% faster). Requires 3-day testing window, complex rollback involving data consistency checks.",
            "change_type": "Normal",
            "impact": "1-High",
            "priority": "Critical",
            "risk_level": 5,
            "status": "Submitted",
            "auto_approved": 0,
            "created_at": "2026-07-24T16:20:00",
            "requestor_name": "Emma Davis",
            "affected_systems": "Payment Processing, Billing System, Financial Reporting, External Payment Gateway",
            "business_justification": """Critical security improvements + 40% performance gain. Q3 deadline.

BUSINESS DRIVERS:
1. Security: Current payment service has known vulnerabilities (CVE-2026-xxxx) affecting PCI-DSS compliance
2. Performance: Transaction processing time increased 20% YoY; customer complaints rising
3. Market timing: Q3 launch aligns with new payment method support (Apple Pay, Google Pay)
4. Revenue impact: 40% faster processing = 15% increase in daily transaction capacity
5. Cost savings: Reduce payment gateway fees by $50K/year through optimized routing""",
            "implementation_plan": """PHASE 1: PRE-DEPLOYMENT (Day 1)
- Deploy Payment v2 to production in shadow mode (parallel processing, no real transactions)
- Run for 24 hours collecting performance metrics and error logs
- Compare results: v1 vs v2 on 1M sample transactions
- Validate security scanning passes (OWASP Top 10, PCI-DSS)

PHASE 2: CANARY DEPLOYMENT (Day 2)
- Route 5% of live transactions to Payment v2
- Monitor error rate, latency, and consistency
- If all metrics green, increase to 25% traffic
- Continue monitoring for 6 hours

PHASE 3: FULL CUTOVER (Day 3)
- 100% traffic to Payment v2
- Keep v1 running in read-only mode for 48 hours (fallback)
- Monitor all metrics continuously
- Coordinate with Billing System and Financial Reporting for data sync""",
            "test_cases": """COMPREHENSIVE TEST SUITE (3-day window):

UNIT TESTS: 500+ test cases
- Payment processing logic: All transaction types (card, ACH, wire)
- PCI-DSS compliance: Data masking, encryption, tokenization
- Error handling: Network failures, timeout scenarios, invalid inputs
- Edge cases: Duplicate transactions, concurrent requests, large amounts

INTEGRATION TESTS: 100+ test cases
- Payment Gateway API: Authorize, capture, refund flows
- Billing System sync: Transaction recording, invoice generation
- Financial Reporting: Settlement reconciliation, reporting accuracy
- Third-party integrations: Apple Pay, Google Pay token validation

LOAD TESTING:
- Peak load: 10,000 TPS (current max capacity)
- Stress test: 15,000 TPS for 30 minutes
- Soak test: 5,000 TPS for 24 hours (stability check)
- Results: v2 handles 12,000+ TPS vs v1's 8,500 TPS (41% improvement)

SECURITY TESTING:
- Penetration testing: OWASP Top 10 vulnerabilities (PASSED)
- Data validation: SQL injection, XSS, CSRF attacks (PASSED)
- PCI-DSS compliance scan: Level 1 requirements (PASSED)

TEST COVERAGE: 94% (target: >90%)
DEFECT DENSITY: 0.3 bugs per 1000 LOC (target: <0.5)""",
            "back_out_plan": """IMMEDIATE ROLLBACK PROCEDURE (If Critical Issues Detected):

TRIGGER POINTS for rollback:
- Error rate >0.5% on any transaction type
- Payment processing latency >2 seconds (p99)
- Billing sync failures >10 in any 1-hour window
- Security scan failures in audit logs

ROLLBACK EXECUTION (Max 30 minutes):
1. Switch all traffic back to Payment v1 (instant, via load balancer)
2. Pause new transactions for 5 minutes (allow in-flight to complete)
3. Verify v1 transaction processing normal
4. Check Billing System backlog (should clear within 30 min)
5. Financial Reporting reconciliation (compare v2 logs vs v1)
6. Send incident notification to all stakeholders

DATA CONSISTENCY RECOVERY (If needed):
- Transactions processed by v2 during outage: tracked in audit log
- Re-process missing transactions in Billing System
- Reconcile Financial Reporting with manual verification
- Expected time: 2-4 hours (worst case)

WORST-CASE SCENARIO:
- Full rollback time: 30 minutes
- Data reconciliation: 4 hours
- Total recovery time: ~5 hours (well within business hours)

RISK: Medium (well-tested fallback, clear rollback path)""",
            "estimated_downtime_hours": 0.5,
        },
    ]

    for rfc in sample_rfcs:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO change_requests (
                    id, rfc_number, title, description, change_type, impact, priority,
                    risk_level, status, auto_approved, created_at, requestor_name,
                    affected_systems, business_justification, estimated_downtime_hours,
                    implementation_plan, test_cases, back_out_plan
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                rfc["id"],
                rfc["rfc_number"],
                rfc["title"],
                rfc["description"],
                rfc["change_type"],
                rfc["impact"],
                rfc["priority"],
                rfc["risk_level"],
                rfc["status"],
                rfc["auto_approved"],
                rfc["created_at"],
                rfc["requestor_name"],
                rfc.get("affected_systems", ""),
                rfc.get("business_justification", ""),
                rfc.get("estimated_downtime_hours", 0),
                rfc.get("implementation_plan", ""),
                rfc.get("test_cases", ""),
                rfc.get("back_out_plan", ""),
            ))
        except sqlite3.IntegrityError:
            pass  # Already exists

    conn.commit()
    conn.close()
    print("[OK] Sample RFCs inserted")

if __name__ == "__main__":
    init_db()
    migrate_db()
    insert_sample_rfcs()
