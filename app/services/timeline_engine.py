import datetime
import logging
from app.core.observability import tracer, log_structured_event
from app.schemas.orchestration_schemas import ExclusionWindow, Milestone, WorkbackTimeline

logger = logging.getLogger("conductor.services.timeline_engine")


class TimelineEngine:
    """
    Orchestration component responsible for calculating project workback schedules dynamically
    backwards from the external analyst submission target date, adjusting for corporate exclusion windows.
    """

    # Standard milestone definitions with offset T in days and assigned operational phase
    MILESTONE_DEFINITIONS = [
        ("External Deadline", 0, "7. Finalize Publication Strategy & Recognize Contributors"),
        ("Final QA, Packaging, and Form Submission", 2, "6. Manage Executive Reviews & Address Inaccuracies"),
        ("Executive Approval Panel Review", 5, "6. Manage Executive Reviews & Address Inaccuracies"),
        ("Final Video Recording & TOC Bookmark Verification", 8, "5. Deploy On-Demand Demo Environments"),
        ("Consolidated OPM/SME Technical Review Session", 9, "5. Deploy On-Demand Demo Environments"),
        ("Demo Script Rehearsal & Dry-Run", 10, "5. Deploy On-Demand Demo Environments"),
        ("Demo Environment & Sandbox Deployment", 12, "5. Deploy On-Demand Demo Environments"),
        ("Initial SME Curation Draft Deadline", 15, "4. Generate Initial RFI Responses"),
        ("Automated RAG Ingestion and Draft Pre-population", 16, "4. Generate Initial RFI Responses"),
        ("Stakeholder Kickoff & Response Project Alignment", 18, "3. Kick Off Response Project & Align Teams"),
        ("Automated Workback Schedule & Task Routing", 19, "2. Auto-Generate Schedules & Assign Tasks"),
        ("Portfolio Eligibility & Go/No-Go Evaluation", 20, "1. Evaluate Inclusion Criteria & Strategic Participation"),
    ]

    @classmethod
    def generate_timeline(
        cls,
        target_deadline: datetime.datetime,
        exclusion_windows: list[ExclusionWindow] | None = None,
    ) -> WorkbackTimeline:
        """
        Constructs project schedules backwards from `target_deadline`.
        If any milestone falls within an `exclusion_window`, shifts that milestone and all prior
        milestones back in time by the duration of the conflict plus a 24-hour buffer.
        """
        with tracer.start_as_current_span("generate_workback_timeline") as span:
            span.set_attribute("target_deadline", target_deadline.isoformat())
            windows = exclusion_windows or []
            span.set_attribute("exclusion_windows.count", len(windows))

            # Sort milestones from Day T (offset 0) backward to Day T - 20
            sorted_defs = sorted(cls.MILESTONE_DEFINITIONS, key=lambda x: x[1])

            milestones: list[Milestone] = []
            accumulated_shift_duration = datetime.timedelta(days=0)

            for name, offset_days, phase_name in sorted_defs:
                # Calculate original date before any shifts
                original_date = target_deadline - datetime.timedelta(days=offset_days)

                # Apply any shift accumulated from later milestones (closer to Day T)
                current_date = original_date - accumulated_shift_duration
                shifted = (current_date != original_date)
                shift_reason = (
                    f"Shifted by {accumulated_shift_duration.days} days due to later milestone conflicts"
                    if shifted else None
                )

                # Check if current_date falls inside any exclusion window
                # We loop in case shifting out of one window lands directly in an earlier window
                conflict_found = True
                while conflict_found:
                    conflict_found = False
                    for window in windows:
                        if window.start_date <= current_date <= window.end_date:
                            conflict_found = True
                            # Shift backwards to right before start_date plus a 24-hour buffer (1 day earlier than start_date)
                            new_date = window.start_date - datetime.timedelta(days=1)
                            additional_shift = current_date - new_date
                            accumulated_shift_duration += additional_shift
                            current_date = new_date
                            shifted = True
                            shift_reason = (
                                f"Shifted out of exclusion window '{window.name}' "
                                f"({window.start_date.date()} to {window.end_date.date()}) plus 24h buffer"
                            )
                            log_structured_event(logger, "milestone_exclusion_shift_triggered", {
                                "milestone": name,
                                "original_date": original_date.isoformat(),
                                "new_date": current_date.isoformat(),
                                "exclusion_window": window.name,
                                "accumulated_shift_days": accumulated_shift_duration.days,
                            })
                            break

                milestone = Milestone(
                    name=name,
                    operational_phase=phase_name,
                    offset_days=offset_days,
                    target_date=current_date,
                    original_date=original_date,
                    shifted=shifted,
                    shift_reason=shift_reason,
                )
                milestones.append(milestone)

            # Sort milestones chronologically from earliest (T-18) to latest (T) for clear presentation
            milestones.sort(key=lambda m: m.target_date)

            timeline = WorkbackTimeline(
                external_deadline=target_deadline,
                milestones=milestones,
                exclusion_windows_applied=windows,
            )

            log_structured_event(logger, "workback_timeline_generated", {
                "external_deadline": target_deadline.isoformat(),
                "total_milestones": len(milestones),
                "shifted_milestones_count": sum(1 for m in milestones if m.shifted),
                "total_accumulated_shift_days": accumulated_shift_duration.days,
            })
            return timeline
