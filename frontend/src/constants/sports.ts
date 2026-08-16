/**
 * Mirrors API_CONTRACT.md's closed sport_type enum EXACTLY.
 * Do not add a value here without adding it to the contract file first.
 */
export const SPORT_TYPES = [
  'badminton',
  'tennis',
  'table_tennis',
  'cricket_bowling',
  'archery',
] as const;

export type SportType = (typeof SPORT_TYPES)[number];

export const SPORT_DISPLAY_NAMES: Record<SportType, string> = {
  badminton: 'Badminton',
  tennis: 'Tennis',
  table_tennis: 'Table Tennis',
  cricket_bowling: 'Cricket Bowling',
  archery: 'Archery',
};
