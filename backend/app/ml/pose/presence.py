"""Reviewed player-presence metadata keyed by source frame index."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Mapping, cast

PlayerPresence = Literal["PLAYER_PRESENT", "PLAYER_ABSENT", "UNCERTAIN"]
PRESENCE_REVIEW_COLUMNS = ("frame_index", "player_presence", "notes")


@dataclass(frozen=True)
class PlayerPresenceInterval:
    """A contiguous inclusive interval reviewed as player-present."""

    start_frame: int
    end_frame: int


def _validate_status(value: str) -> PlayerPresence:
    if value not in {"PLAYER_PRESENT", "PLAYER_ABSENT", "UNCERTAIN"}:
        raise ValueError(f"Unsupported player_presence value: {value!r}")
    return cast(PlayerPresence, value)


def load_presence_review(path: Path) -> dict[int, PlayerPresence]:
    """Load explicit presence decisions without changing source frame indices."""
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError("Presence review is missing a CSV header")
        missing = [
            column for column in PRESENCE_REVIEW_COLUMNS
            if column not in reader.fieldnames
        ]
        if missing:
            raise ValueError(
                f"Presence review is missing required columns: {', '.join(missing)}"
            )
        decisions: dict[int, PlayerPresence] = {}
        for row_number, row in enumerate(reader, start=2):
            try:
                frame_index = int((row.get("frame_index") or "").strip())
            except ValueError as error:
                raise ValueError(
                    f"Invalid frame_index on presence-review row {row_number}"
                ) from error
            if frame_index < 0:
                raise ValueError(
                    f"frame_index must be non-negative on row {row_number}"
                )
            if frame_index in decisions:
                raise ValueError(
                    f"Duplicate frame_index on presence-review row {row_number}: "
                    f"{frame_index}"
                )
            decisions[frame_index] = _validate_status(
                (row.get("player_presence") or "").strip()
            )
    return decisions


def presence_for_frame(
    frame_index: int,
    reviewed_presence: Mapping[int, PlayerPresence] | None = None,
) -> PlayerPresence:
    """Return reviewed presence or UNCERTAIN when no review exists."""
    if reviewed_presence is None:
        return "UNCERTAIN"
    return reviewed_presence.get(frame_index, "UNCERTAIN")


def present_intervals(
    frame_indices: list[int] | tuple[int, ...],
    reviewed_presence: Mapping[int, PlayerPresence] | None = None,
) -> tuple[PlayerPresenceInterval, ...]:
    """Return contiguous reviewed PLAYER_PRESENT runs in source-frame space."""
    intervals: list[PlayerPresenceInterval] = []
    start: int | None = None
    previous: int | None = None
    for frame_index in frame_indices:
        is_present = (
            presence_for_frame(frame_index, reviewed_presence)
            == "PLAYER_PRESENT"
        )
        contiguous = previous is not None and frame_index == previous + 1
        if is_present:
            if start is None or not contiguous:
                if start is not None and previous is not None:
                    intervals.append(PlayerPresenceInterval(start, previous))
                start = frame_index
        elif start is not None and previous is not None:
            intervals.append(PlayerPresenceInterval(start, previous))
            start = None
        previous = frame_index
    if start is not None and previous is not None:
        intervals.append(PlayerPresenceInterval(start, previous))
    return tuple(intervals)
