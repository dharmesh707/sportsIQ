"""
Rule-based diet/fitness engine per brief section 7. Deterministic and
explainable on purpose — this is NOT an LLM call, which matters for the SIH
"no external AI API for core functionality" constraint and for demo-day
"why should I trust this number" questions.

Macro numbers below are a first-pass placeholder scaffold (rough per-day
grams, NOT personalized to bodyweight yet) — good enough for a Day 1 demo
shape, but flag to the team before final pitch: these should be sanity
checked against real sports-nutrition guidance (e.g. ISSN position stands)
before judges see exact numbers, since a nutrition claim is exactly the kind
of thing an adversarial judge will probe. Cheap fix later: multiply by
bodyweight_kg once the profile has that field.
"""

from app.schemas.common import SportType
from app.schemas.nutrition import Exercise, FoodSuggestion, MacroGuidance, NutritionPlan

# energy-system category per sport, per brief section 7
_ENERGY_CATEGORY: dict[SportType, str] = {
    SportType.BADMINTON: "explosive_anaerobic",
    SportType.CRICKET_BOWLING: "explosive_anaerobic",
    SportType.TENNIS: "mixed_rally_based",
    SportType.TABLE_TENNIS: "mixed_rally_based",
    SportType.ARCHERY: "posture_strength_endurance",
}

_MACROS_BY_CATEGORY: dict[str, MacroGuidance] = {
    "explosive_anaerobic": MacroGuidance(protein_g=140, carbs_g=350, fat_g=70),
    "mixed_rally_based": MacroGuidance(protein_g=120, carbs_g=400, fat_g=65),
    "posture_strength_endurance": MacroGuidance(protein_g=110, carbs_g=280, fat_g=60),
}

_FOOD_BY_CATEGORY: dict[str, list[FoodSuggestion]] = {
    "explosive_anaerobic": [
        FoodSuggestion(item="Moong dal + brown rice", region="Pan-India"),
        FoodSuggestion(item="Paneer bhurji with multigrain roti", region="North India"),
        FoodSuggestion(item="Ragi (finger millet) dosa", region="South India"),
        FoodSuggestion(item="Chana chaat with sprouts", region="Pan-India"),
    ],
    "mixed_rally_based": [
        FoodSuggestion(item="Curd rice with vegetables", region="South India"),
        FoodSuggestion(item="Jowar roti with dal and sabzi", region="Maharashtra"),
        FoodSuggestion(item="Banana + peanut chikki", region="Pan-India"),
        FoodSuggestion(item="Rajma chawal", region="North India"),
    ],
    "posture_strength_endurance": [
        FoodSuggestion(item="Bajra khichdi with ghee", region="Rajasthan/Gujarat"),
        FoodSuggestion(item="Sprouted moong salad", region="Pan-India"),
        FoodSuggestion(item="Egg bhurji with roti", region="Pan-India"),
        FoodSuggestion(item="Almonds + dates", region="Pan-India"),
    ],
}

_EXERCISES_BY_SPORT: dict[SportType, list[Exercise]] = {
    SportType.BADMINTON: [
        Exercise(name="Shoulder external rotation with band", rationale="Protects the rotator cuff under repeated overhead smash load."),
        Exercise(name="Lateral bound + stick", rationale="Builds the lateral court-coverage strength badminton footwork demands."),
    ],
    SportType.TENNIS: [
        Exercise(name="Shoulder external rotation with band", rationale="Same overhead-load protection as badminton, applies to serve motion."),
        Exercise(name="Split-step reaction drill", rationale="Improves reactive footwork timing for rally play."),
    ],
    SportType.TABLE_TENNIS: [
        Exercise(name="Wrist flexor/extensor stretch + strengthening", rationale="Table tennis' fast wrist snap is a common overuse-injury site."),
        Exercise(name="Seated medicine ball rotational throw", rationale="Builds the fast trunk rotation used in loop strokes."),
    ],
    SportType.CRICKET_BOWLING: [
        Exercise(name="Rotational core work (cable woodchopper)", rationale="Directly trains the trunk rotation power source for the bowling action."),
        Exercise(name="Front-leg landing stability drill", rationale="Reduces knee/ankle load at front-foot strike, a common bowling injury point."),
    ],
    SportType.ARCHERY: [
        Exercise(name="Scapular retraction (band pull-apart)", rationale="Builds the back tension needed to hold and control the draw."),
        Exercise(name="Isometric wall hold, draw position", rationale="Builds the postural endurance archery's static hold demands."),
    ],
}


def build_nutrition_plan(sport_type: SportType) -> NutritionPlan:
    category = _ENERGY_CATEGORY[sport_type]
    return NutritionPlan(
        sport_type=sport_type,
        energy_system_category=category,
        macro_guidance=_MACROS_BY_CATEGORY[category],
        food_suggestions=_FOOD_BY_CATEGORY[category],
        exercises=_EXERCISES_BY_SPORT[sport_type],
    )
