
import csv
import cv2
from datetime import datetime
from pathlib import Path

# ------------------------------------------------------------
# Paths and configuration
# ------------------------------------------------------------
BACKEND_DIR = Path(__file__).resolve().parents[1]
VIDEO_PATH = (
    BACKEND_DIR
    / "data"
    / "pilot"
    / "source_videos"
    / "badminton_highlights.mp4"
)
CSV_PATH = (
    BACKEND_DIR
    / "data"
    / "pilot"
    / "manifests"
    / "stroke_annotations_pilot.csv"
)

CSV_FIELDS = [
    "annotation_id",
    "video_path",
    "stroke_label",
    "start_ms",
    "end_ms",
    "annotation_status",
    "reviewer_id",
]

STROKE_LABEL = "smash"
MIN_INTERVAL_MS = 250
SEEK_SECONDS = 0.25


def ensure_csv():
    """Create the annotation CSV with a header if it does not exist."""
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not CSV_PATH.exists() or CSV_PATH.stat().st_size == 0:
        with CSV_PATH.open("w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
            writer.writeheader()


def append_annotation(start_ms, end_ms):
    """Append one valid annotation and return its ID."""
    annotation_id = datetime.now().strftime("smash_%Y%m%d_%H%M%S_%f")

    row = {
        "annotation_id": annotation_id,
        "video_path": str(VIDEO_PATH.relative_to(BACKEND_DIR)).replace(
            "\\", "/"
        ),
        "stroke_label": STROKE_LABEL,
        "start_ms": start_ms,
        "end_ms": end_ms,
        "annotation_status": "pending_review",
        "reviewer_id": "",
    }

    with CSV_PATH.open("a", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writerow(row)

    return annotation_id


def undo_last_annotation(annotation_id):
    """Remove the most recently saved annotation from this session."""
    if not annotation_id or not CSV_PATH.exists():
        return False

    with CSV_PATH.open("r", newline="", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    filtered_rows = [
        row
        for row in rows
        if row.get("annotation_id") != annotation_id
    ]

    if len(filtered_rows) == len(rows):
        return False

    with CSV_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(filtered_rows)

    return True


def main():
    ensure_csv()

    if not VIDEO_PATH.exists():
        print(f"ERROR: Video not found:\n{VIDEO_PATH}")
        return

    cap = cv2.VideoCapture(str(VIDEO_PATH))

    if not cap.isOpened():
        print("ERROR: OpenCV could not open the video.")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if fps <= 0 or total_frames <= 0:
        print("ERROR: Could not read video FPS or frame count.")
        cap.release()
        return

    duration_seconds = total_frames / fps

    frame_index = 0
    paused = True
    playback_speed = 1.0
    start_frame = None
    last_annotation_id = None

    print("\n========== SPORTSIQ STROKE ANNOTATOR ==========")
    print(f"Video: {VIDEO_PATH.name}")
    print(f"FPS: {fps:.3f}")
    print(f"Frames: {total_frames}")
    print(f"Duration: {duration_seconds:.2f} seconds")
    print(f"Output CSV: {CSV_PATH}")

    print("\nControls:")
    print("  SPACE : Play / pause")
    print("  1/2/4 : Playback speed 1x / 2x / 4x")
    print("  S     : Mark stroke START")
    print("  E     : Mark stroke END and save")
    print("  J     : Seek backward 0.25 seconds")
    print("  L     : Seek forward 0.25 seconds")
    print("  R     : Clear current start marker")
    print("  U     : Undo last saved annotation in this session")
    print("  Q/ESC : Quit")
    print("===============================================\n")

    window_name = "SPORTSIQ Stroke Annotator"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    while True:
        frame_index = max(0, min(frame_index, total_frames - 1))

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, frame = cap.read()

        if not success:
            print("Could not read frame. Exiting.")
            break

        current_ms = int((frame_index / fps) * 1000)

        # Draw annotation status on the frame.
        status_lines = [
            f"Frame: {frame_index}/{total_frames - 1}",
            f"Time: {current_ms / 1000:.2f}s",
            f"Mode: {'PAUSED' if paused else 'PLAYING'} | Speed: {playback_speed}x",
            f"Stroke: {STROKE_LABEL}",
            f"Start: {'NOT SET' if start_frame is None else f'{start_frame / fps:.2f}s'}",
            "SPACE Play/Pause | 1/2/4 Speed | S Start | E End+Save",
            "J/L Seek | R Clear | U Undo | Q Quit",
        ]

        if start_frame is not None:
            status_lines.append("Annotation in progress")

        y = 30

        for line in status_lines:
            cv2.putText(
                frame,
                line,
                (15, y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )
            y += 28

        cv2.imshow(window_name, frame)

        # waitKeyEx preserves extended key codes.
        wait_ms = (
            0
            if paused
            else max(1, int(1000 / (fps * playback_speed)))
        )

        key = cv2.waitKeyEx(wait_ms)
        key_low = key & 0xFF

        if key_low in (ord("q"), 27):
            break

        elif key_low == ord(" "):
            paused = not paused

        elif key_low == ord("1"):
            playback_speed = 1.0
            print("Playback speed: 1x")

        elif key_low == ord("2"):
            playback_speed = 2.0
            print("Playback speed: 2x")

        elif key_low == ord("4"):
            playback_speed = 4.0
            print("Playback speed: 4x")

        elif key_low == ord("s"):
            start_frame = frame_index
            print(
                f"START marked at {current_ms} ms "
                f"({current_ms / 1000:.2f}s)"
            )

        elif key_low == ord("e"):
            if start_frame is None:
                print("Cannot save: mark the START first using S.")
                continue

            if frame_index <= start_frame:
                print("Cannot save: END must be after START.")
                continue

            start_ms = int((start_frame / fps) * 1000)
            end_ms = int((frame_index / fps) * 1000)
            interval_ms = end_ms - start_ms

            if interval_ms < MIN_INTERVAL_MS:
                print(
                    f"Interval too short ({interval_ms} ms). "
                    f"Choose at least {MIN_INTERVAL_MS} ms."
                )
                continue

            annotation_id = append_annotation(start_ms, end_ms)
            last_annotation_id = annotation_id

            print(
                f"SAVED: {annotation_id} | "
                f"{start_ms}–{end_ms} ms | "
                f"{interval_ms} ms | label={STROKE_LABEL}"
            )

            start_frame = None

        elif key_low == ord("r"):
            start_frame = None
            print("Current start marker cleared.")

        elif key_low == ord("u"):
            if undo_last_annotation(last_annotation_id):
                print(f"Undid annotation: {last_annotation_id}")
                last_annotation_id = None
            else:
                print("No annotation from this session to undo.")

        elif key_low == ord("j"):
            frame_index -= max(1, int(SEEK_SECONDS * fps))
            paused = True

        elif key_low == ord("l"):
            frame_index += max(1, int(SEEK_SECONDS * fps))
            paused = True

        # Common Windows OpenCV extended arrow-key codes.
        elif key in (2424832, 65361):
            frame_index -= 1
            paused = True

        elif key in (2555904, 65363):
            frame_index += 1
            paused = True

        # Advance automatically when playing.
        if not paused:
            frame_index += 1

        if frame_index >= total_frames:
            frame_index = total_frames - 1
            paused = True

    cap.release()
    cv2.destroyAllWindows()

    print("\nAnnotation session closed.")


if __name__ == "__main__":
    main()
