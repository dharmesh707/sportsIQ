"""
Composes the raw detector output into the API contract's AnalysisResult.

This is the seam between "what the CV pipeline measured" and "what the user
is told". Every field set here traces back to a measured value or to a
threshold in app/services/technique/config.py - nothing is invented to make
the result screen look fuller.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.analysis import (
    AnalysisResult,
    AthleteComparison,
    FeatureComparisonItem,
    Fault,
    PoseQualityInfo,
    RecommendationItem,
    ReferenceMatch,
)
from app.schemas.common import SportType
from app.services import sports_registry
from app.services.technique import comparison as technique_comparison
from app.services.technique import quality as technique_quality
from app.services.technique import recommendations as technique_recommendations
from scripts.analyze_badminton_video_rule_based import analyze


def _fallback_result(raw: dict, pose: technique_quality.PoseQuality) -> AnalysisResult:
    """
    Used when not a single feature could be compared (every angle came back
    non-finite). Reporting 0% similarity here would read as "terrible
    technique" when it actually means "we measured nothing", so the score is
    reported as 0 with an explicit explanation and no comparison block.
    """
    return AnalysisResult(
        analysis_id=str(uuid.uuid4()),
        sport_type=SportType.BADMINTON,
        action_label=raw["shot_type"],
        overall_score=0.0,
        professional_comparison=(
            "Joint angles could not be measured reliably at the contact frame, so "
            "no technique comparison was produced for this clip."
        ),
        metrics=_metrics(raw, pose),
        joint_angles={k: v for k, v in (raw.get("angles") or {}).items() if v is not None},
        faults=[],
        strengths=[],
        weaknesses=[],
        recommendations=[
            "Re-record side-on with the full body in frame so the joints can be tracked."
        ],
        pose_quality=_pose_quality_info(pose),
        athlete_comparison=None,
        feature_comparison=[],
        detailed_recommendations=[],
        data_source=sports_registry.DATA_SOURCE_MEASURED,
        created_at=datetime.now(timezone.utc),
    )


def _metrics(raw: dict, pose: technique_quality.PoseQuality) -> dict:
    """v1 metric keys preserved exactly; v2 keys appended."""
    return {
        "fps": raw["fps"],
        "detectedFrames": raw["detected_frames"],
        "detectionRate": raw["detection_rate"],
        "contactFrame": raw["contact_frame"],
        "techniqueScore": raw["technique_score"],
        "templateSimilarity": raw["template_similarity"],
        # additive
        "totalFrames": raw.get("total_frames"),
        "poseQualityBand": pose.band,
        "wristPeakVelocity": raw.get("wrist_peak_velocity"),
    }


def _pose_quality_info(pose: technique_quality.PoseQuality) -> PoseQualityInfo:
    return PoseQualityInfo(
        band=pose.band,
        detection_rate=pose.detection_rate,
        detection_percent=pose.percent,
        detected_frames=pose.detected_frames,
        total_frames=pose.total_frames,
        is_reliable=pose.is_reliable,
        message=pose.message,
    )


def analyze_badminton_video(video_path: Path) -> AnalysisResult:
    raw = analyze(video_path, "viktor_axelsen")

    pose = technique_quality.assess(
        detected_frames=raw["detected_frames"],
        total_frames=raw.get("total_frames") or raw["detected_frames"],
    )

    measured_angles = {
        key: value
        for key, value in (raw.get("angles") or {}).items()
        if value is not None
    }
    result = technique_comparison.compare(measured_angles)
    if result is None:
        return _fallback_result(raw, pose)

    recs, strength_text = technique_recommendations.build(result, reliable=pose.is_reliable)
    fault_dicts = technique_recommendations.to_fault_dicts(result, raw["contact_frame"])

    weaknesses = [
        f"{f.label} is {f.abs_deviation:.0f}\u00b0 "
        f"{'above' if f.deviation > 0 else 'below'} the reference profile."
        for f in result.weaknesses
    ]

    # When the pose track is unreliable we still return the measured numbers -
    # hiding them would be worse - but we do not let the headline score imply
    # a confidence the detection rate does not support.
    headline_note = (
        ""
        if pose.is_reliable
        else " Treat this score as provisional - the athlete was not tracked consistently."
    )

    return AnalysisResult(
        analysis_id=str(uuid.uuid4()),
        sport_type=SportType.BADMINTON,
        action_label=raw["shot_type"],
        overall_score=result.overall_similarity,
        professional_comparison=result.comparison_basis + headline_note,
        metrics=_metrics(raw, pose),
        joint_angles=measured_angles,
        faults=[Fault(**f) for f in fault_dicts],
        strengths=strength_text,
        weaknesses=weaknesses,
        recommendations=[r.text for r in recs],
        pose_quality=_pose_quality_info(pose),
        athlete_comparison=AthleteComparison(
            reference=result.closest.profile_id,
            reference_display_name=result.closest.display_name,
            similarity=result.overall_similarity,
            level_estimate=result.level,
            level_description=result.level_description,
            comparison_basis=result.comparison_basis,
            is_validated=result.closest.is_validated,
            all_matches=[
                ReferenceMatch(
                    profile_id=m.profile_id,
                    display_name=m.display_name,
                    similarity=m.similarity,
                    provenance=m.provenance,
                    is_validated=m.is_validated,
                )
                for m in result.all_matches
            ],
        ),
        feature_comparison=[
            FeatureComparisonItem(
                key=f.key,
                label=f.label,
                unit=f.unit,
                user_value=f.user_value,
                reference_value=f.reference_value,
                deviation=f.deviation,
                abs_deviation=f.abs_deviation,
                similarity=f.similarity,
                verdict=f.verdict,
            )
            for f in result.features
        ],
        detailed_recommendations=[
            RecommendationItem(
                feature_key=r.feature_key,
                text=r.text,
                priority=r.priority,
                measured_deviation=r.measured_deviation,
                drill=r.drill,
            )
            for r in recs
        ],
        data_source=sports_registry.DATA_SOURCE_MEASURED,
        created_at=datetime.now(timezone.utc),
    )
