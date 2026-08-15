from fastapi import APIRouter, Query

from app.schemas.common import SportType
from app.schemas.nutrition import NutritionPlan
from app.services.nutrition_rules import build_nutrition_plan

router = APIRouter(prefix="/nutrition", tags=["nutrition"])


@router.get("/plan", response_model=NutritionPlan)
def get_nutrition_plan(
    sportType: SportType = Query(...),  # noqa: N803 - contract field naming
) -> NutritionPlan:
    """
    Real rule-based logic (not a Day 1 mock) — see services/nutrition_rules.py.
    No auth required per contract (no Authorization header listed for this
    endpoint) — reconsider that if you want plans tied to a saved user profile
    later; that'd be a contract change first.
    """
    return build_nutrition_plan(sportType)
