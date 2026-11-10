"""Canonical full-body pose observations for offline processing."""

from __future__ import annotations

import math
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

from app.ml.pose.presence import PlayerPresence


CANONICAL_KEYPOINT_NAMES = (
    "nose",
    "left_eye",
    "right_eye",
    "left_ear",
    "right_ear",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
    "left_heel",
    "right_heel",
    "left_foot_index",
    "right_foot_index",
)

_KEYPOINT_SET = frozenset(CANONICAL_KEYPOINT_NAMES)

_PRESENCE_VALUES = frozenset(
    {
        "PLAYER_PRESENT",
        "PLAYER_ABSENT",
        "UNCERTAIN",
    }
)


def _finite(value: Any, field: str) -> float:
    """Convert a value to float and ensure it is finite."""

    if isinstance(value, bool):
        raise ValueError(f"{field} must be finite")

    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} must be finite") from error

    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")

    return number


def _optional_finite(value: Any, field: str) -> float | None:
    """Validate an optional finite numeric value."""

    if value is None:
        return None

    return _finite(value, field)


def _optional_confidence(value: Any, field: str) -> float | None:
    """Validate an optional confidence-like value in [0, 1]."""

    number = _optional_finite(value, field)

    if number is not None and not 0.0 <= number <= 1.0:
        raise ValueError(f"{field} must be between 0 and 1")

    return number


@dataclass(frozen=True)
class CoordinateMetadata:
    """Coordinate conventions shared by one canonical sequence."""

    image_xy: str = "normalized_image"
    x_formula: str = "x_px / width_px"
    y_formula: str = "y_px / height_px"
    z_convention: str = "estimator_native"
    world_convention: str | None = None

    def __post_init__(self) -> None:
        if self.image_xy != "normalized_image":
            raise ValueError(
                "image_xy must be 'normalized_image'"
            )

        if not self.x_formula or not self.y_formula:
            raise ValueError(
                "coordinate formulas are required"
            )


@dataclass(frozen=True)
class KeypointObservation:
    """
    One raw keypoint observation.

    Derived, interpolated, or imputed values are not represented here.

    x_norm and y_norm are normalized image coordinates. Values outside
    [0, 1] are allowed because estimators may report joints outside the
    image boundary.

    z_native is estimator-specific and must not be assumed comparable
    across different pose estimators.

    confidence, visibility, and presence are optional because not every
    estimator provides all of these values.
    """

    present: bool

    x_norm: float | None = None
    y_norm: float | None = None
    z_native: float | None = None

    confidence: float | None = None
    visibility: float | None = None
    presence: float | None = None

    source_x: float | None = None
    source_y: float | None = None
    source_coordinate_system: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.present, bool):
            raise ValueError("present must be a boolean")

        # Validate raw coordinate values.
        for field in (
            "x_norm",
            "y_norm",
            "z_native",
            "source_x",
            "source_y",
        ):
            _optional_finite(
                getattr(self, field),
                field,
            )

        # Validate optional confidence-like values.
        for field in (
            "confidence",
            "visibility",
            "presence",
        ):
            _optional_confidence(
                getattr(self, field),
                field,
            )

        if self.present:
            if self.x_norm is None or self.y_norm is None:
                raise ValueError(
                    "present keypoints require x_norm and y_norm"
                )

        else:
            # Missing keypoints cannot contain coordinate values.
            if any(
                getattr(self, field) is not None
                for field in (
                    "x_norm",
                    "y_norm",
                    "z_native",
                    "source_x",
                    "source_y",
                )
            ):
                raise ValueError(
                    "missing keypoints cannot contain coordinate values"
                )

        if (
            self.source_coordinate_system is not None
            and not self.source_coordinate_system
        ):
            raise ValueError(
                "source_coordinate_system cannot be empty"
            )

    @classmethod
    def missing(cls) -> "KeypointObservation":
        """Create an explicit missing-keypoint observation."""

        return cls(present=False)


@dataclass(frozen=True)
class FramePoseObservation:
    """
    One source frame containing the complete canonical keypoint map.

    The keypoint mapping is copied and made immutable during
    construction. This prevents external dictionary mutation from
    changing an already-created frame observation.
    """

    frame_index: int
    timestamp_ms: int
    width_px: int
    height_px: int

    keypoints: Mapping[str, KeypointObservation]

    player_presence: PlayerPresence = "UNCERTAIN"

    def __post_init__(self) -> None:
        if (
            isinstance(self.frame_index, bool)
            or not isinstance(self.frame_index, int)
        ):
            raise ValueError(
                "frame_index must be a non-negative integer"
            )

        if self.frame_index < 0:
            raise ValueError(
                "frame_index must be a non-negative integer"
            )

        if (
            isinstance(self.timestamp_ms, bool)
            or not isinstance(self.timestamp_ms, int)
        ):
            raise ValueError(
                "timestamp_ms must be a non-negative integer"
            )

        if self.timestamp_ms < 0:
            raise ValueError(
                "timestamp_ms must be a non-negative integer"
            )

        for field in (
            "width_px",
            "height_px",
        ):
            value = getattr(self, field)

            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value <= 0
            ):
                raise ValueError(
                    f"{field} must be a positive integer"
                )

        if self.player_presence not in _PRESENCE_VALUES:
            raise ValueError(
                f"Unsupported player_presence: "
                f"{self.player_presence!r}"
            )

        if not isinstance(self.keypoints, Mapping):
            raise ValueError(
                "keypoints must be a mapping"
            )

        # Validate the canonical keypoint vocabulary.
        supplied_names = set(self.keypoints)

        if supplied_names != _KEYPOINT_SET:
            missing = sorted(
                _KEYPOINT_SET - supplied_names
            )

            extra = sorted(
                supplied_names - _KEYPOINT_SET
            )

            raise ValueError(
                "keypoints must contain exactly canonical names; "
                f"missing={missing}, extra={extra}"
            )

        # Validate the observations themselves.
        if any(
            not isinstance(value, KeypointObservation)
            for value in self.keypoints.values()
        ):
            raise ValueError(
                "keypoints values must be "
                "KeypointObservation instances"
            )

        # Copy the mapping before wrapping it.
        # MappingProxyType alone would not protect against mutation
        # through another reference to the original dictionary.
        immutable_keypoints = MappingProxyType(
            dict(self.keypoints)
        )

        object.__setattr__(
            self,
            "keypoints",
            immutable_keypoints,
        )


@dataclass(frozen=True)
class CanonicalPoseSequence:
    """Variable-length ordered raw canonical pose observations."""

    frames: tuple[FramePoseObservation, ...]

    estimator_name: str
    estimator_version: str | None
    model_name: str | None

    coordinate_metadata: CoordinateMetadata = CoordinateMetadata()

    schema_name: str = "sportsiq.canonical_pose"
    schema_version: str = "1.0"

    fps: float | None = None

    def __post_init__(self) -> None:
        if not self.estimator_name:
            raise ValueError(
                "estimator_name is required"
            )

        if self.fps is not None:
            if isinstance(self.fps, bool):
                raise ValueError(
                    "fps must be finite and positive when provided"
                )

            if not isinstance(self.fps, (int, float)):
                raise ValueError(
                    "fps must be finite and positive when provided"
                )

            if (
                not math.isfinite(self.fps)
                or self.fps <= 0
            ):
                raise ValueError(
                    "fps must be finite and positive when provided"
                )

        if any(
            not isinstance(frame, FramePoseObservation)
            for frame in self.frames
        ):
            raise ValueError(
                "frames must contain FramePoseObservation instances"
            )

        # Frame indices and timestamps must both increase strictly.
        for previous, current in zip(
            self.frames,
            self.frames[1:],
        ):
            if current.frame_index <= previous.frame_index:
                raise ValueError(
                    "frame_index values must be strictly increasing"
                )

            if current.timestamp_ms <= previous.timestamp_ms:
                raise ValueError(
                    "timestamp_ms values must be strictly increasing"
                )

        # All frames in a sequence must share image dimensions.
        dimensions = {
            (
                frame.width_px,
                frame.height_px,
            )
            for frame in self.frames
        }

        if len(dimensions) > 1:
            raise ValueError(
                "all frames must use the same image dimensions"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the sequence into a JSON-compatible dictionary."""

        return {
            "schema_name": self.schema_name,
            "schema_version": self.schema_version,

            "estimator": {
                "name": self.estimator_name,
                "version": self.estimator_version,
                "model": self.model_name,
            },

            "fps": self.fps,

            "coordinate_policy": {
                "image_xy": self.coordinate_metadata.image_xy,
                "x_formula": self.coordinate_metadata.x_formula,
                "y_formula": self.coordinate_metadata.y_formula,
                "z_convention": self.coordinate_metadata.z_convention,
                "world_convention": (
                    self.coordinate_metadata.world_convention
                ),
            },

            "frames": [
                {
                    "frame_index": frame.frame_index,
                    "timestamp_ms": frame.timestamp_ms,
                    "width_px": frame.width_px,
                    "height_px": frame.height_px,
                    "player_presence": frame.player_presence,

                    "keypoints": {
                        name: observation.__dict__
                        for name, observation
                        in frame.keypoints.items()
                    },
                }
                for frame in self.frames
            ],
        }

    @classmethod
    def from_dict(
        cls,
        data: Mapping[str, Any],
    ) -> "CanonicalPoseSequence":
        """Deserialize a sequence from a JSON-compatible mapping."""

        estimator = data.get("estimator")
        policy = data.get("coordinate_policy", {})

        if (
            not isinstance(estimator, Mapping)
            or not isinstance(policy, Mapping)
        ):
            raise ValueError(
                "estimator and coordinate_policy objects are required"
            )

        raw_frames = data.get("frames")

        if not isinstance(raw_frames, list):
            raise ValueError(
                "frames must be a list"
            )

        frames = tuple(
            FramePoseObservation(
                frame_index=frame["frame_index"],
                timestamp_ms=frame["timestamp_ms"],
                width_px=frame["width_px"],
                height_px=frame["height_px"],

                player_presence=frame.get(
                    "player_presence",
                    "UNCERTAIN",
                ),

                keypoints={
                    name: KeypointObservation(**observation)
                    for name, observation
                    in frame["keypoints"].items()
                },
            )
            for frame in raw_frames
        )

        return cls(
            frames=frames,

            estimator_name=estimator["name"],
            estimator_version=estimator.get("version"),
            model_name=estimator.get("model"),

            coordinate_metadata=CoordinateMetadata(
                image_xy=policy.get(
                    "image_xy",
                    "normalized_image",
                ),
                x_formula=policy.get(
                    "x_formula",
                    "x_px / width_px",
                ),
                y_formula=policy.get(
                    "y_formula",
                    "y_px / height_px",
                ),
                z_convention=policy.get(
                    "z_convention",
                    "estimator_native",
                ),
                world_convention=policy.get(
                    "world_convention",
                ),
            ),

            schema_name=data.get(
                "schema_name",
                "sportsiq.canonical_pose",
            ),

            schema_version=data.get(
                "schema_version",
                "1.0",
            ),

            fps=data.get("fps"),
        )