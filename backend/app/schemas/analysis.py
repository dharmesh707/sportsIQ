from datetime import datetime
from typing import Any, Optional
from pydantic import Field
from .base import CamelModel
from .common import FaultType, SportType


class Fault(CamelModel):
    fault_code: str
    type: FaultType
    description: str
    frame: int
    reference_source: Optional[str] = None


class AnalysisResult(CamelModel):
    """
    Mirrors API_CONTRACT_final.md -> Core analysis -> AnalysisResult exactly.
    metrics and joint_angles are intentionally open dicts (contract marks them
    "sport-specific, see below" / "number values, degrees") - each
    ml/sports/<sport>/ module is free to populate whatever keys apply to that
    sport. Don't add sport-specific typed fields here; that would fragment
    the shape sport-by-sport, which the contract explicitly avoids.
    """
    analysis_id: str
    sport_type: SportType
    action_label: str
    overall_score: float = Field(ge=0, le=100)
    professional_comparison: str
    metrics: dict[str, Any]
    joint_angles: dict[str, float]
    faults: list[Fault]
    strengths: list[str]
    recommendations: list[str]
    created_at: datetime


class AnalysisResultSummary(CamelModel):
    """
    Lighter-weight shape for GET /history list items, per contract section
    2.4 exactly - includes hardFaultCount/softFaultCount (was missing here
    before - contract requires them, this schema didn't have them).
    Kept intentionally close to AnalysisResult minus the heavy per-frame
    fields (metrics, joint_angles), which the history list view doesn't need.
    """
    analysis_id: str
    sport_type: SportType
    action_label: str
    overall_score: float = Field(ge=0, le=100)
    hard_fault_count: int
    soft_fault_count: int
    created_at: datetime


class Pagination(CamelModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class HistoryResponse(CamelModel):
    analyses: list[AnalysisResultSummary]
    pagination: Pagination
