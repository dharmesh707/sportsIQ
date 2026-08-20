"""
GET /sports - which sports actually have a real analysis pipeline.

Additive endpoint. Nothing existing depends on it, and it does not change any
existing response. It exists so the sport picker can label a sport as COMING
SOON *before* the user records and uploads a clip, rather than letting them
find out after the fact that the numbers were placeholders.
"""

from fastapi import APIRouter

from app.schemas.base import CamelModel
from app.schemas.common import SportType
from app.services import sports_registry

router = APIRouter(tags=["meta"])


class SportSupportInfo(CamelModel):
    sport_type: SportType
    display_name: str
    status: str  # SUPPORTED | PREVIEW
    data_source: str  # measured | simulated
    note: str


class SportsResponse(CamelModel):
    sports: list[SportSupportInfo]


@router.get("/sports", response_model=SportsResponse)
def list_sports() -> SportsResponse:
    return SportsResponse(
        sports=[
            SportSupportInfo(
                sport_type=s.sport_type,
                display_name=s.display_name,
                status=s.status,
                data_source=s.data_source,
                note=s.note,
            )
            for s in sports_registry.all_sports()
        ]
    )
