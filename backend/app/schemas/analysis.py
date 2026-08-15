from datetime import datetime
from typing import Any

from pydantic import Field

from .base import CamelModel
from .common import FaultType, SportType


class Fault(CamelModel):
    type: FaultType
    description: str
    frame: int


class AnalysisResult(CamelModel):
    """
    Mirrors API_CONTRACT.md -> Core analysis -> AnalysisResult exactly.

    metrics and joint_angles are intentionally open dicts (contract marks them
    "sport-specific, see below" / "number values, degrees") — each
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
    Lighter-weight shape for GET /history list items. Contract references
    this type by name without spelling it out — kept intentionally close to
    AnalysisResult minus the heavy per-frame fields (metrics, joint_angles),
    which the history list view doesn't need. If a teammate's UI needs a
    heavier history item, that's a contract change first (see contract's
    "Adding to this file" section), not a silent addition here.
    """

    analysis_id: str
    sport_type: SportType
    action_label: str
    overall_score: float = Field(ge=0, le=100)
    created_at: datetime


class HistoryResponse(CamelModel):
    analyses: list[AnalysisResultSummary]
