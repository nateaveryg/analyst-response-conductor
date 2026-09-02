import datetime
import uuid
from typing import Literal
from pydantic import BaseModel, Field


class ExclusionWindow(BaseModel):
    """
    Represents a corporate event or freeze window (e.g., Google Cloud Next or Google I/O)
    during which milestones cannot be scheduled.
    """
    name: str = Field(..., description="Name of the corporate event or exclusion window")
    start_date: datetime.datetime = Field(..., description="Start timestamp of the exclusion window")
    end_date: datetime.datetime = Field(..., description="End timestamp of the exclusion window")


class Milestone(BaseModel):
    """
    Individual milestone date calculated dynamically backwards from external submission target.
    """
    name: str = Field(..., description="Name of the workback milestone")
    operational_phase: str = Field(default="4. Generate Initial RFI Responses", description="Assigned phase from the 7-Phase End-to-End Operational Process")
    offset_days: int = Field(..., description="Standard offset in days prior to the target deadline T")
    target_date: datetime.datetime = Field(..., description="Final scheduled timestamp after window adjustments")
    original_date: datetime.datetime = Field(..., description="Original scheduled timestamp before window adjustments")
    shifted: bool = Field(default=False, description="Whether this milestone was shifted due to an exclusion window")
    shift_reason: str | None = Field(default=None, description="Explanation of why this milestone was shifted")


class WorkbackTimeline(BaseModel):
    """
    Completed schedule timeline with exact dates and any applied exclusion shifts.
    """
    external_deadline: datetime.datetime = Field(..., description="Target external analyst deadline (Day T)")
    milestones: list[Milestone] = Field(default_factory=list, description="Chronological list of project milestones")
    exclusion_windows_applied: list[ExclusionWindow] = Field(
        default_factory=list, description="List of exclusion windows considered during calculation"
    )


class TimelineRequest(BaseModel):
    """
    Payload for generating a workback schedule from a target date.
    """
    target_deadline: datetime.datetime = Field(..., description="Submission target deadline")
    exclusion_windows: list[ExclusionWindow] = Field(
        default_factory=list, description="Optional corporate exclusion windows to work around"
    )


class RoutingRequest(BaseModel):
    """
    Payload for initiating SME routing on unassigned RfiQuestion records.
    """
    evaluation_id: uuid.UUID | None = Field(
        default=None, description="Optional Evaluation ID to route all its questions"
    )
    question_ids: list[uuid.UUID] | None = Field(
        default=None, description="Optional explicit list of Question IDs to route"
    )
    confidence_threshold: float = Field(
        default=0.7, description="Minimum similarity confidence required to assign an SME without fallback"
    )


class RoutingResult(BaseModel):
    """
    Outcome summary for a single routed RfiQuestion.
    """
    question_id: uuid.UUID
    section_identifier: str
    assigned_sme_id: str
    routing_method: Literal["Keyword/Semantic Match", "Fallback Coordinator"]
    confidence_score: float
