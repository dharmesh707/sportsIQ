from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass
from math import isfinite
from typing import Optional

from app.ml.features.full_body_temporal import TemporalFeatureSequence


@dataclass(frozen=True)
class EncodedTemporalSequence:
    """
    Fixed-length representation of a temporal feature sequence.

    values:
        Matrix with shape (target_length, number_of_features).
        Missing values remain None.

    feature_names:
        Stable column order for every encoded sequence.
    """

    values: list[list[Optional[float]]]
    feature_names: list[str]
    timestamps_ms: list[float]
    target_length: int
    source_frame_count: int
    feature_schema: str
    feature_version: str


def _is_finite(value: Optional[float]) -> bool:
    return value is not None and isfinite(value)


def _interpolate_feature(
    source_timestamps: list[float],
    source_values: list[Optional[float]],
    target_timestamp: float,
) -> Optional[float]:
    """
    Interpolate a feature at a target timestamp.

    Rules:
      - Exact valid observations are returned directly.
      - Interpolation is only performed between valid observations.
      - No extrapolation is performed outside the valid observation range.
      - Missing observations are skipped.
      - If no valid observations exist, return None.
    """
    valid_observations = [
        (timestamp, value)
        for timestamp, value in zip(source_timestamps, source_values)
        if _is_finite(value)
    ]

    if not valid_observations:
        return None

    valid_timestamps = [item[0] for item in valid_observations]
    valid_values = [item[1] for item in valid_observations]

    insertion_index = bisect_left(valid_timestamps, target_timestamp)

    # Exact observation.
    if insertion_index < len(valid_timestamps):
        if valid_timestamps[insertion_index] == target_timestamp:
            return valid_values[insertion_index]

    # No extrapolation before the first valid observation.
    if insertion_index == 0:
        return None

    # No extrapolation after the last valid observation.
    if insertion_index >= len(valid_timestamps):
        return None

    left_timestamp = valid_timestamps[insertion_index - 1]
    right_timestamp = valid_timestamps[insertion_index]

    left_value = valid_values[insertion_index - 1]
    right_value = valid_values[insertion_index]

    time_delta = right_timestamp - left_timestamp

    if time_delta <= 0:
        return None

    ratio = (target_timestamp - left_timestamp) / time_delta

    interpolated_value = left_value + ratio * (
        right_value - left_value
    )

    return interpolated_value if isfinite(interpolated_value) else None


def encode_temporal_sequence(
    sequence: TemporalFeatureSequence,
    target_length: int = 32,
) -> EncodedTemporalSequence:
    """
    Resample a variable-length temporal feature sequence to fixed length.

    The target timestamps are evenly distributed across the source
    sequence's timestamp range.

    Each feature is interpolated independently. Missing feature values
    remain None when no valid interpolation is possible.
    """
    if target_length < 1:
        raise ValueError("target_length must be at least 1.")

    frames = sequence.frames

    if not frames:
        raise ValueError("Cannot encode an empty temporal sequence.")

    source_timestamps = [
        float(frame.timestamp_ms)
        for frame in frames
    ]

    if not all(isfinite(timestamp) for timestamp in source_timestamps):
        raise ValueError("All frame timestamps must be finite.")

    for index in range(1, len(source_timestamps)):
        if source_timestamps[index] <= source_timestamps[index - 1]:
            raise ValueError(
                "Frame timestamps must be strictly increasing."
            )

    feature_names = sorted(
        {
            feature_name
            for frame in frames
            for feature_name in frame.features
        }
    )

    source_feature_values: dict[str, list[Optional[float]]] = {}

    for feature_name in feature_names:
        values = []

        for frame in frames:
            value = frame.features.get(feature_name)

            if _is_finite(value):
                values.append(float(value))
            else:
                values.append(None)

        source_feature_values[feature_name] = values

    start_timestamp = source_timestamps[0]
    end_timestamp = source_timestamps[-1]

    if target_length == 1:
        target_timestamps = [
            (start_timestamp + end_timestamp) / 2.0
        ]
    else:
        duration = end_timestamp - start_timestamp

        target_timestamps = [
            start_timestamp
            + duration * index / (target_length - 1)
            for index in range(target_length)
        ]

    encoded_values: list[list[Optional[float]]] = []

    for target_timestamp in target_timestamps:
        encoded_frame: list[Optional[float]] = []

        for feature_name in feature_names:
            value = _interpolate_feature(
                source_timestamps,
                source_feature_values[feature_name],
                target_timestamp,
            )

            encoded_frame.append(value)

        encoded_values.append(encoded_frame)

    return EncodedTemporalSequence(
        values=encoded_values,
        feature_names=feature_names,
        timestamps_ms=target_timestamps,
        target_length=target_length,
        source_frame_count=len(frames),
        feature_schema="encoded_full_body_temporal",
        feature_version="1.0.0",
    )