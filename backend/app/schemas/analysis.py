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

    # --- v2 additive fields (all optional, older clients ignore them) ---
    pose_quality: Optional["PoseQualityInfo"] = None
    athlete_comparison: Optional["AthleteComparison"] = None
    feature_comparison: list["FeatureComparisonItem"] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    detailed_recommendations: list["RecommendationItem"] = Field(default_factory=list)
    data_source: str = "measured"  # "measured" | "simulated" - see sports registry


# ---------------------------------------------------------------------------
# v2 ADDITIVE TECHNIQUE FIELDS
# ---------------------------------------------------------------------------
# Everything below was ADDED, not changed. Every field on AnalysisResult that
# existed before still exists with the same type and meaning, and all new
# fields default to None/[] so an older client that ignores them, or a sport
# whose pipeline cannot populate them, both keep working unchanged.
#
# Rule for this block: a field is only ever populated from a value the
# inference pipeline actually measured or computed. Nothing here is filled in
# with a plausible-looking default.


class PoseQualityInfo(CamelModel):
    """Reliability of the pose track. All values measured, none estimated."""

    band: str  # HIGH | MEDIUM | LOW
    detection_rate: float = Field(ge=0, le=1)
    detection_percent: float = Field(ge=0, le=100)
    detected_frames: int
    total_frames: int
    is_reliable: bool
    message: str


class FeatureComparisonItem(CamelModel):
    """One measured joint angle against its reference-profile counterpart."""

    key: str
    label: str
    unit: str
    user_value: float
    reference_value: float
    deviation: float  # signed, user - reference
    abs_deviation: float
    similarity: float = Field(ge=0, le=100)
    verdict: str  # GOOD | SLIGHT_DIFFERENCE | NEEDS_IMPROVEMENT


class ReferenceMatch(CamelModel):
    profile_id: str
    display_name: str
    similarity: float = Field(ge=0, le=100)
    provenance: str  # hand_authored | video_derived
    is_validated: bool


class AthleteComparison(CamelModel):
    """
    Comparison against hand-authored reference profiles.

    `is_validated` is False for every profile currently in the repo. The
    frontend uses it to decide whether it may say "measured reference data"
    or must say "reference profile" - it must never claim the former while
    this is False.
    """

    reference: str  # closest profile id
    reference_display_name: str
    similarity: float = Field(ge=0, le=100)
    level_estimate: str  # BEGINNER | DEVELOPING | INTERMEDIATE | ADVANCED | ELITE_REFERENCE_LIKE
    level_description: str
    comparison_basis: str
    is_validated: bool
    all_matches: list[ReferenceMatch] = Field(default_factory=list)


class RecommendationItem(CamelModel):
    """A recommendation traceable to the measured deviation that produced it."""

    feature_key: str
    text: str
    priority: int
    measured_deviation: float
    drill: str


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
