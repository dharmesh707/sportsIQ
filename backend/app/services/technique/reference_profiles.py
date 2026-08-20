"""
Loads the hand-authored reference profiles from data/reference_profiles.json.

Kept as data rather than a Python dict so the provenance metadata travels
with the numbers - the API refuses to describe a profile as validated unless
the file itself says `provenance: "video_derived"`, which nothing currently
does. See that file's _README block.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.services.technique.config import FEATURE_SPEC_BY_KEY

_DATA_PATH = Path(__file__).resolve().parent / "data" / "reference_profiles.json"

PROVENANCE_HAND_AUTHORED = "hand_authored"
PROVENANCE_VIDEO_DERIVED = "video_derived"


@dataclass(frozen=True)
class ReferenceProfile:
    id: str
    display_name: str
    style_note: str
    provenance: str
    source_note: str
    features: dict[str, float]

    @property
    def is_validated(self) -> bool:
        """
        True only when the profile claims to come from real measurement.

        Nothing in this repo does. This gate exists so that if someone adds
        real data later, the wording upgrades automatically - and so nobody
        can accidentally claim validation for a hand-typed number.
        """
        return self.provenance == PROVENANCE_VIDEO_DERIVED


class ReferenceProfileError(RuntimeError):
    """Raised when the profiles file is missing or structurally invalid."""


@lru_cache(maxsize=1)
def load_profiles() -> tuple[ReferenceProfile, ...]:
    if not _DATA_PATH.exists():
        raise ReferenceProfileError(
            f"Reference profile data file is missing: {_DATA_PATH}"
        )
    try:
        raw = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ReferenceProfileError(f"Reference profile file is not valid JSON: {exc}") from exc

    entries = raw.get("profiles")
    if not isinstance(entries, list) or not entries:
        raise ReferenceProfileError("Reference profile file contains no profiles.")

    known_keys = set(FEATURE_SPEC_BY_KEY)
    profiles: list[ReferenceProfile] = []
    for entry in entries:
        features = entry.get("features") or {}
        # Silently ignoring an unknown feature key would let a typo quietly
        # drop out of every comparison, so fail loudly at load time instead.
        unknown = set(features) - known_keys
        if unknown:
            raise ReferenceProfileError(
                f"Profile '{entry.get('id')}' has features not in FEATURE_SPECS: {sorted(unknown)}"
            )
        if not features:
            raise ReferenceProfileError(f"Profile '{entry.get('id')}' has no features.")
        profiles.append(
            ReferenceProfile(
                id=str(entry["id"]),
                display_name=str(entry.get("display_name", entry["id"])),
                style_note=str(entry.get("style_note", "")),
                provenance=str(entry.get("provenance", PROVENANCE_HAND_AUTHORED)),
                source_note=str(entry.get("source_note", "")),
                features={k: float(v) for k, v in features.items()},
            )
        )
    return tuple(profiles)


def get_profile(profile_id: str) -> ReferenceProfile:
    for profile in load_profiles():
        if profile.id == profile_id:
            return profile
    raise KeyError(f"Unknown reference profile: {profile_id}")


def profile_ids() -> list[str]:
    return [p.id for p in load_profiles()]


def any_validated() -> bool:
    """True if ANY loaded profile claims real measured provenance."""
    return any(p.is_validated for p in load_profiles())
