"""
Turns the detector's real measured detection rate into a quality band the
UI can act on.

No confidence statistic is invented here. The only input is
detected_frames / total_frames, which the detector actually measures.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.services.technique.config import (
    POSE_QUALITY_BANDS,
    POSE_QUALITY_MESSAGES,
    POSE_QUALITY_REJECT_BELOW,
    QUALITY_CAVEAT_BELOW,
    band_for,
)


@dataclass(frozen=True)
class PoseQuality:
    band: str  # HIGH | MEDIUM | LOW | REJECT
    detection_rate: float  # 0.0 - 1.0, as measured
    detected_frames: int
    total_frames: int
    is_reliable: bool
    message: str

    @property
    def percent(self) -> float:
        return round(self.detection_rate * 100, 1)


def _safe_rate(detected_frames: int, total_frames: int) -> float:
    """Guard against divide-by-zero, NaN and inf before any banding happens."""
    if total_frames <= 0:
        return 0.0
    rate = detected_frames / total_frames
    if math.isnan(rate) or math.isinf(rate):
        return 0.0
    return max(0.0, min(1.0, rate))


def assess(detected_frames: int, total_frames: int) -> PoseQuality:
    rate = _safe_rate(detected_frames, total_frames)
    band = band_for(rate, POSE_QUALITY_BANDS, default="REJECT")
    if rate < POSE_QUALITY_REJECT_BELOW:
        band = "REJECT"
    return PoseQuality(
        band=band,
        detection_rate=round(rate, 4),
        detected_frames=max(0, detected_frames),
        total_frames=max(0, total_frames),
        is_reliable=rate >= QUALITY_CAVEAT_BELOW,
        message=POSE_QUALITY_MESSAGES.get(
            band,
            "The athlete could not be detected in enough frames to analyze this clip.",
        ),
    )
