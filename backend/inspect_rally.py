import cv2

video_path = r"data\pilot\source_videos\badminton_highlights.mp4"

cap = cv2.VideoCapture(video_path)

start_ms = 13000
end_ms = 28000

cap.set(cv2.CAP_PROP_POS_MSEC, start_ms)

while cap.get(cv2.CAP_PROP_POS_MSEC) < end_ms:
    ret, frame = cap.read()

    if not ret:
        break

    timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0

    cv2.putText(
        frame,
        f"{timestamp:.2f}s",
        (30, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (0, 255, 0),
        2
    )

    cv2.imshow("SPORTSIQ Rally Inspection", frame)

    # Press Q to exit. Playback is slowed to approximately 10 FPS.
    if cv2.waitKey(100) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
