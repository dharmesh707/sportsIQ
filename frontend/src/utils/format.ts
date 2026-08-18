/**
 * Rendering rules for the contract's extend-only lists (actionLabel,
 * faultCode, and unrecognized metrics/jointAngles keys — Sections 2.1-2.3).
 * These values grow as training data lands; anything we don't recognize
 * yet must render as a readable fallback, never crash, never hide.
 */

export function snakeToTitleCase(value: string): string {
  return value
    .toLowerCase()
    .split(/[_\s]+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

// actionLabel values in the contract are already UPPER_SNAKE (e.g. FH_SMASH).
export function formatActionLabel(actionLabel: string): string {
  return snakeToTitleCase(actionLabel);
}

// faultCode values are lower_snake (e.g. elbow_extension_excess).
export function formatFaultCode(faultCode: string): string {
  return snakeToTitleCase(faultCode);
}

// metrics/jointAngles keys are camelCase (e.g. racketSpeedMps). Split on
// camel boundaries, then title-case, and lift a trailing unit token if we
// recognize one so labels read like "Racket Speed (m/s)" not "Racket Speed Mps".
const UNIT_SUFFIXES: Record<string, string> = {
  Mps: "m/s",
  Cm: "cm",
  Deg: "°",
  Sec: "s",
  Kg: "kg",
};

export function formatMetricKey(key: string): string {
  const words = key.replace(/([a-z0-9])([A-Z])/g, "$1 $2").split(" ").filter(Boolean);
  const last = words[words.length - 1];
  if (last && UNIT_SUFFIXES[last]) {
    const unit = UNIT_SUFFIXES[last];
    const label = words
      .slice(0, -1)
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(" ");
    return `${label} (${unit})`;
  }
  return words.map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(" ");
}

export function formatDateShort(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function formatRelativeDay(iso: string | null): string {
  if (!iso) return "No sessions yet";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return iso;
  const diffMs = Date.now() - then;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  if (diffDays <= 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  return `${diffDays} days ago`;
}

export function formatPercent(value: number): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}
