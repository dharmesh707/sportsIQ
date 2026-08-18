/**
 * SportsIQ design tokens.
 *
 * Direction: "line judge, not scoreboard." The product's entire premise is a
 * precise measurement layer sitting on top of imprecise human motion — a
 * court/field at dusk under floodlights, chalk lines, a single decisive
 * accent for "in" vs "out" style calls. Dark base (courts read better at
 * night in a demo hall), one court-line off-white for structure, a single
 * hot accent (line-in yellow-green, borrowed from tennis/badminton line
 * paint, not a generic AI-purple) for primary action + score. Per-sport
 * accents are desaturated relatives of real equipment/court colors, not a
 * rainbow picked for variety's sake.
 */

export const color = {
  // Base
  bg: "#0B1210", // near-black, faint green cast — turf at night
  bgElevated: "#121D19", // card surface, one step up
  bgElevated2: "#1A2621", // second elevation (modals, active rows)
  line: "#2A3A34", // hairline dividers, borrowed from court-line grey-green

  // Text
  ink: "#EDF4F0", // primary text — chalk white, not pure #FFF
  inkMuted: "#9DB0A8", // secondary text
  inkFaint: "#5C6E67", // tertiary / placeholder

  // Primary accent — "line-in" yellow-green (court line paint)
  accent: "#C6FF3D",
  accentDim: "#8FBF2A",
  accentInk: "#0B1210", // text placed on top of accent

  // Semantic (hard fault / soft deviation / positive — Freedom-to-Play)
  hardFault: "#FF5D5D", // called out, not negotiable
  softFault: "#F5B942", // logged, not penalized
  positive: "#4ADE80", // strength / improving

  // Status backgrounds (10% alpha equivalents, precomputed for RN)
  hardFaultBg: "#3A1B1B",
  softFaultBg: "#3A2E14",
  positiveBg: "#123222",
} as const;

// Per-sport identity — desaturated, real-material colors, not a rainbow.
export const sportAccent: Record<
  "badminton" | "tennis" | "table_tennis" | "cricket_bowling" | "archery",
  { accent: string; bg: string; label: string }
> = {
  badminton: { accent: "#F2C879", bg: "#2A2418", label: "Badminton" }, // shuttle-cork cream
  tennis: { accent: "#C6FF3D", bg: "#1F2A18", label: "Tennis" }, // ball fuzz yellow-green
  table_tennis: { accent: "#FF8A5C", bg: "#2A1E18", label: "Table Tennis" }, // orange ball
  cricket_bowling: { accent: "#DCEBFF", bg: "#1A222A", label: "Cricket Bowling" }, // red-ball leather / whites
  archery: { accent: "#E0A94A", bg: "#2A2015", label: "Archery" }, // gold target ring
};

export const trendColor: Record<
  "improving" | "stable" | "declining" | "insufficient_data",
  string
> = {
  improving: color.positive,
  stable: color.softFault,
  declining: color.hardFault,
  insufficient_data: color.inkFaint,
};

export const trendLabel: Record<
  "improving" | "stable" | "declining" | "insufficient_data",
  string
> = {
  improving: "Improving",
  stable: "Stable",
  declining: "Declining",
  insufficient_data: "Not enough data yet",
};

export const space = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 20,
  xl: 28,
  xxl: 40,
} as const;

export const radius = {
  sm: 8,
  md: 14,
  lg: 22,
  pill: 999,
} as const;

// Type scale. Display face: Space Grotesk (geometric, slightly mechanical —
// reads as instrumentation, not editorial). Body/data face: Inter, tabular
// figures for score readouts.
export const font = {
  display: "SpaceGrotesk_700Bold",
  displayMedium: "SpaceGrotesk_500Medium",
  body: "Inter_400Regular",
  bodyMedium: "Inter_500Medium",
  bodySemibold: "Inter_600SemiBold",
} as const;

export const type = {
  h1: { fontFamily: font.display, fontSize: 30, lineHeight: 36 },
  h2: { fontFamily: font.display, fontSize: 22, lineHeight: 28 },
  h3: { fontFamily: font.displayMedium, fontSize: 17, lineHeight: 22 },
  scoreHuge: { fontFamily: font.display, fontSize: 56, lineHeight: 60 },
  body: { fontFamily: font.body, fontSize: 15, lineHeight: 21 },
  bodyMedium: { fontFamily: font.bodyMedium, fontSize: 15, lineHeight: 21 },
  small: { fontFamily: font.body, fontSize: 13, lineHeight: 18 },
  smallMedium: { fontFamily: font.bodyMedium, fontSize: 13, lineHeight: 18 },
  label: { fontFamily: font.bodySemibold, fontSize: 11, lineHeight: 14, letterSpacing: 1.2 },
} as const;
