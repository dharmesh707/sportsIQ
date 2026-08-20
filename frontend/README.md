# SportsIQ — Frontend (React Native / Expo)

Multi-sport AI coaching app frontend, built against `API_CONTRACT_final.md` as
the single source of truth for every request/response shape.

> **Note on stack:** the SportsIQ master brief specifies React Native (Expo) —
> needed for the on-device Health Connect integration in the Train screen,
> which has no web equivalent. This build follows the brief. (An earlier
> `sportsiq_frontend_build_prompt.md` in the same batch specified a React +
> Vite web app instead; that conflict was flagged and Expo was the confirmed
> choice.)

## Setup

```bash
npm install
npx expo start
```

Health Connect requires a **development build**, not Expo Go:

```bash
npx expo run:android
```

On iOS, Health Connect is unavailable (Android-only API) — the Train screen
detects this and disables sync with an inline explanation rather than
crashing; the rest of the app is unaffected.

Set your backend URL in `.env`:

```
EXPO_PUBLIC_API_BASE_URL=http://localhost:8000
```

## Structure

```
App.tsx                        Entry point: fonts, providers, nav mount
src/
  api/
    types.ts                   Types mirroring API_CONTRACT_final.md exactly
    client.ts                  Single typed fetch client, 401 interceptor hook
  theme/
    tokens.ts                  Design tokens: color, type, spacing, per-sport accents
  context/
    AuthContext.tsx            Token persistence (SecureStore), login/register/logout
  navigation/
    RootNavigator.tsx          Auth stack vs. main tabs, detail screen
    types.ts                   Navigation param types
  screens/
    auth/LoginScreen.tsx
    auth/RegisterScreen.tsx
    AnalyzeScreen.tsx          Video upload + sportType selector + result
    HistoryScreen.tsx          Paginated, filterable list -> detail
    AnalysisDetailScreen.tsx   Full AnalysisResult via GET /analyze/{id}
    DashboardScreen.tsx        Summary, per-sport breakdown, recent, top faults
    ProgressScreen.tsx         Baseline, chart, fault trends per sport/range
    TrainScreen.tsx            Health Connect sync + nutrition plan (optional)
    ProfileScreen.tsx
  components/
    Primitives.tsx             Screen, Card, buttons, text field
    AnalysisResultView.tsx     Shared full-result renderer (Analyze + Detail)
    ScoreRing.tsx               Signature SVG score dial
    FaultCard.tsx               Hard-fault vs soft-note visual language
    SportBadge.tsx / TrendPill.tsx / EmptyState.tsx / ErrorBanner.tsx / LoadingState.tsx
  utils/
    format.ts                  Extend-only enum fallback rendering, dates
    sportMeta.ts                Closed sportType -> label/accent lookup
  health/
    healthConnect.ts            Isolated Health Connect wrapper (Android only)
```

## Contract rules this build enforces

- `sportType` is a **closed** 5-value enum — dropdown-only everywhere, no free text.
- `actionLabel` / `faultCode` / unrecognized `metrics` & `jointAngles` keys are
  **extend-only** — anything unrecognized renders via `formatActionLabel` /
  `formatFaultCode` / `formatMetricKey` (snake_case → Title Case) instead of
  crashing or being hidden.
- Every error response is read as `{ error: { code, message } } ` through one
  path (`ApiError` + `ErrorBanner`) — no endpoint-specific error UI.
- A `401` anywhere clears stored auth and drops to the login stack via one
  interceptor (`configureApiClient` in `api/client.ts`), not per-screen logic.
- Empty states (`dataPoints: []`, zeroed dashboard, zeroed health summary) are
  rendered as real empty states, never as errors.
- No percentile/leaderboard/cross-player comparison exists anywhere in the
  UI or types — Progress is explicitly baseline-vs-self only.
- Health Connect and nutrition are optional enrichment: every other screen
  works fully if both are never called.

## Design

Dark "court at night" base with a single decisive accent (`#C6FF3D`, line-paint
yellow-green) for primary actions and the score dial; per-sport accents are
desaturated, material-grounded colors (shuttle cream, ball orange, target
gold, cricket-whites blue) rather than an arbitrary rainbow. Type: Space
Grotesk for display/instrumentation, Inter for body and data. Signature
element is the 270°-arc `ScoreRing` — a line-call dial, not a generic gauge.
