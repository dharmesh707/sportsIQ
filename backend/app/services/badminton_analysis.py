"""Adapt the detector's raw result to the existing analysis API contract."""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.schemas.analysis import AnalysisResult
from app.schemas.common import SportType
from scripts.analyze_badminton_video_rule_based import analyze


def analyze_badminton_video(video_path: Path) -> AnalysisResult:
    raw = analyze(video_path, "viktor_axelsen")
    return AnalysisResult(
        analysis_id=str(uuid.uuid4()),
        sport_type=SportType.BADMINTON,
        action_label=raw["shot_type"],
        overall_score=raw["technique_score"],
        professional_comparison=(
            f"Rule-based biomechanics comparison with the {raw['template']} template; "
            "this is coarse technique feedback, not one of the six dataset action classes."
        ),
        metrics={
            "fps": raw["fps"], "detectedFrames": raw["detected_frames"],
            "detectionRate": raw["detection_rate"], "contactFrame": raw["contact_frame"],
            "techniqueScore": raw["technique_score"],
            "templateSimilarity": raw["template_similarity"],
        },
        joint_angles=raw["angles"],
        faults=[],
        strengths=["Pose was detected across enough frames for technique feedback."],
        recommendations=["Use the contact frame and technique score to guide the next practice session."],
        created_at=datetime.now(timezone.utc),
    )