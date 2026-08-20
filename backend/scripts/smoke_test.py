"""
Real end-to-end smoke test. Nothing is mocked.

Exercises the exact chain the mobile app uses:

    video file
      -> HTTP multipart POST /analyze  (identical request the RN client sends)
      -> FastAPI router + guardrails
      -> MediaPipe PoseLandmarker inference
      -> technique comparison
      -> AnalysisResult JSON
      -> rendered the way the result screen renders it
      -> GET /analyze/{id} to confirm it persisted and round-trips

Usage
-----
    # against a running server (what the app actually talks to)
    uvicorn app.main:app --reload          # in another terminal
    python scripts/smoke_test.py /path/to/clip.mp4

    # in-process, no server needed
    python scripts/smoke_test.py /path/to/clip.mp4 --in-process

    # detector only, skipping the API entirely
    python scripts/smoke_test.py /path/to/clip.mp4 --detector-only

Exit code is 0 only if the whole chain succeeded.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

RULE = "=" * 68


def _section(title: str) -> None:
    print(f"\n{RULE}\n{title}\n{RULE}")


def _render_result(body: dict) -> None:
    """Print the payload the way the result screen presents it."""
    _section("RESULT (as the app renders it)")

    print(f"ACTION DETECTED   {body.get('actionLabel')}")

    quality = body.get("poseQuality")
    if quality:
        print(f"POSE QUALITY      {quality['detectionPercent']}% - {quality['band']}")
        print(f"                  ({quality['detectedFrames']}/{quality['totalFrames']} frames)")
        print(f"                  {quality['message']}")
    else:
        print("POSE QUALITY      (not reported)")

    print(f"TECHNIQUE SCORE   {body.get('overallScore')}/100")

    comparison = body.get("athleteComparison")
    if comparison:
        print(f"CLOSEST REFERENCE {comparison['referenceDisplayName']}")
        print(f"SIMILARITY        {comparison['similarity']}%")
        print(f"ESTIMATED LEVEL   {comparison['levelEstimate']}")
        print(f"BASIS             {comparison['comparisonBasis']}")
        print(f"VALIDATED DATA?   {comparison['isValidated']}  "
              "(False = hand-authored reference profile, not measured athlete data)")
        if comparison.get("allMatches"):
            print("\n  All reference profiles:")
            for match in comparison["allMatches"]:
                print(f"    {match['displayName']:22} {match['similarity']:5.1f}%  "
                      f"({match['provenance']})")

    features = body.get("featureComparison") or []
    if features:
        print(f"\n  {'FEATURE':26}{'USER':>10}{'REFERENCE':>12}{'SIM':>8}   VERDICT")
        for feature in features:
            print(f"  {feature['label']:26}{feature['userValue']:9.1f}\u00b0"
                  f"{feature['referenceValue']:11.1f}\u00b0{feature['similarity']:7.1f}%"
                  f"   {feature['verdict']}")

    if body.get("strengths"):
        print("\n  STRENGTHS")
        for item in body["strengths"]:
            print(f"    + {item}")

    if body.get("weaknesses"):
        print("\n  NEEDS WORK")
        for item in body["weaknesses"]:
            print(f"    - {item}")

    if body.get("recommendations"):
        print("\n  RECOMMENDATIONS")
        for index, item in enumerate(body["recommendations"], start=1):
            print(f"    {index}. {item}")

    print(f"\nDATA SOURCE       {body.get('dataSource')}  "
          "('measured' = real inference ran on your video)")


def run_detector_only(video: Path) -> int:
    from scripts.analyze_badminton_video_rule_based import (
        InsufficientPoseError,
        VideoError,
        analyze,
    )

    _section("DETECTOR ONLY - real MediaPipe inference")
    started = time.perf_counter()
    try:
        raw = analyze(video)
    except (VideoError, InsufficientPoseError, FileNotFoundError) as exc:
        print(f"REJECTED: {exc}")
        return 1
    elapsed = time.perf_counter() - started
    print(json.dumps(raw, indent=2))
    print(f"\nwall clock: {elapsed:.1f}s")
    return 0


def run_api(video: Path, base_url: str | None, in_process: bool) -> int:
    if in_process:
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)
        target = "in-process TestClient"

        def post(path, **kwargs):
            return client.post(path, **kwargs)

        def get(path, **kwargs):
            return client.get(path, **kwargs)
    else:
        import httpx

        target = base_url
        transport = httpx.Client(base_url=base_url, timeout=600.0)

        def post(path, **kwargs):
            return transport.post(path, **kwargs)

        def get(path, **kwargs):
            return transport.get(path, **kwargs)

    _section(f"END-TO-END via {target}")

    email = f"smoke-{uuid.uuid4().hex[:10]}@example.com"
    password = "SmokeTest123!"

    print("1. POST /auth/register")
    response = post("/auth/register", json={"email": email, "password": password})
    if response.status_code >= 400:
        print(f"   FAILED {response.status_code}: {response.text}")
        return 1
    token = response.json()["accessToken"]
    print(f"   ok ({response.status_code})")

    print("2. GET /sports")
    response = get("/sports")
    print(f"   ok ({response.status_code}) - "
          f"{[s['sportType'] for s in response.json()['sports'] if s['status'] == 'SUPPORTED']} supported")

    print(f"3. POST /analyze  <- {video.name} ({video.stat().st_size / 1_048_576:.1f} MB)")
    print("   running real MediaPipe inference, this can take a while on CPU...")
    started = time.perf_counter()
    with video.open("rb") as handle:
        response = post(
            "/analyze",
            headers={"Authorization": f"Bearer {token}"},
            files={"video": (video.name, handle, "video/mp4")},
            data={"sportType": "badminton"},
        )
    elapsed = time.perf_counter() - started
    print(f"   HTTP {response.status_code} in {elapsed:.1f}s")

    if response.status_code != 200:
        body = response.json()
        print(f"\n   REJECTED - code={body.get('error', {}).get('code')}")
        print(f"   message shown to the user: {body.get('error', {}).get('message')}")
        print("\n   This is a correct, handled failure - not a crash. The app would "
              "show this message with a Retry button.")
        return 1

    body = response.json()
    _render_result(body)

    _section("PERSISTENCE ROUND-TRIP")
    analysis_id = body["analysisId"]
    response = get(f"/analyze/{analysis_id}", headers={"Authorization": f"Bearer {token}"})
    print(f"GET /analyze/{analysis_id} -> HTTP {response.status_code}")
    if response.status_code != 200:
        print("   FAILED to read the analysis back")
        return 1
    reloaded = response.json()
    for field in ("overallScore", "actionLabel", "poseQuality", "athleteComparison",
                  "featureComparison"):
        matches = reloaded.get(field) == body.get(field)
        print(f"   {field:22} round-trips: {matches}")
        if not matches:
            return 1

    _section("SMOKE TEST PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", help="Path to a real badminton video file")
    parser.add_argument("--api", default="http://127.0.0.1:8000",
                        help="Base URL of a running backend")
    parser.add_argument("--in-process", action="store_true",
                        help="Use an in-process TestClient instead of HTTP")
    parser.add_argument("--detector-only", action="store_true",
                        help="Run only the detector, skipping the API")
    args = parser.parse_args()

    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        print(f"Video not found: {video}")
        print("Pass the path to a real clip - this script will not invent one.")
        return 2

    print(f"video: {video}")
    if args.detector_only:
        return run_detector_only(video)
    return run_api(video, args.api, args.in_process)


if __name__ == "__main__":
    raise SystemExit(main())
