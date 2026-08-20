from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.models.health_data import HealthDataRecord
from app.schemas.health import HealthDataSummary, HealthDataSyncRequest, OkResponse

router = APIRouter(prefix="/health-data", tags=["health-data"])

# Per API_CONTRACT_final.md this is an OPTIONAL enrichment layer - never
# gate /analyze or any core endpoint on this data existing. Frontend side
# (teammate 6): this endpoint is already the real implementation, not a
# stub - wire react-native-health-connect to POST here whenever real
# device data is available. One row per user (upsert on sync) - matches
# the contract exactly, no history is exposed, so none is stored.


@router.post("/sync", response_model=OkResponse)
def sync_health_data(
    current_user: CurrentUser, db: DbSession, body: HealthDataSyncRequest
) -> OkResponse:
    record = db.get(HealthDataRecord, current_user.id)
    if record is None:
        record = HealthDataRecord(user_id=current_user.id)
        db.add(record)
    record.steps = body.steps
    record.heart_rate_avg = body.heart_rate_avg
    record.active_minutes = body.active_minutes
    record.last_synced_at = body.synced_at
    db.commit()
    return OkResponse()


@router.get("/summary", response_model=HealthDataSummary)
def get_health_summary(current_user: CurrentUser, db: DbSession) -> HealthDataSummary:
    record = db.get(HealthDataRecord, current_user.id)
    if record is None:
        return HealthDataSummary(steps=0, heart_rate_avg=0, active_minutes=0, last_synced_at=None)
    return HealthDataSummary(
        steps=record.steps,
        heart_rate_avg=record.heart_rate_avg,
        active_minutes=record.active_minutes,
        last_synced_at=record.last_synced_at,
    )
