from app.ml.pose.full_body_sequence import extract_full_body_pose_sequence

VIDEO_PATH = r"data\pilot\source_videos\badminton_highlights.mp4"
VISIBILITY_THRESHOLD = 0.5

sequence = extract_full_body_pose_sequence(VIDEO_PATH)

total_frames = len(sequence.frames)
player_present_frames = 0
reliable_pose_frames = 0
visibility_values = []

required_landmarks = [
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle",
]

for frame in sequence.frames:
    if frame.player_presence == "PLAYER_PRESENT":
        player_present_frames += 1

    reliable_count = 0

    for name in required_landmarks:
        keypoint = frame.keypoints.get(name)

        if keypoint is None or not keypoint.present:
            continue

        visibility = keypoint.visibility

        if visibility is None:
            continue

        visibility_values.append(visibility)

        if visibility >= VISIBILITY_THRESHOLD:
            reliable_count += 1

    # At least 7 of 10 major landmarks must be reliable.
    if reliable_count >= 7:
        reliable_pose_frames += 1

print("\n--- Pose Quality Summary ---")
print(f"Total frames: {total_frames}")
print(
    f"Player present: {player_present_frames} "
    f"({player_present_frames / total_frames * 100:.2f}%)"
)
print(
    f"Reliable pose frames: {reliable_pose_frames} "
    f"({reliable_pose_frames / total_frames * 100:.2f}%)"
)

if visibility_values:
    print(
        f"Mean landmark visibility: "
        f"{sum(visibility_values) / len(visibility_values):.4f}"
    )
