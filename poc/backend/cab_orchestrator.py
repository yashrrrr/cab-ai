"""
AI CAB Orchestrator — Multi-Agent Deliberation Engine
Coordinates 5 virtual CAB members to review and decide on RFCs.
Uses OpenAI GPT-4o for agent reasoning.
"""

from openai import OpenAI
import json
from typing import Tuple, List, Dict
import os

# Initialize OpenAI client with GitHub endpoint
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set")

# GitHub Models API endpoint
client = OpenAI(
    api_key=api_key,
    base_url="https://models.inference.ai.azure.com"
)

# ─────────────────────────────────────────────────────────────
# Agent Personas (System Prompts)
# ─────────────────────────────────────────────────────────────

AGENT_PERSONAS = {
    "chair": {
        "name": "Change Manager (CAB Chair)",
        "role": "Orchestrate discussion, synthesize perspectives, make final decision.",
        "style": "Pragmatic, decisive, accountable. Asks clarifying questions to resolve blockers.",
        "system_prompt": """You are the Change Manager chairing a Change Advisory Board (CAB) meeting.
Your role is to:
1. Summarize the RFC at the start
2. Solicit expert opinions from Infrastructure, Application, Business, and Security leads
3. Identify consensus or conflicts
4. Ask follow-up questions to resolve concerns
5. Make a final decision (Approve/Reject/Conditional Approval)

Always think about risk accountability: is a human taking responsibility for this change?

Be concise, decisive, and fair to all perspectives.
""",
    },
    "infrastructure": {
        "name": "Infrastructure Specialist",
        "role": "Assess infrastructure impact, downtime, back-out feasibility",
        "style": "Detail-oriented, conservative. Concerned with availability and recovery.",
        "system_prompt": """You are the Infrastructure Specialist reviewing the RFC.
Assess:
1. Downtime impact: Is the change window adequate?
2. Back-out plan: Can we recover quickly if this fails?
3. Resource constraints: Do we have the engineers/capacity?
4. Infrastructure stability: Does this risk cascading failures?
5. Maintenance window: Is the timing appropriate?

Raise concerns if back-out is risky, downtime is extended, or recovery plan is weak.
Be specific with your concerns and recommendations.
""",
    },
    "application": {
        "name": "Application Specialist",
        "role": "Review test coverage, deployment risk, code quality",
        "style": "Quality-focused, asks for evidence. Concerned with regressions.",
        "system_prompt": """You are the Application Specialist reviewing the RFC.
Assess:
1. Test evidence: Are test cases comprehensive? Do they cover edge cases?
2. Deployment risk: How many services affected? Any breaking changes?
3. Rollback: Can we quickly revert if issues arise?
4. Test results: Are test results provided? Any failures?
5. Code review: Is there evidence of peer review?

Flag weak testing or missing deployment evidence. Ask for specifics.
Be skeptical: if test evidence is absent or weak, say so clearly.
""",
    },
    "business": {
        "name": "Business & Service Owner",
        "role": "Advocate for business value, SLA impact, stakeholder communication",
        "style": "Business-first, customer-focused. Asks 'why now?' and 'who benefits?'",
        "system_prompt": """You are the Business Owner / Service Owner reviewing the RFC.
Assess:
1. Business justification: Is there clear value? Why now?
2. SLA impact: Will this affect service level agreements?
3. User communication: Have we notified customers of downtime?
4. Resource allocation: Can we afford to do this (cost, effort)?
5. Priority alignment: Does this align with business strategy?

Ask tough questions about value. If the business case is weak, say so.
Be the voice of the customer: would they approve this change?
""",
    },
    "security": {
        "name": "Security & Compliance Officer",
        "role": "Security risk assessment, compliance, VAPT requirements",
        "style": "Risk-averse, thorough. Asks 'what if this is compromised?'",
        "system_prompt": """You are the Security & Compliance Officer reviewing the RFC.
Assess:
1. Security posture: Does this expose new attack surfaces?
2. Data protection: Are sensitive data adequately protected?
3. VAPT needed: Should we do Vulnerability Assessment + Penetration Testing?
4. Compliance: Any regulatory/audit implications?
5. Access control: Are privilege escalations or permission changes involved?

Be cautious. Flag security concerns immediately.
If VAPT is needed, recommend it. Don't guess on security—escalate when uncertain.
""",
    },
}

# ─────────────────────────────────────────────────────────────
# CAB Session Orchestrator
# ─────────────────────────────────────────────────────────────

def run_ai_cab_session(rfc_data: Dict) -> Tuple[str, str, List[str]]:
    """
    Run an AI CAB session for the given RFC using OpenAI GPT-4o.

    Steps:
    1. Chair summarizes RFC
    2. Each specialist (Infrastructure, Application, Business, Security) reviews
    3. Chair synthesizes and makes decision
    4. Chair issues final decision (Approve/Reject/Conditional)

    Returns:
    - cab_decision: "Approved" | "Rejected" | "Conditional Approval"
    - cab_reasoning: Detailed reasoning from chair
    - agent_logs: List of agent statements for UI display
    """

    agent_logs = []

    # Format RFC for agents
    rfc_summary = format_rfc_summary(rfc_data)

    # Step 1: Chair opens session
    agent_logs.append(
        "📋 CHANGE MANAGER: Opening CAB session for RFC " + rfc_data["rfc_number"]
    )
    agent_logs.append(f"📋 CHANGE MANAGER: \n{rfc_summary}")

    # Step 2: Each specialist reviews (in order)
    specialist_opinions = {}

    for specialist in ["infrastructure", "application", "business", "security"]:
        opinion = get_specialist_opinion(
            specialist, rfc_data, rfc_summary, specialist_opinions
        )
        specialist_opinions[specialist] = opinion
        agent_name = AGENT_PERSONAS[specialist]["name"]
        agent_logs.append(f"\n🔍 {agent_name.upper()}:\n{opinion}")

    # Step 3: Chair synthesizes and decides
    synthesis = synthesize_decision(rfc_data, specialist_opinions, rfc_summary)
    agent_logs.append(f"\n📋 CHANGE MANAGER (SYNTHESIS):\n{synthesis}")

    # Step 4: Parse decision
    cab_decision, cab_reasoning = parse_decision(synthesis)

    return cab_decision, cab_reasoning, agent_logs

# ─────────────────────────────────────────────────────────────
# Helper: Format RFC Summary
# ─────────────────────────────────────────────────────────────

def format_rfc_summary(rfc_data: Dict) -> str:
    """Format RFC into a clear summary for agents"""
    return f"""
RFC NUMBER: {rfc_data['rfc_number']}
TITLE: {rfc_data['title']}
TYPE: {rfc_data['change_type']}
IMPACT: {rfc_data['impact']}
PRIORITY: {rfc_data['priority']}
RISK LEVEL: {rfc_data.get('risk_level', 'N/A')}

DESCRIPTION:
{rfc_data['description']}

AFFECTED SYSTEMS:
{', '.join(rfc_data.get('affected_systems', ['Unknown']))}

IMPLEMENTATION PLAN:
{rfc_data.get('implementation_plan', 'Not provided')}

TEST CASES:
{rfc_data.get('test_cases', 'Not provided')}

BACK-OUT PLAN:
{rfc_data.get('back_out_plan', 'Not provided')}

BUSINESS JUSTIFICATION:
{rfc_data.get('business_justification', 'Not provided')}
"""

# ─────────────────────────────────────────────────────────────
# Helper: Get Specialist Opinion (OpenAI API call)
# ─────────────────────────────────────────────────────────────

def get_specialist_opinion(
    specialist: str, rfc_data: Dict, rfc_summary: str, prior_opinions: Dict
) -> str:
    """
    Get opinion from a specialist agent using OpenAI GPT-4o.
    Considers prior opinions to simulate discussion.
    """

    persona = AGENT_PERSONAS[specialist]
    prior_context = ""

    if prior_opinions:
        prior_context = "\n\nPRIOR SPECIALIST OPINIONS:\n"
        for spec, opinion in prior_opinions.items():
            prior_context += f"- {AGENT_PERSONAS[spec]['name']}: {opinion[:200]}...\n"

    prompt = f"""You are the {persona['name']}.

{prior_context}

Now review this RFC and provide your assessment. Be concise (2-3 paragraphs).
Raise concerns, ask questions, and provide recommendations.

RFC SUMMARY:
{rfc_summary}

Your assessment:"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": persona["system_prompt"]
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=500,
        temperature=0.7
    )

    return response.choices[0].message.content

# ─────────────────────────────────────────────────────────────
# Helper: Synthesize Decision (OpenAI API call)
# ─────────────────────────────────────────────────────────────

def synthesize_decision(
    rfc_data: Dict, specialist_opinions: Dict, rfc_summary: str
) -> str:
    """
    Chair synthesizes all opinions and makes final decision using OpenAI.
    """

    opinions_text = "\n".join(
        [
            f"• {AGENT_PERSONAS[spec]['name']}: {opinion[:300]}"
            for spec, opinion in specialist_opinions.items()
        ]
    )

    prompt = f"""You are the Change Manager (CAB Chair).

You have gathered opinions from your CAB team:

{opinions_text}

Now synthesize these opinions and make a final decision on the RFC.

RFC SUMMARY:
{rfc_summary}

Your decision (include: decision, key concerns, conditions/blockers, recommendations):"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": AGENT_PERSONAS["chair"]["system_prompt"]
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=800,
        temperature=0.7
    )

    return response.choices[0].message.content

# ─────────────────────────────────────────────────────────────
# Helper: Parse Decision
# ─────────────────────────────────────────────────────────────

def parse_decision(synthesis: str) -> Tuple[str, str]:
    """
    Parse chair's synthesis to extract decision (Approve/Reject/Conditional).
    """

    synthesis_lower = synthesis.lower()

    if "reject" in synthesis_lower:
        decision = "Rejected"
    elif "conditional" in synthesis_lower or "subject to" in synthesis_lower:
        decision = "Conditional Approval"
    elif "approve" in synthesis_lower:
        decision = "Approved"
    else:
        decision = "Pending Review"

    return decision, synthesis
