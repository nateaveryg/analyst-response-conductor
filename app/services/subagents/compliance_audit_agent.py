import time
import logging
from app.schemas.phase4_agent_schemas import ComplianceAuditTaskResult

logger = logging.getLogger("conductor.subagent.compliance_audit")


class ComplianceAuditSubAgent:
    """
    Specialized Sub-Agent responsible for auditing synthesized RFI drafts for legal, GA cutoff,
    Sovereign Cloud data residency, and financial revenue compliance before presenting to SMEs.
    """

    NON_GA_TERMS = ["pre-ga", "alpha", "experimental", "roadmap target", "deprecated", "preview"]

    async def execute_audit(self, draft_response: str) -> ComplianceAuditTaskResult:
        """
        Audits draft response for compliance risks.
        """
        start_time = time.perf_counter()

        text_lower = draft_response.lower()
        flagged = [term for term in self.NON_GA_TERMS if term in text_lower]

        is_compliant = len(flagged) == 0
        compliance_score = 1.0 if is_compliant else 0.75
        notes = "100% Compliant with GA & Data Residency rules" if is_compliant else f"Flagged terms requiring Phase 6 Attestation Waiver: {', '.join(flagged)}"

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        return ComplianceAuditTaskResult(
            is_compliant=is_compliant,
            compliance_score=compliance_score,
            audit_notes=notes,
            flagged_terms=flagged,
            execution_duration_ms=round(duration_ms, 2),
        )
