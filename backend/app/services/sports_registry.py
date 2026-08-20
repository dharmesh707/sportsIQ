"""
Which sports actually have a real analysis pipeline behind them.

The contract's SportType enum is closed and stays closed. This registry is a
separate, honest statement of MATURITY: badminton runs real MediaPipe
inference; the other four still fall through to build_mock_analysis(), which
returns randomised numbers shaped like the real thing.

That mock exists so the frontend could be built in parallel, and removing it
would break existing tests and the demo. But shipping randomised numbers to a
user without saying so would be the single most dishonest thing in this
codebase, so:

  * every AnalysisResult now carries `data_source`
  * "measured" means real pose inference ran on the uploaded video
  * "simulated" means the numbers are placeholder output, not analysis
  * GET /sports exposes this so the UI can label sports before upload

The frontend must show a preview sport as COMING SOON and must not present
simulated output as a real score.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.common import SportType

DATA_SOURCE_MEASURED = "measured"
DATA_SOURCE_SIMULATED = "simulated"

STATUS_SUPPORTED = "SUPPORTED"
STATUS_PREVIEW = "PREVIEW"


@dataclass(frozen=True)
class SportSupport:
    sport_type: SportType
    status: str
    data_source: str
    display_name: str
    note: str


_REGISTRY: dict[SportType, SportSupport] = {
    SportType.BADMINTON: SportSupport(
        sport_type=SportType.BADMINTON,
        status=STATUS_SUPPORTED,
        data_source=DATA_SOURCE_MEASURED,
        display_name="Badminton",
        note=(
            "Real analysis: MediaPipe pose tracking, measured contact-frame joint "
            "angles, and comparison against hand-authored reference profiles."
        ),
    ),
}

_PREVIEW_NOTE = (
    "Not implemented yet. Uploads for this sport return placeholder numbers so "
    "the interface can be demonstrated - they are not an analysis of your video."
)

_PREVIEW_NAMES = {
    SportType.TENNIS: "Tennis",
    SportType.TABLE_TENNIS: "Table Tennis",
    SportType.CRICKET_BOWLING: "Cricket Bowling",
    SportType.ARCHERY: "Archery",
}

for _sport, _name in _PREVIEW_NAMES.items():
    _REGISTRY[_sport] = SportSupport(
        sport_type=_sport,
        status=STATUS_PREVIEW,
        data_source=DATA_SOURCE_SIMULATED,
        display_name=_name,
        note=_PREVIEW_NOTE,
    )


def get(sport_type: SportType) -> SportSupport:
    return _REGISTRY[sport_type]


def all_sports() -> list[SportSupport]:
    # Supported first, then preview, each in enum order - stable for the UI.
    return sorted(
        _REGISTRY.values(),
        key=lambda s: (0 if s.status == STATUS_SUPPORTED else 1, s.sport_type.value),
    )


def is_supported(sport_type: SportType) -> bool:
    return _REGISTRY[sport_type].status == STATUS_SUPPORTED
