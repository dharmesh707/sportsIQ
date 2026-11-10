import cv2
import numpy as np
from pathlib import Path
import math

video_path = Path(r"data\pilot\source_videos\badminton_highlights.mp4")
output_path = Path(r"data\pilot\segment_13_28_contact_sheet.jpg")

start_s = 13.0
end_s = 28.0
interval_s = 0.25

cap = cv2.VideoCapture(str(video_path))
if not cap.isOpened():
    raise RuntimeError("Could not open video")

fps = cap.get(cv2.CAP_PROP_FPS)

timestamps = np.arange(start_s, end_s, interval_s)

thumb_w = 240
thumb_h = 135
label_h = 24
columns = 5
rows = math.ceil(len(timestamps) / columns)

sheet = np.full(
    (rows * (thumb_h + label_h), columns * thumb_w, 3),
    255,
    dtype=np.uint8
)

for i, timestamp in enumerate(timestamps):
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    ok, frame = cap.read()

    if not ok:
        continue

    frame = cv2.resize(frame, (thumb_w, thumb_h))

    x = (i % columns) * thumb_w
    y = (i // columns) * (thumb_h + label_h)

    sheet[y:y + thumb_h, x:x + thumb_w] = frame

    cv2.putText(
        sheet,
        f"{timestamp:.2f}s",
        (x + 5, y + thumb_h + 17),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (0, 0, 0),
        1
    )

cap.release()

output_path.parent.mkdir(parents=True, exist_ok=True)
cv2.imwrite(str(output_path), sheet)

print(f"Saved: {output_path.resolve()}")
print(f"Frames sampled: {len(timestamps)}")
