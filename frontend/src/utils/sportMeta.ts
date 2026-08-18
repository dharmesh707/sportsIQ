import { SportType } from "@/api/types";
import { sportAccent } from "@/theme/tokens";

export function getSportMeta(sportType: SportType) {
  return sportAccent[sportType];
}

export const SPORT_OPTIONS: { value: SportType; label: string }[] = [
  { value: "badminton", label: "Badminton" },
  { value: "tennis", label: "Tennis" },
  { value: "table_tennis", label: "Table Tennis" },
  { value: "cricket_bowling", label: "Cricket Bowling" },
  { value: "archery", label: "Archery" },
];
