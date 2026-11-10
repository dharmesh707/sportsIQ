# SportsIQ Evidence Report

Date: 2026-11-09

## Step 0 - Environment

Initial environment command output:

```text
Python 3.11.8

mediapipe                                1.0.1
numpy                                    2.2.6
onnxruntime                              1.24.3
opencv-python                            5.0.0.93
torch                                    2.2.2
11th Gen Intel(R) Core(TM) i3-1115G4 @ 3.00GHz

TotalPhysicalMemory : 16859734016

nvidia-smi : The term 'nvidia-smi' is not recognized as the name of a cmdlet, function, script file, or operable program.
Check the spelling of the name, or if a path was included, verify that the path is correct and try again.
At line:2 char:282
+ ... omputerSystem | Select-Object TotalPhysicalMemory; nvidia-smi; Get-Ci ...
+                                                        ~~~~~~~~~~
    + CategoryInfo          : ObjectNotFound: (:) [], CommandNotFoundException
    + FullyQualifiedErrorId : CommandNotFoundException
```

OS command output:

```text
Caption                                   Version    BuildNumber
-------                                   -------    -----------
Microsoft Windows 11 Home Single Language 10.0.26200 26200
```

`nvidia-smi` was not available. NVIDIA GPU status: not detected by
`nvidia-smi`.

After the requested installation in Step 5, package distribution versions
were:

```text
mediapipe==1.0.1
opencv-python==5.0.0.93
numpy==2.2.6
onnxruntime==1.24.3
ultralytics==8.4.208
rtmlib==0.0.16
torch==2.15.0
torchvision==0.29.2
```

## Step 1 - Repository state

Command:

```powershell
cd backend
python -m pytest -q -rs
```

Final output:

```text
116 passed, 1 skipped in 65.77s (0:01:05)
```

Skip output:

```text
SKIPPED [1] app\tests\test_manifest_validator.py:404: Symlinks are unavailable in this test environment
```

`git status --short`:

```text
M backend/app/ml/pose/__init__.py
?? backend/data/benchmark/
```

`git log --oneline -3`:

```text
acad19e Snapshot before 3-day SportsIQ delivery
41c8ecb chore: complete backend configuration and database migration
e810e14 Add Docker Compose with persistent SQLite storage
```

## Step 2 - Benchmark files

The requested files do not exist:

```text
Get-Item : Cannot find path 'C:\Users\dharm\Downloads\SPORTSIQ\backend\scripts\pose_benchmark.py' because it does not exist.
Get-Item : Cannot find path 'C:\Users\dharm\Downloads\SPORTSIQ\backend\app\tests\test_pose_benchmark.py' because it does not exist.
```

The requested test command was run:

```text
C:\Program Files\Python311\python.exe: No module named scripts.pose_benchmark
```

Result: no tests ran; the requested benchmark utility and test are absent.

## Step 3 - Video inventory

The inventory searched all repository subdirectories and the specified user
directories non-recursively plus one level of subdirectories. The following
video files were found. No `.mov`, `.avi`, or `.webm` files were found in
those search locations.

| Path | Size MB | Resolution | FPS | Frames | Duration seconds |
|---|---:|---:|---:|---:|---:|
| `C:\Users\dharm\Downloads\demo video-1.mp4` | 144.641 | 1918x1078 | 30.0 | 4130 | 137.66666666666666 |
| `C:\Users\dharm\Downloads\demo_ps 2.mp4` | 131.485 | 1920x1076 | 30.0 | 3760 | 125.33333333333333 |
| `C:\Users\dharm\Downloads\Recording 2026-09-30 143118.mp4` | 120.868 | 1918x1078 | 30.0 | 3456 | 115.2 |
| `C:\Users\dharm\Downloads\SkyGUARD demoV.mp4` | 18.118 | 1920x1080 | 30.0 | 4123 | 137.43333333333334 |
| `C:\Users\dharm\Downloads\SPORTSIQ\backend\data\validation\f0724262-de53-46ba-88dc-3fed18758ee1.mp4` | 2.837 | 608x1080 | 25.99998183090019 | 159 | 6.115388888888888 |
| `C:\Users\dharm\Downloads\Untitled - September 29, 2026 at 10.30.03.mp4` | 20.659 | 1280x720 | 30.0 | 3936 | 131.2 |
| `C:\Users\dharm\Videos\2026-02-18 12-54-21.mp4` | 23.641 | 1280x720 | 30.0 | 968 | 32.266666666666666 |
| `C:\Users\dharm\Videos\Screen Recordings\Screen Recording 2025-02-23 151535.mp4` | 39.888 | 1920x1076 | 30.0 | 1161 | 38.7 |
| `C:\Users\dharm\Videos\Screen Recordings\Screen Recording 2025-03-05 224536.mp4` | 81.934 | 1920x1078 | 30.0 | 2305 | 76.83333333333333 |
| `C:\Users\dharm\Videos\Screen Recordings\Screen Recording 2025-03-11 174819.mp4` | 390.264 | 1920x1078 | 30.0 | 11082 | 369.4 |
| `C:\Users\dharm\Videos\Screen Recordings\Screen Recording 2026-03-21 223556.mp4` | 242.484 | 1920x1080 | 30.0 | 6884 | 229.46666666666666 |

All listed files were only inspected with `cv2.VideoCapture`; no files
outside the repository were opened for copying or modification.

## Step 4 - MediaPipe-only benchmark

Command:

```powershell
python -m scripts.pose_benchmark data\validation\f0724262-de53-46ba-88dc-3fed18758ee1.mp4 --backends mediapipe --presence-review data\pilot\manifests\presence_review.csv --out-dir data\benchmark --overlay
```

Exact output:

```text
C:\Program Files\Python311\python.exe: No module named scripts.pose_benchmark
```

Full JSON: NOT RUN; the benchmark module is absent.

## Step 5 - YOLO and RTMPose installation and benchmark

The requested installation command completed successfully:

```powershell
pip install ultralytics rtmlib onnxruntime
```

Relevant exact installation output:

```text
Downloading torch-2.15.0-cp311-cp311-win_amd64.whl (126.7 MB)
...
Attempting uninstall: torch
Found existing installation: torch 2.2.2
Uninstalling torch-2.2.2:
Successfully uninstalled torch-2.2.2
...
ERROR: pip's dependency resolver does not currently take into account all the packages that are installed. This behaviour is the source of the following dependency conflicts.
crawl4ai 0.8.6 requires pydantic>=2.10, but you have pydantic 2.9.2 which is incompatible.
storage3 2.28.0 requires pydantic>=2.11.7, but you have pydantic 2.9.2 which is incompatible.
Successfully installed httpx-0.28.1 nvidia-ml-py-13.615.71 polars-2.1.0 polars-runtime-32-2.1.0 rtmlib-0.0.16 setuptools-84.2.1 torch-2.15.0 torchvision-0.29.2 ultralytics-8.4.208 ultralytics-platform-0.1.107 ultralytics-thop-2.2.5
```

The output showed a 126.7 MB Windows Torch wheel. It did not show a CUDA
Torch wheel or CUDA package installation.

All three requested benchmark commands failed before execution because the
benchmark module is absent.

Combined backends:

```text
C:\Program Files\Python311\python.exe: No module named scripts.pose_benchmark
```

MediaPipe plus YOLO:

```text
C:\Program Files\Python311\python.exe: No module named scripts.pose_benchmark
```

MediaPipe plus RTMPose:

```text
C:\Program Files\Python311\python.exe: No module named scripts.pose_benchmark
```

RTMPose API signature: NOT RUN; RTMPose did not reach import/use through the
missing benchmark module, so no RTMPose API error occurred.

Overlay files: none created. `data\benchmark` contained only:

```text
Name                  Length LastWriteTime
----                  ------ -------------
api_server_stderr.txt      0 09-11-2026 00:52:44
api_server_stdout.txt      0 09-11-2026 00:52:44
```

`ms_per_frame_median`: NOT AVAILABLE for all backends.

## Step 6 - Live API

The server was started with an isolated SQLite database at
`backend\data\benchmark\api_evidence.db`, so the existing database was not
used for registration or analysis. The server process was stopped afterward.

The registration/login/upload command stopped at the multipart upload because
the available Windows PowerShell `Invoke-RestMethod` does not support the
requested `-Form` parameter.

Exact error:

```text
Invoke-RestMethod : A parameter cannot be found that matches parameter name 'Form'.
At line:2 char:1618
+ ... Headers @{Authorization='Bearer ' + $login.accessToken} -Form $form;  ...
+                                                             ~~~~~
    + CategoryInfo          : InvalidArgument: (:) [], ParameterBindingException
    + FullyQualifiedErrorId : NamedParameterNotFound,Microsoft.PowerShell.Commands.InvokeRestMethod
```

Full `/analyze` JSON: NOT RUN.

Request duration: NOT RUN; the multipart request was not sent.

## Step 7 - Frontend

`frontend\package.json` scripts:

```json
"scripts": {
  "start": "expo start",
  "android": "expo run:android",
  "ios": "expo run:ios",
  "dev-client": "expo start --dev-client"
}
```

`frontend\node_modules` exists: `True`.

[`frontend\src\api\client.ts`](C:/Users/dharm/Downloads/SPORTSIQ/frontend/src/api/client.ts)
configures the API base URL as:

```text
process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000"
```

The Expo command used was:

```powershell
npx expo start --offline
```

Exact relevant output:

```text
node_modules:
True
expo version:
0.18.31
offline start:
Networking has been disabled
Starting project at C:\Users\dharm\Downloads\SPORTSIQ\frontend
env: load .env
env: export EXPO_PUBLIC_API_BASE_URL
Starting Metro Bundler
Waiting on http://localhost:8081
Logs for your project will appear below.
```

The Metro process was stopped after readiness was observed.

The Analyze screen source shows a badminton default, video-library picker,
video preview, `Run analysis` button, uploading state, error state, and
analysis result rendering. The same video was not uploaded through the
frontend during this run; therefore the post-upload screen result and
screenshot path are NOT RUN.

## Questions

- Which hand do I use to hold the racket? ____

- Where is the camera for my own clips (side/behind/front, height, distance)? ____

- What is the target demo scenario for the app (e.g. record a smash, upload, see feedback)? ____

- Are there other reference videos (pro players) I already have the right to use? ____

## Final status

### Succeeded

- Environment version and hardware inspection.
- Backend test suite: `116 passed, 1 skipped`.
- Skip reason captured: symlinks unavailable.
- Repository status and latest three commits captured.
- Video inventory completed.
- Requested dependency installation completed.
- All requested benchmark commands were attempted.
- Frontend package/configuration inspection completed.
- Expo offline Metro startup reached `http://localhost:8081`.
- API server startup and cleanup completed using an isolated database.

### Failed or not completed

- Step 2: benchmark utility and test file absent. First error:
  `Cannot find path ... backend\scripts\pose_benchmark.py`.
- Step 4: `No module named scripts.pose_benchmark`.
- Step 5 benchmark runs: `No module named scripts.pose_benchmark`.
- Step 6: `Invoke-RestMethod ... A parameter cannot be found that matches parameter name 'Form'.`
- Step 6 full analysis response and request duration were not obtained.
- Step 7 post-upload Analyze result was not obtained.

### Surprising observations

- The requested benchmark files are not present despite the repository state
  containing an unrelated modified `backend/app/ml/pose/__init__.py`.
- The dependency installation upgraded Torch from `2.2.2` to `2.15.0` and
  installed `torchvision 0.29.2`.
- The dependency installation reported existing `pydantic` conflicts for
  `crawl4ai` and `storage3`.
- `nvidia-smi` was unavailable.
- The validation video opened successfully and contains 159 frames at
  608x1080 and approximately 26 FPS.
