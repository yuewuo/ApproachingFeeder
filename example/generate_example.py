import cv2
import pathlib
from cv2.typing import MatLike
import numpy as np

this_dir = pathlib.Path(__file__).parent
input_video_path = this_dir / ".." / "recordings" / "original_2025-10-05_22-27-37.mp4"
# ffmpeg -i recordings/hourly_2025-10-05_22-00-00.mp4 -frames:v 1 example/reference.jpg
reference_frame_path = this_dir / "reference.jpg"
output_video_path = this_dir / "example.mp4"

duration: float = 20
fps: float = 30

cap = cv2.VideoCapture(str(input_video_path))
reference: MatLike = cv2.imread(reference_frame_path, cv2.IMREAD_COLOR)

fourcc: int = cv2.VideoWriter.fourcc(*"avc1")
writer = cv2.VideoWriter(
    str(output_video_path),
    fourcc=fourcc,
    fps=fps,
    frameSize=(reference.shape[1], reference.shape[0]),
)


def gray_frame_of(frame) -> MatLike:
    gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)
    return gray_frame


def is_different(
    frame1: MatLike,
    frame2: MatLike,
    *,
    frame_to_draw: MatLike | None = None,
    # the number 0.015 is calculated based on the size of the plate (~0.011)
    threshold_ratio: float = 0.015,
) -> bool:
    frame_diff = cv2.absdiff(frame1, frame2)
    thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
    thresh = cv2.dilate(thresh, kernel=np.ones((3, 3), np.uint8), iterations=2)

    contours, _ = cv2.findContours(
        thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    is_motion_detected = False
    threshold_area = threshold_ratio * frame1.shape[0] * frame1.shape[1]
    for contour in contours:
        if cv2.contourArea(contour) < threshold_area:
            continue
        (x, y, w, h) = cv2.boundingRect(contour)
        is_motion_detected = True
        if frame_to_draw is not None:
            cv2.rectangle(frame_to_draw, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return is_motion_detected


gray_reference = gray_frame_of(reference)


elapsed: float = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    gray_frame = gray_frame_of(frame)
    is_different(gray_reference, gray_frame, frame_to_draw=frame)

    writer.write(frame)

    # breaking
    elapsed += 1 / fps
    if elapsed > duration:
        break

cap.release()
writer.release()
cv2.destroyAllWindows()
