# SportsIQ API Contract — SINGLE SOURCE OF TRUTH

Read this before writing any code that touches a request/response boundary — frontend,
backend, or ML pipeline output. If your code and this file disagree, this file is right;
fix the code, don't fix the file to match what you already wrote.

## Global rules (the part that prevents integration hell)

1. **All JSON keys are camelCase.** No exceptions. In FastAPI/Pydantic, this does NOT happen
   by default — you must configure it:
   ```python
   from pydantic import BaseModel, ConfigDict
   from pydantic.alias_generators import to_camel

   class AnalysisResult(BaseModel):
       model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
       analysis_id: str   # serializes as "analysisId"
       overall_score: float  # serializes as "overallScore"
   ```
   Every response model in every router must use this config. Copy it, don't reinvent it.

2. **`sport_type` values are an exact, closed enum — copy-paste these, never retype:**
   `"badminton" | "tennis" | "table_tennis" | "cricket_bowling" | "archery"`
   (lowercase, underscore-separated, exactly as written here)

3. **Every error response, from every endpoint, has this exact shape:**
   ```json
   { "error": { "code": "string", "message": "string" } }
   ```
   No endpoint returns a bare string error or a differently-shaped error object.

4. **Integration testing happens daily, not at the end.** After any endpoint changes, hit it
   with curl/Postman against this contract before merging — don't trust that it matches, check.

---

## Auth

`POST /auth/register` — body: `{ email, password }` → `{ accessToken, user }`
`POST /auth/login` — body: `{ email, password }` → `{ accessToken, user }`
`GET /auth/me` — header: `Authorization: Bearer <token>` → `{ user }`

`user` shape: `{ id, email, createdAt }`

---

## Core analysis

`POST /analyze` — multipart form: `video` (file), `sportType` (string, see enum above)
Requires `Authorization: Bearer <token>`.

Response — `AnalysisResult`:
```json
{
  "analysisId": "string",
  "sportType": "badminton",
  "actionLabel": "string",
  "overallScore": 0,
  "professionalComparison": "string",
  "metrics": { "...": "sport-specific, see below" },
  "jointAngles": { "...": "number values, degrees" },
  "faults": [
    { "type": "hard", "description": "string", "frame": 0 },
    { "type": "soft", "description": "string", "frame": 0 }
  ],
  "strengths": ["string"],
  "recommendations": ["string"],
  "createdAt": "ISO8601 string"
}
```
Note: `mistakes` (v1.0 field) is renamed `faults` in this contract and now carries `type`
(hard/soft) per the Freedom-to-Play system — update any old client code still expecting
`mistakes` as a flat string array.

`actionLabel` values are sport-specific (e.g. `FH_SMASH` for badminton, `FOREHAND_LOOP` for
table tennis) — each sport owner defines their own enum list in this file once trained; add
it as a subsection below when ready, don't invent ad hoc strings mid-build.

`GET /history` → `{ analyses: [AnalysisResultSummary] }`
`GET /dashboard` → dashboard aggregate (unchanged from v1.0 shape — see existing code)
`GET /progress` → progress/skill data (unchanged from v1.0 shape — see existing code)

---

## Health / wearable data (Health Connect)

`POST /health-data/sync` — body: `{ steps, heartRateAvg, activeMinutes, syncedAt }` → `{ ok: true }`
`GET /health-data/summary` → `{ steps, heartRateAvg, activeMinutes, lastSyncedAt }`

This is an optional enrichment layer — never a dependency for `/analyze` to function.

---

## Nutrition & fitness (rule-based, not ML — see dataset scaffold README)

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

---

## Adding to this file

New endpoint or field? Add it here FIRST, in the same PR as the code, before merging. If two
people need the same endpoint shaped slightly differently, that's a 2-minute conversation now —
not a debugging session on integration day.
