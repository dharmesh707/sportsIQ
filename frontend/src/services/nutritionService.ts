import { apiClient } from '../api/client';
import { SportType } from '../constants/sports';
import { NutritionPlan } from '../types/api';

export async function getNutritionPlan(sportType: SportType): Promise<NutritionPlan> {
  const { data } = await apiClient.get<NutritionPlan>('/nutrition/plan', {
    params: { sportType },
  });
  return data;
}
