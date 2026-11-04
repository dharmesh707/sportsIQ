# SportsIQ

**Your personal AI sports coach. Improve your technique, one rep at a time.**

SportsIQ is an AI-powered multi-sport coaching application that helps athletes analyze their technique using video-based pose estimation, biomechanical measurements, and personalized feedback.

The goal is not to rank players against one another. SportsIQ helps each athlete understand their movement, identify areas for improvement, and track progress against their own performance.

> **Product philosophy: The line judge, not the scoreboard.**
>
> SportsIQ is built around personal improvement and the freedom to play.

---

## Overview

SportsIQ analyzes sports videos through a computer-vision pipeline:

1. Video upload
2. Pose extraction using MediaPipe
3. Joint-angle and movement analysis
4. Comparison against professional reference templates
5. Technique feedback, strengths, and recommendations
6. Personal progress tracking

The core analysis pipeline does not depend on an external LLM API.

### Supported sports

| Sport           | Current implementation          |
| --------------- | ------------------------------- |
| Badminton       | Rule-based MediaPipe analysis   |
| Tennis          | Preview — mock analysis results |
| Table Tennis    | Preview — mock analysis results |
| Cricket Bowling | Preview — mock analysis results |
| Archery         | Preview — mock analysis results |

**Important:** Badminton analysis currently uses rule-based heuristics. It is not a self-trained machine-learning classifier. The other sports are not yet backed by real sport-specific analysis pipelines.

---

## Features

### Authentication

- User registration and login
- JWT-based authentication
- Password hashing with bcrypt
- Authenticated API endpoints

### Video Analysis

- Video upload and processing
- MediaPipe pose estimation
- Joint-angle computation
- Professional reference-template comparison
- Technique scores, strengths, and recommendations

### Progress Tracking

- Analysis history
- Dashboard summaries
- Progress tracking
- Training streaks

### Nutrition

- Rule-based nutrition planning
- Deterministic recommendations without an external LLM API

### Health Data

- Health data synchronization endpoints
- Android Health Connect integration groundwork

---

## Tech Stack

### Backend

- Python 3.12
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0
- JWT authentication
- MediaPipe PoseLandmarker
- OpenCV
- NumPy
- pytest

### Frontend

- React Native
- Expo SDK 51
- TypeScript
- React Navigation

### Database

- SQLite for current local development
- Production database selection is pending

### Machine Learning and Computer Vision

- MediaPipe PoseLandmarker
- OpenCV
- NumPy
- Rule-based biomechanics analysis

---

## Repository Structure

```text
sportsIQ/
├── API_CONTRACT_final.md
├── README.md
├── backend/
│   ├── .env.example
│   ├── requirements.txt
│   ├── models/
│   │   └── pose_landmarker_full.task
│   ├── scripts/
│   │   └── analyze_badminton_video_rule_based.py
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── api/
│       │   └── routers/
│       ├── schemas/
│       ├── models/
│       ├── services/
│       ├── database/
│       ├── ml/
│       └── tests/
└── frontend/
    ├── App.tsx
    ├── app.json
    ├── package.json
    └── src/
        ├── api/
        ├── components/
        ├── context/
        ├── health/
        ├── navigation/
        ├── screens/
        ├── theme/
        └── utils/
```

---

## Getting Started

### Prerequisites

- Python 3.12
- Node.js and npm
- Git
- Expo development environment
- Android device or emulator for mobile testing

### Backend Setup

From the repository root:

```powershell
cd backend
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Create your local environment file:

```powershell
Copy-Item .env.example .env
```

Start the development server:

```powershell
uvicorn app.main:app --reload
```

The API will be available at:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health check: http://127.0.0.1:8000/health

Interactive API documentation is available when `DEBUG=true`.

### Frontend Setup

Open a separate terminal from the repository root:

```powershell
cd frontend
```

Install dependencies:

```powershell
npm install
```

Configure the API base URL using the frontend's environment configuration.

For local development, the backend is available at:

```text
http://127.0.0.1:8000
```

Start Expo:

```powershell
npx expo start
```

For a physical Android device, use the development machine's LAN IP address instead of `127.0.0.1`.

---

## API Documentation

The backend exposes REST endpoints for:

| Area           | Description                           |
| -------------- | ------------------------------------- |
| Authentication | Registration, login, and current user |
| Analysis       | Video analysis and analysis details   |
| History        | Paginated analysis history            |
| Dashboard      | User activity summaries               |
| Progress       | Personal performance tracking         |
| Nutrition      | Rule-based nutrition planning         |
| Health Data    | Health data synchronization           |
| Health         | Application health check              |

The API contract is maintained in:

[`API_CONTRACT_final.md`](./API_CONTRACT_final.md)

The contract defines the request and response shapes, enums, error format, and integration rules.

---

## API Contract Discipline

`API_CONTRACT_final.md` is the single source of truth for every request and response.

Any change to an API boundary must follow these rules:

1. Update the API contract first.
2. Implement the corresponding backend or frontend change.
3. Add or update contract smoke tests.
4. Verify the integration before merging.

### JSON conventions

All JSON keys use camelCase.

Example:

```json
{
  "analysisId": "example-id",
  "sportType": "badminton",
  "overallScore": 85
}
```

### Error format

Every API error follows this structure:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message"
  }
}
```

### Sport types

The current sport enum is:

```text
badminton
tennis
table_tennis
cricket_bowling
archery
```

Do not introduce additional sport types without updating the API contract.

---

## Testing

The backend test suite is located in:

```text
backend/app/tests/
```

Run the complete test suite from the `backend` directory:

```powershell
pytest -v
```

Run contract smoke tests:

```powershell
pytest app/tests/test_contract_smoke.py -v
```

The project currently has 48 backend tests passing in the reviewed codebase.

Always run the tests before pushing changes.

---

## Docker and Deployment

SportsIQ is being prepared for deployment as a publicly accessible demo.

The deployment plan includes:

- Containerized FastAPI backend
- Environment-based production configuration
- Persistent production database
- Public frontend deployment
- Android application distribution

Docker support and production deployment are currently being prepared.

Deployment instructions will be updated after the container build and health checks have been verified.

---

## Known Limitations

SportsIQ is an actively developed project.

Current limitations include:

- Real video analysis is currently implemented for badminton only.
- Other sports return mock analysis results.
- Badminton analysis uses rule-based heuristics rather than a trained classifier.
- The fault-detection system is not fully implemented.
- Personal baseline comparison is not yet implemented.
- Professional reference templates are currently hard-coded.
- Analysis uses a limited contact-frame approach.
- Frontend behavior and production deployment require further verification.

These limitations are being addressed as part of the development roadmap.

---

## Development Roadmap

### Phase 0 — Housekeeping and Deployment Readiness

- Rewrite project documentation
- Add Docker support
- Improve production configuration
- Clearly label unsupported sports

### Phase 1 — ML Refinement

- Build a real-video evaluation dataset
- Improve pose detection and contact-frame estimation
- Implement fault detection
- Introduce personal performance baselines
- Evaluate and calibrate analysis scores

### Phase 2 — Deployment

- Deploy the backend
- Configure a persistent production database
- Configure production environment variables
- Verify API health and application behavior

### Phase 3 — UI Redesign

- Refine the design system
- Improve navigation and screen hierarchy
- Introduce the signature analysis experience
- Improve visual feedback and progress tracking

### Phase 4 — Beta and Scaling

- Introduce asynchronous analysis jobs
- Add rate limits and monitoring
- Improve privacy and consent handling
- Publish an Android demo build
- Collect user feedback

---

## Security Notes

- Never commit real `.env` files or production secrets.
- Use a strong production `SECRET_KEY`.
- Restrict CORS origins in production.
- Keep authentication enabled for protected endpoints.
- Do not expose user videos or personal analysis data publicly.
- Review database persistence and backup requirements before deployment.

---

## Project

SportsIQ was developed as part of Smart India Hackathon 2026 and is being extended into a demo-ready sports-coaching product.

The project follows the principle of personal improvement over competitive ranking.

**Your technique. Your progress. Your game.**
