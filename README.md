SportsIQ
Your personal AI sports coach. Improve your technique, one rep at a
time.

SportsIQ is an AI-powered multi-sport coaching application that helps
athletes analyze their technique using video-based pose estimation,
biomechanical measurements, and personalized feedback.

The goal is not to rank players against one another. SportsIQ helps each
athlete understand their movement, identify areas for improvement, and
track progress against their own performance.

Product philosophy: The line judge, not the scoreboard.

SportsIQ is built around personal improvement and the freedom to play.

Overview
SportsIQ analyzes sports videos through a computer-vision pipeline:

Video upload
Pose extraction using MediaPipe
Joint-angle and movement analysis
Comparison against professional reference templates
Technique feedback, strengths, and recommendations
Personal progress tracking
The core analysis pipeline does not depend on an external LLM API.

Supported sports
Sport Current implementation

Badminton Rule-based MediaPipe analysis
Tennis Preview --- mock analysis results
Table Tennis Preview --- mock analysis results
Cricket Bowling Preview --- mock analysis results
Archery Preview --- mock analysis results

Important: Badminton analysis currently uses rule-based heuristics.
It is not a self-trained machine-learning classifier. The other sports
are not yet backed by real sport-specific analysis pipelines.

Features
Authentication
User registration and login
JWT-based authentication
Password hashing with bcrypt
Authenticated API endpoints
Video Analysis
Video upload and processing
MediaPipe pose estimation
Joint-angle computation
Professional reference-template comparison
Technique scores, strengths, and recommendations
Progress Tracking
Analysis history
Dashboard summaries
Progress tracking
Training streaks
Nutrition
Rule-based nutrition planning
Deterministic recommendations without an external LLM API
Health Data
Health data synchronization endpoints
Android Health Connect integration groundwork
Tech Stack
Backend
Python 3.11 (recommended; matches the Docker environment)
FastAPI
Pydantic v2
SQLAlchemy 2.0
JWT authentication
MediaPipe PoseLandmarker
OpenCV
NumPy
pytest
Frontend
React Native
Expo SDK 51
TypeScript
React Navigation
Database
SQLite for current local development
Production database selection is pending
Machine Learning and Computer Vision
MediaPipe PoseLandmarker
OpenCV
NumPy
Rule-based biomechanics analysis
Repository Structure
sportsIQ/
├── API_CONTRACT_final.md
├── README.md
├── backend/
│ ├── .env.example
│ ├── requirements.txt
│ ├── models/
│ │ └── pose_landmarker_full.task
│ ├── scripts/
│ │ └── analyze_badminton_video_rule_based.py
│ └── app/
│ ├── main.py
│ ├── config.py
│ ├── api/
│ │ └── routers/
│ ├── schemas/
│ ├── models/
│ ├── services/
│ ├── database/
│ ├── ml/
│ └── tests/
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
Getting Started
Prerequisites
Python 3.11 (recommended; matches the Docker environment)
Node.js and npm
Git
Expo development environment
Android device or emulator for mobile testing
Backend Setup
From the repository root:

cd backend
Create a virtual environment:

python -m venv .venv
Activate it:

.\.venv\Scripts\Activate.ps1
Install dependencies:

python -m pip install -r requirements.txt
Create your local environment file:

Copy-Item .env.example .env
Start the development server:

uvicorn app.main:app --reload
The API will be available at:

API: http://127.0.0.1:8000
Swagger UI: http://127.0.0.1:8000/docs
ReDoc: http://127.0.0.1:8000/redoc
Health check: http://127.0.0.1:8000/health
Interactive API documentation is available when DEBUG=true.

Frontend Setup
Open a separate terminal from the repository root:

cd frontend
Install dependencies:

npm install
Configure the API base URL using the frontend's environment
configuration.

For local development, the backend is available at:

http://127.0.0.1:8000
Start Expo:

npx expo start
For a physical Android device, use the development machine's LAN IP
address instead of 127.0.0.1.

API Documentation
The backend exposes REST endpoints for:

Area Description

Authentication Registration, login, and current user
Analysis Video analysis and analysis details
History Paginated analysis history
Dashboard User activity summaries
Progress Personal performance tracking
Nutrition Rule-based nutrition planning
Health Data Health data synchronization
Health Application health check

The API contract is maintained in:

`API_CONTRACT_final.md`

The contract defines the request and response shapes, enums, error
format, and integration rules.

API Contract Discipline
API_CONTRACT_final.md is the single source of truth for every request
and response.

Any change to an API boundary must follow these rules:

Update the API contract first.
Implement the corresponding backend or frontend change.
Add or update contract smoke tests.
Verify the integration before merging.
JSON conventions
All JSON keys use camelCase.

Example:

{
"analysisId": "example-id",
"sportType": "badminton",
"overallScore": 85
}
Error format
Every API error follows this structure:

{
"error": {
"code": "ERROR_CODE",
"message": "Human-readable error message"
}
}
Sport types
The current sport enum is:

badminton
tennis
table_tennis
cricket_bowling
archery
Do not introduce additional sport types without updating the API
contract.

Testing
The backend test suite is located in:

backend/app/tests/
Run the complete test suite from the repository root:

docker compose run --rm api pytest app/tests -q
Run contract smoke tests:

pytest app/tests/test_contract_smoke.py -v
The backend test suite currently contains 53 passing tests in the
reviewed codebase.

Always run the tests before pushing changes.

Docker and Deployment
SportsIQ includes Docker Compose support for running the FastAPI backend
locally.

Docker Compose
From the repository root, build the API image:

docker compose build api
Run the backend test suite inside the container:

docker compose run --rm api pytest app/tests -q
Start the API service:

docker compose up -d api
The API is exposed on port 8000:

API: http://127.0.0.1:8000
Swagger UI: http://127.0.0.1:8000/docs
Health check: http://127.0.0.1:8000/health
Stop the service:

docker compose down
The Compose configuration uses SQLite at /app/data/sportsiq.db and
mounts a named Docker volume at /app/data for database persistence.

Production Deployment Status
The project is being prepared for a publicly accessible demo. Local
Docker image building and backend tests have been verified, but
production deployment is not yet complete.

Before deploying, configure:

A production database and persistent storage

A unique SECRET_KEY with at least 32 characters

DEBUG=false

Explicit production CORS_ORIGINS values (wildcard origins are
rejected)

A publicly accessible frontend deployment

## Appropriate monitoring, security, and privacy controls

Known Limitations
SportsIQ is an actively developed project.

Current limitations include:

Real video analysis is currently implemented for badminton only.
Other sports return mock analysis results.
Badminton analysis uses rule-based heuristics rather than a trained
classifier.
The fault-detection system is not fully implemented.
Personal baseline comparison is not yet implemented.
Professional reference templates are currently hard-coded.
Analysis uses a limited contact-frame approach.
Frontend behavior and production deployment require further
verification.
These limitations are being addressed as part of the development
roadmap.

Development Roadmap
Phase 0 --- Housekeeping and Deployment Readiness

Rewrite project documentation

Add Docker support for local backend development

Improve production configuration validation

Clearly label unsupported sports
Complete production deployment and deployment verification
Phase 1 --- ML Refinement
Build a real-video evaluation dataset
Improve pose detection and contact-frame estimation
Implement fault detection
Introduce personal performance baselines
Evaluate and calibrate analysis scores
Phase 2 --- Deployment
Deploy the backend
Configure a persistent production database
Configure production environment variables
Verify API health and application behavior
Phase 3 --- UI Redesign
Refine the design system
Improve navigation and screen hierarchy
Introduce the signature analysis experience
Improve visual feedback and progress tracking
Phase 4 --- Beta and Scaling
Introduce asynchronous analysis jobs
Add rate limits and monitoring
Improve privacy and consent handling
Publish an Android demo build
Collect user feedback
Security Notes
Never commit real .env files or production secrets.

Use a unique production SECRET_KEY with at least 32 characters.

Set DEBUG=false in production.

Configure explicit production CORS_ORIGINS; wildcard origins are
rejected when DEBUG=false.

Keep authentication enabled for protected endpoints.

Do not expose user videos or personal analysis data publicly.

## Review database persistence and backup requirements before deployment.

Project
SportsIQ was developed as part of Smart India Hackathon 2026 and is
being extended into a demo-ready sports-coaching product.

The project follows the principle of personal improvement over
competitive ranking.

Your technique. Your progress. Your game.
