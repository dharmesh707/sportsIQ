from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.health import HealthDataSummary, HealthDataSyncRequest, OkResponse

router = APIRouter(prefix="/health-data", tags=["health-data"])

# In-memory only for now, same pattern as mock_store.py - swap for a real
# health_data table once persistence matters. Per API_CONTRACT.md this is
# an OPTIONAL enrichment layer - never gate /analyze or any core endpoint
# on this data existing. Frontend side (teammate 6): this endpoint is
# already the real implementation, not a stub - wire react-native-health-connect
# to POST here whenever real device data is available.
_summary_store: dict[str, HealthDataSummary] = {}


@router.post("/sync", response_model=OkResponse)
def sync_health_data(current_user: CurrentUser, body: HealthDataSyncRequest) -> OkResponse:
    _summary_store[current_user.id] = HealthDataSummary(
        steps=body.steps,
        heart_rate_avg=body.heart_rate_avg,
        active_minutes=body.active_minutes,
        last_synced_at=body.synced_at,
    )
    return OkResponse()


@router.get("/summary", response_model=HealthDataSummary)
def get_health_summary(current_user: CurrentUser) -> HealthDataSummary:
    return _summary_store.get(
        current_user.id,
        HealthDataSummary(steps=0, heart_rate_avg=0, active_minutes=0, last_synced_at=None),
    )
