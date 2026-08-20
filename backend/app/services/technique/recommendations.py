"""
Deterministic recommendation engine.

Every string this module emits is selected by a measured deviation on a
named feature, and carries the feature key and the actual numbers that
triggered it. There is no generic motivational text and no random choice -
the same feature vector always produces the same advice, which is what makes
it auditable.

Direction matters: telling someone to extend the elbow more when they are
already over-extending is worse than saying nothing, so each feature has
separate copy for "too high" and "too low".
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.technique.comparison import ComparisonResult, FeatureComparison
from app.services.technique.config import (
    MAX_RECOMMENDATIONS,
    VERDICT_GOOD,
    VERDICT_NEEDS_WORK,
)


@dataclass(frozen=True)
class Recommendation:
    feature_key: str
    text: str
    priority: int  # 1 = highest
    measured_deviation: float
    drill: str


# feature_key -> (text when user value is ABOVE reference, text when BELOW, drill)
_ADVICE: dict[str, tuple[str, str, str]] = {
    "elbow_angle": (
        "Your elbow is more extended than the reference profile at contact. "
        "Allow a little more flex during preparation so the forearm can snap "
        "through the shuttle rather than reaching for it.",
        "Focus on maintaining a more extended elbow during the hitting phase - "
        "a bent arm at contact lowers the contact point and leaks power.",
        "Shadow swings: pause at contact and check arm extension in a mirror, 3 x 10.",
    ),
    "shoulder_elevation": (
        "Your hitting arm is higher than the reference profile at contact, which "
        "can pull you off balance. Let the shoulder settle slightly and take the "
        "shuttle marginally in front of the body instead.",
        "Work on raising the hitting shoulder during preparation. A low contact "
        "point flattens the shot trajectory and reduces steepness on the smash.",
        "Overhead throw drill with a tennis ball, focusing on a high contact point, 2 x 15.",
    ),
    "knee_angle": (
        "Your legs are straighter than the reference profile at contact. Loading "
        "the knees more will give you a stronger base and more upward drive.",
        "Work on lower-body positioning and knee extension - deep knee flexion at "
        "contact suggests you are hitting without completing the jump or lunge.",
        "Split-step into jump-smash footwork, 4 x 8 reps, focusing on leg drive.",
    ),
    "hip_shoulder_separation": (
        "Your trunk rotation is larger than the reference profile. Over-rotating "
        "can cost you recovery time for the next shot.",
        "Increase hip-to-shoulder separation during preparation. Rotating the "
        "trunk stores energy that the arm releases into the shuttle.",
        "Medicine-ball rotational throws, 3 x 8 each side.",
    ),
    "torso_inclination": (
        "Work on maintaining a more controlled torso position - you are leaning "
        "noticeably more than the reference profile, which reduces balance and "
        "slows recovery.",
        "Your torso is more upright than the reference profile. A slight lean into "
        "the shot helps transfer body weight through contact.",
        "Core stability holds and single-leg balance work, 3 x 30s.",
    ),
}


def build(
    comparison: ComparisonResult, *, reliable: bool
) -> tuple[list[Recommendation], list[str]]:
    """
    Returns (recommendations, strengths_text).

    When pose quality is unreliable, we return a single honest instruction
    about re-recording instead of coaching advice built on angles we do not
    trust. Giving confident technical corrections from a 35%-detection clip
    would be the most damaging thing this system could do.
    """
    if not reliable:
        return (
            [
                Recommendation(
                    feature_key="pose_quality",
                    text=(
                        "Re-record before acting on these numbers. The athlete was "
                        "not detected in enough frames for the joint angles to be "
                        "dependable - film from side-on with the full body in frame, "
                        "in even lighting, with nothing crossing between you and the camera."
                    ),
                    priority=1,
                    measured_deviation=0.0,
                    drill="Re-record the clip and run the analysis again.",
                )
            ],
            [],
        )

    ranked = sorted(
        [f for f in comparison.features if f.verdict == VERDICT_NEEDS_WORK],
        key=lambda f: f.similarity,
    )

    recommendations: list[Recommendation] = []
    for index, feature in enumerate(ranked[:MAX_RECOMMENDATIONS], start=1):
        advice = _ADVICE.get(feature.key)
        if advice is None:
            continue
        above_text, below_text, drill = advice
        text = above_text if feature.deviation > 0 else below_text
        recommendations.append(
            Recommendation(
                feature_key=feature.key,
                text=text,
                priority=index,
                measured_deviation=feature.abs_deviation,
                drill=drill,
            )
        )

    if not recommendations:
        recommendations.append(
            Recommendation(
                feature_key="none",
                text=(
                    "No feature deviated far enough from the reference profile to "
                    "flag. Keep filming from the same angle so changes over time "
                    "stay comparable."
                ),
                priority=1,
                measured_deviation=0.0,
                drill="Repeat the same shot across several sessions to build a baseline.",
            )
        )

    return recommendations, _strength_text(comparison.strengths)


def _strength_text(strengths: list[FeatureComparison]) -> list[str]:
    return [
        f"{f.label} is close to the reference profile "
        f"({f.user_value:.0f}{_unit(f.unit)} vs {f.reference_value:.0f}{_unit(f.unit)})."
        for f in strengths
    ]


def _unit(unit: str) -> str:
    return "\u00b0" if unit == "deg" else f" {unit}"


def to_fault_dicts(comparison: ComparisonResult, contact_frame: int) -> list[dict]:
    """
    Map feature verdicts onto the contract's existing Fault shape.

    NEEDS_IMPROVEMENT -> hard, SLIGHT_DIFFERENCE -> soft. GOOD produces
    nothing. `faults` was previously always an empty list for badminton even
    though the contract and the frontend both already render it.
    """
    faults: list[dict] = []
    for feature in comparison.features:
        if feature.verdict == VERDICT_GOOD:
            continue
        is_hard = feature.verdict == VERDICT_NEEDS_WORK
        direction = "above" if feature.deviation > 0 else "below"
        faults.append(
            {
                "fault_code": f"{feature.key}_deviation",
                "type": "hard" if is_hard else "soft",
                "description": (
                    f"{feature.label} measured {feature.user_value:.0f}"
                    f"{_unit(feature.unit)} at contact, {feature.abs_deviation:.0f}"
                    f"{_unit(feature.unit)} {direction} the reference profile's "
                    f"{feature.reference_value:.0f}{_unit(feature.unit)}."
                ),
                "frame": contact_frame,
                "reference_source": f"reference profile: {comparison.closest.profile_id}",
            }
        )
    return faults
