from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas.health import HealthDataSummary, HealthDataSyncRequest, OkResponse

router = APIRouter(prefix="/health-data", tags=["health-data"])

# In-memory only for Day 1 stub. Day 2 TODO (per brief section 8): Teammate 6
# hands off a working react-native-health-connect flow; this becomes a real
# ingestion endpoint writing to a health_data table. Contract explicitly
# marks this an OPTIONAL enrichment layer — never gate /analyze on it.
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
