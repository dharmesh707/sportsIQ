# SportsIQ — Frontend (React Native / Expo)

Flow, per the project brief: **Screen → Custom Hook → Service → Axios API
client → FastAPI**. Don't skip layers — a screen should never import axios
directly, and a service should never import a screen.

## Folder layout

    frontend/src/
    ├── api/            axios instance + typed API_CONTRACT.md-matching calls
    ├── types/          TypeScript types mirroring API_CONTRACT.md exactly
    ├── constants/      SPORT_TYPES enum, shared app constants
    ├── services/       one file per domain (auth, analyze, nutrition...) —
    │                   wraps api/ calls, no React in here
    ├── hooks/          useAuth, useAnalyze, etc. — calls services/, exposes
    │                   state to screens
    ├── screens/        Dashboard, Analyze, Train, Progress, Profile — one
    │                   folder per screen, built fresh for this project
    ├── components/     shared UI components
    └── navigation/      React Navigation setup

## Getting started (teammate 3 — this is your Day 1 job)

This scaffold has no package.json yet — that's deliberate, since Expo's
create-expo-app generates one with the right native config, and hand-writing
one risks drifting from what Expo actually expects. Run this from frontend/:

    npx create-expo-app@latest . --template blank-typescript

When it asks about overwriting existing files, say no to anything that would
clobber this src/ folder — you want Expo's config files (app.json,
package.json, babel.config.js, etc.) alongside src/, not instead of it.

Then install axios:

    npx expo install axios

Point API_BASE_URL in src/api/client.ts at Dharmesh's running backend
(http://<his-local-ip>:8000 for local dev on the same wifi, or the Railway
URL once deployed — check the team channel for the current value).

## Contract discipline

Every type in src/types/ mirrors ../../API_CONTRACT.md field-for-field.
If the backend changes a field name, src/types/ changes in the same PR —
don't let TypeScript types silently drift from what the backend actually
returns. src/api/client.ts already throws on the contract's exact error
shape ({ error: { code, message } }) — build your error handling against
that, not a generic axios error.
