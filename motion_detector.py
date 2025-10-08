import cv2
import json
import os
import pathlib
import requests
from datetime import datetime, timedelta
from threading import Thread
import time
from logging import getLogger
from cv2.typing import MatLike
import numpy as np
import logging
import sys

if "DEBUG" in os.environ:

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


_LOGGER = getLogger(__name__)

this_dir = pathlib.Path(__file__).parent


def main():
    with MotionDetector() as detector:
        while True:
            time.sleep(1)


class MotionDetector:
    """
    motion is detected per 1 second interval (and it is recorded with one file per hour)
    "motion", in this scenario, is defined as the difference from the reference frame (where the cat is not there)
    since the lighting condition changes throughput the day, the reference frame is updated every 1 second
    - it takes 10 previous frames calculates the average of them
    - if motion is detected, the reference frame is not updated until the motion is gone
        - in case the motion is not gone for more than 20 minutes (which is very unlikely), we will force quite the motion
            detected state and update the reference frame accordingly
        - during the motion-detected state, we record videos at the original resolution and frame rate
    """

    def __init__(
        self,
        ip_port: str = "192.168.0.91:8080",
        height: int = 1080,
        width: int = 1920,
        interval: float = 1,  # the event of detection
    ):

        with open(this_dir / "credentials.json", "r") as f:
            credentials = json.load(f)
            username = credentials["webcam"]["username"]
            password = credentials["webcam"]["password"]

        self.base_url = f"{username}:{password}@{ip_port}"

        # update video size to reduce bandwidth requirements
        size_url = f"http://{self.base_url}/settings/video_size?set={width}x{height}"
        requests.get(size_url, auth=(username, password))

        self.capture_url = f"rtsp://{self.base_url}/h264_ulaw.sdp"
        self.capture = cv2.VideoCapture(self.capture_url)
        # self.fps = self.capture.get(cv2.CAP_PROP_FPS)
        self.fps = 30.0  # hardcode it to 30 fps (there is a bug, see below)
        # https://stackoverflow.com/questions/58583810/opencv-4-1-1-26-reports-90000-0-fps-for-a-25fps-rtsp-stream
        self.width = int(self.capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame: MatLike | None = None
        _LOGGER.debug(f"FPS: {self.fps}, Width: {self.width}, Height: {self.height}")
        assert self.fps > 0 and self.fps <= 120, "FPS is not correct"
        assert self.height == height, "Height is not updated"
        assert self.width == width, "Width is not updated"

        self.is_motion_detected = False
        self.writer_hourly: cv2.VideoWriter | None = None
        self.writer_original: cv2.VideoWriter | None = None

    def __enter__(self) -> "MotionDetector":
        self.thread = Thread(target=self._thread_function)
        self.thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if self.writer_original is not None:
            self.writer_original.release()
        if self.writer_hourly is not None:
            self.writer_hourly.release()

    def _thread_function(self) -> None:
        reference_window: list[tuple[float, MatLike]] = []

        last_failed: bool = False
        last_time = time.time()
        now = datetime.now()
        hourly_start = now.hour
        self.writer_hourly = self.create_video_writer(
            this_dir / "recordings" / f"hourly_{self.now_mp4()}",
            fps=1,
        )
        motion_start_time: datetime | None = None
        # if motion is detected but the frame is stable for more than 30 seconds,
        # we will consider the motion is not real and soft reboot it quickly
        last_grey: MatLike | None = None
        count_stable_frames: int = 0
        while True:
            ret, frame = self.capture.read()
            if not ret:
                if not last_failed:
                    _LOGGER.error(
                        "Failed to read frame from camera since "
                        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                last_failed = True
                time.sleep(1)  # try again in 1 second
                if time.time() - last_time > 60:
                    last_time = time.time()
                    # if it does not recover after 1min, we will reinitialize the capture stream
                    self.capture.release()
                    self.capture = cv2.VideoCapture(self.capture_url)
                    _LOGGER.error(
                        "Reconnecting the video stream at "
                        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                continue
            else:
                if last_failed:
                    _LOGGER.error(
                        "Successfully recover reading frame from camera since "
                        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
            last_failed = False

            # do the work that is done in every frame (30fps)
            if self.writer_original is not None:
                self.writer_original.write(frame)
            self.frame = frame

            # we will drop frame unless the previous one was taken at least 1 seconds ago
            if time.time() - last_time < 1:
                continue

            # do the work that is done in every 1 second
            last_time = time.time()
            now = datetime.now()
            if now.hour != hourly_start and self.writer_hourly is not None:
                self.writer_hourly.release()
                hourly_start = now.hour
                self.writer_hourly = self.create_video_writer(
                    this_dir / "recordings" / f"hourly_{self.now_mp4()}",
                    fps=1,
                )

            gray_frame = self.gray_frame_of(frame)

            if len(reference_window) < 10:
                if self.writer_hourly is not None:
                    self.writer_hourly.write(frame)
                reference_window.append((time.time(), gray_frame))
                continue  # need to accumulate more frames before we start to do some processing
            while len(reference_window) > 10:
                reference_window.pop(0)  # remove the oldest frame

            # calculate the average of the reference window
            height, width = gray_frame.shape
            average_reference = np.zeros((height, width), dtype=np.float32)
            # excluding the current frame because it might contain motion
            for history_gray_frame in reference_window:
                average_reference += history_gray_frame[1].astype(np.float32)
            average_reference /= len(reference_window)
            gray_reference = average_reference.astype(np.uint8)

            is_motion_detected = self.is_different(
                gray_reference, gray_frame, frame_to_draw=frame
            )
            if is_motion_detected and not self.is_motion_detected:
                motion_start_time = datetime.now()
                _LOGGER.debug(
                    "Motion started at "
                    + motion_start_time.strftime("%Y-%m-%d %H:%M:%S")
                )
                self.start_recording_original()
                count_stable_frames = 0
            elif not is_motion_detected and self.is_motion_detected:
                motion_start_time = None
                _LOGGER.debug(
                    "Motion ended at " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                self.stop_recording_original()
                count_stable_frames = 0
            self.is_motion_detected = is_motion_detected

            if not self.is_motion_detected:
                reference_window.append((time.time(), gray_frame))

            if last_grey is not None and is_motion_detected:
                if self.is_different(last_grey, gray_frame, threshold_ratio=0.001):
                    count_stable_frames = 0
                else:
                    count_stable_frames += 1
                if count_stable_frames > 30:
                    _LOGGER.debug(
                        "Stable frames cause motion soft reboot at "
                        + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    )
                    count_stable_frames = 0
                    motion_start_time = None
                    self.is_motion_detected = False
                    self.stop_recording_original()
                    reference_window.clear()  # soft reboot

            last_grey = gray_frame

            if (
                motion_start_time is not None
                and datetime.now() - motion_start_time > timedelta(minutes=20)
            ):
                _LOGGER.debug(
                    "Motion soft reboot at "
                    + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
                motion_start_time = None
                self.is_motion_detected = False
                self.stop_recording_original()
                reference_window.clear()  # soft reboot

            if self.writer_hourly is not None:
                self.writer_hourly.write(frame)

    def is_different(
        self,
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

    def start_recording_original(self) -> None:
        if self.writer_original is not None:
            return
        self.writer_original = self.create_video_writer(
            this_dir / "recordings" / f"original_{self.now_mp4()}"
        )

    def create_video_writer(
        self, filename: pathlib.Path, fps: float | None = None
    ) -> cv2.VideoWriter:
        fourcc: int = cv2.VideoWriter.fourcc(*"avc1")
        return cv2.VideoWriter(
            str(filename),
            fourcc=fourcc,
            fps=fps or self.fps,
            frameSize=(self.width, self.height),
        )

    def stop_recording_original(self) -> None:
        if self.writer_original is None:
            return
        self.writer_original.release()
        self.writer_original = None

    def now_mp4(self) -> str:
        return datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".mp4"

    def gray_frame_of(self, frame) -> MatLike:
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)
        return gray_frame


if __name__ == "__main__":
    main()
