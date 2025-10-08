import cv2
import os
import pathlib

"""
conclusion: night: 50-, day: 125+, torch on at night: ~108

night-example.mp4 max: 50.90150462962963, min: 45.890763406635806, mean: 49.478055599396754
day-example.mp4 max: 165.1203448109568, min: 125.2001634837963, mean: 136.1318621870344
torch-example2.mp4 max: 108.16965663580247, min: 42.22174238040123, mean: 66.93585223644868
"""

this_dir = pathlib.Path(__file__).parent

for input_video_path in [
    this_dir / ".." / "recordings" / "night-example.mp4",
    this_dir / ".." / "recordings" / "day-example.mp4",
    this_dir / ".." / "recordings" / "torch-example2.mp4",
]:

    cap = cv2.VideoCapture(str(input_video_path))

    def brightness_of(frame) -> float:
        hsv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        _, _, v_channel = cv2.split(hsv_image)
        return v_channel.mean()

    brightnesses: list[float] = []

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        brightness = brightness_of(frame)
        brightnesses.append(brightness)

    print(
        os.path.basename(input_video_path),
        f"max: {max(brightnesses)}, min: {min(brightnesses)}, mean: {sum(brightnesses) / len(brightnesses)}",
    )

    cap.release()
    cv2.destroyAllWindows()
