from .base import CamelModel
from .common import SportType


class MacroGuidance(CamelModel):
    protein_g: float
    carbs_g: float
    fat_g: float


class FoodSuggestion(CamelModel):
    item: str
    region: str


class Exercise(CamelModel):
    name: str
    rationale: str


class NutritionPlan(CamelModel):
    sport_type: SportType
    energy_system_category: str
    macro_guidance: MacroGuidance
    food_suggestions: list[FoodSuggestion]
    exercises: list[Exercise]
    disclaimer: str = "General guidance, not medical or clinical advice."
