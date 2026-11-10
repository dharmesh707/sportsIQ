import cv2
import math
import numpy as np
from pathlib import Path

video_path = Path(r"data\pilot\source_videos\badminton_highlights.mp4")
output_path = Path(r"data\pilot\badminton_contact_sheet.jpg")

cap = cv2.VideoCapture(str(video_path))

if not cap.isOpened():
    raise RuntimeError(f"Cannot open video: {video_path}")

fps = cap.get(cv2.CAP_PROP_FPS)
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration = frame_count / fps

interval = 1.0
timestamps = [i * interval for i in range(math.ceil(duration / interval))]

thumb_width = 320
thumb_height = 180
label_height = 30
columns = 4
rows = math.ceil(len(timestamps) / columns)

sheet = np.full(
    (rows * (thumb_height + label_height), columns * thumb_width, 3),
    255,
    dtype=np.uint8
)

for index, timestamp in enumerate(timestamps):
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    success, frame = cap.read()

    if not success:
        continue

    frame = cv2.resize(frame, (thumb_width, thumb_height))

    x = (index % columns) * thumb_width
    y = (index // columns) * (thumb_height + label_height)

    sheet[y:y + thumb_height, x:x + thumb_width] = frame

    cv2.putText(
        sheet,
        f"{timestamp:.1f}s",
        (x + 8, y + thumb_height + 21),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.6,
        (0, 0, 0),
        2
    )

cap.release()

output_path.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(output_path), sheet)

print(f"Duration: {duration:.2f}s")
print(f"Contact sheet: {output_path.resolve()}")
