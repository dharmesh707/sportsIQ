# SportsIQ API Contract — SINGLE SOURCE OF TRUTH

Read this before writing any code that touches a request/response boundary — frontend,
backend, or ML pipeline output. If your code and this file disagree, this file is right;
fix the code, don't fix the file to match what you already wrote.

**Status: FINAL for this hackathon round.** The JSON *shape* of every endpoint below is
locked — do not add, remove, rename, or restructure fields without updating this file
first and flagging it to the whole team, not just committing a change quietly.

The *contents* of a few closed lists (per-sport `actionLabel` values, per-sport
`faultCode` values) are marked "extend-only" below — those grow as training data lands,
but growth means adding new entries, never renaming or removing ones already listed.
Any client (frontend, ML output writer) must treat unrecognized enum values inside an
extend-only list as "unknown, render generically" rather than crashing — this is what
makes the list safely appendable without a contract version bump.

---

## Global rules (the part that prevents integration hell)

1. **All JSON keys are camelCase.** No exceptions. In FastAPI/Pydantic, this does NOT
   happen by default — you must configure it on every response model:
   ```python
   from pydantic import BaseModel, ConfigDict
   from pydantic.alias_generators import to_camel

   class CamelModel(BaseModel):
       model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
   ```
   Every response model in every router inherits `CamelModel`. Copy it, don't reinvent it.

2. **`sportType` values are an exact, closed enum — copy-paste, never retype:**
   `"badminton" | "tennis" | "table_tennis" | "cricket_bowling" | "archery"`
   (lowercase, underscore-separated, exactly as written here). This list is **closed**,
   not extend-only — no sixth sport is being added this round.

3. **Every error response, from every endpoint, has this exact shape:**
   ```json
   { "error": { "code": "string", "message": "string" } }
   ```
   No endpoint ever returns a bare string error or a differently-shaped error object.
   See Section 8 for the closed `code` enum.

4. **All timestamps are ISO 8601 strings in UTC** (e.g. `"2026-08-16T18:22:00Z"`).
   All dates-without-time are `"YYYY-MM-DD"`.

5. **Auth**: every endpoint except `/auth/register` and `/auth/login` requires
   `Authorization: Bearer <accessToken>`. A missing/invalid/expired token returns
   `401` with `error.code = "UNAUTHORIZED"`.

6. **Integration testing happens daily, not at the end.** After any endpoint changes,
   hit it with curl/Postman against this contract before merging — don't trust that it
   matches, check. `backend/app/tests/test_contract_smoke.py` should have one test per
   endpoint in this file; add to it in the same PR as any endpoint change.

---

## 1. Auth

`POST /auth/register` — body: `{ email, password }` → `{ accessToken, user }`
`POST /auth/login` — body: `{ email, password }` → `{ accessToken, user }`
`GET /auth/me` — → `{ user }`

`user` shape: `{ id, email, createdAt }`

Errors: `EMAIL_ALREADY_REGISTERED` (register), `INVALID_CREDENTIALS` (login).

---

## 2. Core analysis

`POST /analyze` — multipart form: `video` (file), `sportType` (string, closed enum above)

Response — `AnalysisResult`:
```json
{
  "analysisId": "string",
  "sportType": "badminton",
  "actionLabel": "FH_SMASH",
  "overallScore": 0,
  "professionalComparison": "string",
  "metrics": { "...": "sport-specific numeric fields, see 2.3" },
  "jointAngles": { "...": "sport-specific, degrees, see 2.3" },
  "faults": [
    {
      "faultCode": "string",
      "type": "hard",
      "description": "string",
      "frame": 0,
      "referenceSource": "string | null"
    }
  ],
  "strengths": ["string"],
  "recommendations": ["string"],
  "createdAt": "ISO8601 string"
}
```

Field notes:
- `faults[].type` is `"hard" | "soft"` per the Freedom-to-Play system. Hard faults must
  be backed by a real external rule/reference range where one exists; `referenceSource`
  holds that citation (e.g. `"ICC Law 24"`) or `null` for soft/style deviations.
- `faults[].faultCode` comes from the per-sport extend-only list in Section 2.4.
- `metrics` and `jointAngles` are open key-value maps (numeric values) — see 2.3 for the
  per-sport key sets defined so far. Undefined keys are allowed to appear as training
  matures; frontend renders any key it doesn't recognize as a generic labeled stat rather
  than hiding it.

### 2.1 `actionLabel` — extend-only, per sport

Frontend/ML: any value not yet in this list is rendered as a formatted fallback
(snake_case → Title Case) rather than crashing.

- **badminton**: `FH_SMASH`, `BH_CLEAR`, `FH_CLEAR`, `SERVE_SHORT`, `SERVE_LONG`, `DRIVE`, `NET_SHOT`
- **tennis**: `FOREHAND_GROUNDSTROKE`, `BACKHAND_GROUNDSTROKE`, `SERVE`, `VOLLEY`, `OVERHEAD_SMASH`
- **table_tennis**: `FOREHAND_LOOP`, `BACKHAND_LOOP`, `PUSH`, `SERVE`, `BLOCK`
- **cricket_bowling**: `FAST_DELIVERY`, `SPIN_DELIVERY`
- **archery**: `FULL_DRAW`, `ANCHOR_HOLD`, `RELEASE`

### 2.2 `faultCode` — extend-only, per sport

Same fallback rule as 2.1 applies. `type` and `referenceSource` given here are the
current defaults for each code; a fault instance's actual `type` can still vary
per-occurrence per Freedom-to-Play (e.g. a borderline case logged soft even for a
normally-hard code) — the list below is the *default classification*, not a hard rule
enforced by the schema itself.

| sportType | faultCode | default type | referenceSource |
|---|---|---|---|
| cricket_bowling | `elbow_extension_excess` | hard | `"ICC Law 24 (>15° extension)"` |
| badminton | `non_bent_elbow_contact` | hard | `null` — pending literature threshold |
| badminton | `racket_face_angle` | soft | `null` |
| badminton | `footwork_stance` | soft | `null` |
| tennis | `contact_point_late` | soft | `null` — pending literature threshold |
| tennis | `follow_through_incomplete` | soft | `null` |
| table_tennis | `wrist_snap_timing` | soft | `null` |
| archery | `bow_arm_collapse` | hard | `null` — pending literature threshold |
| archery | `anchor_point_drift` | soft | `null` |

Tennis and archery hard-fault thresholds are explicitly **not yet literature-sourced**
(open thread, tracked outside this file) — until they are, treat any hard fault emitted
for those two sports as provisional and flag it in the UI as such if easy to do; don't
block the pipeline on it.

### 2.3 `metrics` / `jointAngles` — known keys so far (open map, not closed)

These are illustrative of the numeric key style expected, not exhaustive — ML owner adds
keys as models are trained; no PR needed to *add* a key, just document it here when you do.

- **badminton**: `metrics.racketSpeedMps`, `metrics.contactHeightCm`; `jointAngles.elbowFlexionDeg`, `jointAngles.shoulderRotationDeg`
- **cricket_bowling**: `metrics.releaseHeightCm`; `jointAngles.elbowExtensionDeg` (the one ICC Law 24 checks)
- **archery**: `metrics.drawLengthCm`, `metrics.holdDurationSec`; `jointAngles.bowArmElbowDeg`

### 2.4 `GET /history`

Query params: `page` (int, default 1), `pageSize` (int, default 20, max 100), `sportType` (optional filter, closed enum).

```json
{
  "analyses": [
    {
      "analysisId": "string",
      "sportType": "badminton",
      "actionLabel": "FH_SMASH",
      "overallScore": 0,
      "hardFaultCount": 0,
      "softFaultCount": 0,
      "createdAt": "ISO8601 string"
    }
  ],
  "pagination": { "page": 1, "pageSize": 20, "totalItems": 0, "totalPages": 0 }
}
```
This is `AnalysisResultSummary` — a trimmed version of `AnalysisResult`, no `metrics`/`jointAngles`/`recommendations`. Full detail for one analysis: `GET /analyze/{analysisId}` → full `AnalysisResult` shape from Section 2.

---

## 3. Dashboard & progress

`GET /dashboard` → `DashboardResponse`:
```json
{
  "summary": {
    "totalSessions": 0,
    "sportsPracticed": ["badminton"],
    "currentStreakDays": 0,
    "lastSessionAt": "ISO8601 string | null"
  },
  "sportBreakdown": [
    {
      "sportType": "badminton",
      "sessionCount": 0,
      "averageScore": 0,
      "lastSessionAt": "ISO8601 string | null",
      "trend": "improving"
    }
  ],
  "recentSessions": [
    {
      "sessionId": "string",
      "sportType": "badminton",
      "score": 0,
      "hardFaultCount": 0,
      "softFaultCount": 0,
      "createdAt": "ISO8601 string"
    }
  ],
  "topFaults": [
    {
      "faultCode": "string",
      "sportType": "badminton",
      "faultType": "hard",
      "occurrenceCount": 0
    }
  ],
  "recommendations": ["string"]
}
```
- `recentSessions` capped at 5 most recent — full history stays on `/history`, never duplicate.
- `topFaults` capped at 5, ranked by `occurrenceCount` descending.
- `trend` is `"improving" | "stable" | "declining" | "insufficient_data"`, computed by
  comparing the most recent session's score against the average of all prior sessions in
  that sport: `< 3` sessions → `insufficient_data`; diff `> +5` → `improving`;
  `< -5` → `declining`; else `stable`.
- Never compares against other players — Freedom-to-Play tracks each player against
  their own baseline only. No percentile/leaderboard field exists anywhere in this shape,
  and none should be added.

`GET /progress?sportType=badminton&range=30d` → `ProgressResponse`:
```json
{
  "sportType": "badminton",
  "range": { "start": "2026-07-17", "end": "2026-08-16" },
  "baseline": {
    "initialScore": 0,
    "currentScore": 0,
    "percentChange": 0,
    "establishedAt": "2026-07-17"
  },
  "dataPoints": [
    {
      "date": "2026-07-17",
      "sessionId": "string",
      "score": 0,
      "hardFaultCount": 0,
      "softFaultCount": 0
    }
  ],
  "faultTrends": [
    {
      "faultCode": "string",
      "faultType": "soft",
      "occurrences": [{ "date": "2026-07-17", "count": 0 }]
    }
  ]
}
```
- `sportType` query param is **required**, closed enum from the global rules.
- `range` accepts `"7d" | "30d" | "90d" | "all"`, default `"30d"`.
- If the user has zero sessions for the given sport: `200` with `dataPoints: []`,
  `faultTrends: []`, and `baseline` fields all `0`/today's date — not a `404`. A sport the
  user hasn't tried yet is a valid, empty state, not an error.

---

## 4. Health / wearable data (Health Connect)

`POST /health-data/sync` — body: `{ steps, heartRateAvg, activeMinutes, syncedAt }` → `{ ok: true }`
`GET /health-data/summary` → `{ steps, heartRateAvg, activeMinutes, lastSyncedAt }`

This is an optional enrichment layer — never a dependency for `/analyze` or any other
core endpoint to function. If no Health Connect data has ever been synced,
`GET /health-data/summary` returns `200` with all numeric fields `0` and
`lastSyncedAt: null`, not a `404`.

---

## 5. Nutrition & fitness (rule-based, not ML)

`GET /nutrition/plan?sportType=badminton` →
```json
{
  "sportType": "badminton",
  "energySystemCategory": "explosive_anaerobic",
  "macroGuidance": { "proteinG": 0, "carbsG": 0, "fatG": 0 },
  "foodSuggestions": [{ "item": "string", "region": "string" }],
  "exercises": [{ "name": "string", "rationale": "string" }],
  "disclaimer": "General guidance, not medical or clinical advice."
}
```
`energySystemCategory` — extend-only list, current values:
`"explosive_anaerobic" | "aerobic_endurance" | "mixed_intermittent" | "precision_static"`

Owned by Dharmesh (backend/integration). No other teammate builds a competing version of
this endpoint — see team decision log outside this file if that's ever unclear.

---

## 6. Pagination convention (applies to any future list endpoint)

Any endpoint returning a list that could exceed ~20 items uses this shape, matching
`/history` in Section 2.4:
```json
{ "items": [ "..." ], "pagination": { "page": 1, "pageSize": 20, "totalItems": 0, "totalPages": 0 } }
```
(`/history` names its array `analyses` instead of `items` — endpoint-specific array name
is fine, the `pagination` object shape is what must stay consistent.)

---

## 7. HTTP status code conventions

- `200` — success, including valid-but-empty results (see Sections 3, 4)
- `201` — resource created (`/auth/register`, `/analyze`)
- `400` — malformed request (missing required field, wrong type)
- `401` — missing/invalid/expired token
- `403` — valid token, insufficient permission (not expected to come up this round — no
  role system — but reserved rather than repurposed if it does)
- `404` — requested resource doesn't exist (e.g. `GET /analyze/{analysisId}` for an id
  that isn't there or isn't the caller's)
- `422` — request is well-formed but fails validation (e.g. `sportType` not in the closed enum)
- `500` — unhandled server error

## 8. Error `code` enum — closed, extend-only with team sign-off

`UNAUTHORIZED`, `INVALID_CREDENTIALS`, `EMAIL_ALREADY_REGISTERED`, `VALIDATION_ERROR`,
`NOT_FOUND`, `UNSUPPORTED_SPORT_TYPE`, `VIDEO_PROCESSING_FAILED`, `INTERNAL_ERROR`

Adding a new code is fine (extend-only), but do it in this file first, same PR as the
code — a new error code a frontend dev hasn't seen coming is exactly the integration-day
surprise this contract exists to prevent.

---

## Adding to this file

New endpoint or field? Add it here FIRST, in the same PR as the code, before merging. If
two people need the same endpoint shaped slightly differently, that's a 2-minute
conversation now — not a debugging session on integration day.

**Extend-only lists** (Sections 2.1, 2.2, 5's `energySystemCategory`, Section 8) may grow
by adding entries without a conversation — but never rename or remove an existing entry
without flagging it to the whole team first, since that *does* break already-integrated
clients.
