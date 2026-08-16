"""
Day 1 scope: NO real ML wired up. Every function here returns hardcoded fake
data shaped EXACTLY like the real thing will be, so the frontend can build
against real endpoint shapes today.

When Day 2/3 wires in the real MediaPipe + LSTM pipeline (see ml/pose,
ml/angles, ml/sports/<sport>/), replace the body of build_mock_analysis()
with a call into that pipeline - the function signature and return type
(AnalysisResult) should NOT need to change, since the frontend is already
built against this shape.

action_label vocab status per sport (per API_CONTRACT.md's note that each
sport owner defines their own enum "once trained"):
  - badminton: real vocab already exists from BadmintonIQ v1.0 (see contract).
  - tennis / table_tennis / cricket_bowling / archery: PLACEHOLDER labels
    below, marked as such. Swap for the real trained vocab as each sport's
    classifier lands - update this file's comment when you do, so nobody
    mistakes a placeholder for a final label.

fault_code values match API_CONTRACT.md section 2.2's per-sport table
exactly - if you add a new fault_code here, add it to the contract table
in the same PR.
"""

import random
import uuid
from datetime import datetime, timezone

from app.schemas.analysis import AnalysisResult, Fault
from app.schemas.common import FaultType, SportType

# Badminton vocab is real (matches BadmintonIQ v1.0 / brief section 4).
# Everything else is a placeholder until that sport's classifier is trained.
_ACTION_LABELS: dict[SportType, list[str]] = {
    SportType.BADMINTON: [
        "FH_SMASH", "BH_SMASH", "STICK_SMASH", "JUMP_SMASH",
        "FH_CLEAR", "BH_CLEAR", "FH_DROP", "BH_DROP",
        "FH_DRIVE", "BH_DRIVE", "NET_PUSH",
    ],
    SportType.TENNIS: ["FOREHAND", "BACKHAND", "SERVE", "READY_POSITION"],  # placeholder
    SportType.TABLE_TENNIS: ["FOREHAND_LOOP", "BACKHAND_LOOP", "PUSH", "SERVE"],  # placeholder
    SportType.CRICKET_BOWLING: ["FAST_DELIVERY", "SPIN_DELIVERY"],  # placeholder
    SportType.ARCHERY: ["DRAW", "ANCHOR", "RELEASE"],  # placeholder
}

_JOINT_ANGLE_KEYS = [
    "shoulderAngle", "elbowAngle", "wristAngle", "hipAngle", "kneeAngle", "trunkTilt",
]


def _mock_faults(sport: SportType) -> list[Fault]:
    if sport == SportType.CRICKET_BOWLING:
        # Real, defensible hard-fault anchor per the brief: ICC Law 24 -
        # elbow extension > 15 deg between shoulder-height and release = illegal.
        return [
            Fault(
                fault_code="elbow_extension_excess",
                type=FaultType.HARD,
                description="Elbow extension of 18.4 degrees between shoulder-height and "
                "release exceeds the ICC Law 24 limit of 15 degrees - illegal delivery.",
                frame=42,
                reference_source="ICC Law 24 (>15 degrees extension)",
            ),
            Fault(
                fault_code="footwork_stance",
                type=FaultType.SOFT,
                description="Front foot landing angle is wider than the professional baseline, "
                "but within personal-baseline variation.",
                frame=38,
                reference_source=None,
            ),
        ]
    return [
        Fault(
            fault_code="non_bent_elbow_contact",
            type=FaultType.HARD,
            description="Elbow drops below shoulder line at contact, reducing power transfer.",
            frame=51,
            reference_source=None,
        ),
        Fault(
            fault_code="footwork_stance",
            type=FaultType.SOFT,
            description="Stance width slightly narrower than the reference form - consistent "
            "with this player's personal baseline, not penalized.",
            frame=12,
            reference_source=None,
        ),
    ]


def build_mock_analysis(sport_type: SportType) -> AnalysisResult:
    labels = _ACTION_LABELS[sport_type]
    return AnalysisResult(
        analysis_id=str(uuid.uuid4()),
        sport_type=sport_type,
        action_label=random.choice(labels),
        overall_score=round(random.uniform(55, 92), 1),
        professional_comparison=(
            f"Your form is closest to a mid-advanced amateur reference for "
            f"{sport_type.value.replace('_', ' ')}."
        ),
        metrics={
            "swingSpeedMps": round(random.uniform(8, 22), 2),
            "contactFrame": random.randint(30, 60),
            "balanceScore": round(random.uniform(0.5, 1.0), 2),
        },
        joint_angles={key: round(random.uniform(60, 175), 1) for key in _JOINT_ANGLE_KEYS},
        faults=_mock_faults(sport_type),
        strengths=[
            "Consistent follow-through across repeated attempts.",
            "Good head stability through contact.",
        ],
        recommendations=[
            "Work on hip rotation timing to increase power transfer.",
            "Add shoulder mobility drills 2-3x/week.",
        ],
        created_at=datetime.now(timezone.utc),
    )
