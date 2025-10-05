import cv2
import json
import pathlib
import requests

this_dir = pathlib.Path(__file__).parent


def main():
    detector = MotionDetector()
    detector.wait_until_motion_detected()

    # while cap.isOpened():
    #     ret, frame = cap.read()

    #     gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    #     cv2.imshow("frame", gray)
    #     if cv2.waitKey(1) & 0xFF == ord("q"):
    #         break

    # cap.release()
    # cv2.destroyAllWindows()


class MotionDetector:
    def __init__(
        self, ip_port: str = "192.168.0.91:8080", height: int = 1080, width: int = 1920
    ):

        with open(this_dir / "credentials.json", "r") as f:
            credentials = json.load(f)
            username = credentials["webcam"]["username"]
            password = credentials["webcam"]["password"]

        self.base_url = f"{username}:{password}@{ip_port}"

        # update video size to reduce bandwidth requirements
        print(
            f"http://{self.base_url}/settings/video_size",
        )
        size_url = f"http://{self.base_url}/settings/video_size?set={width}x{height}"
        requests.get(size_url, auth=(username, password))

        self.url = f"rtsp://{self.base_url}/h264_ulaw.sdp"

    def wait_until_motion_detected(self) -> None:

        capture = cv2.VideoCapture(self.url)
        # Capture initial background frame
        ret, background_frame = capture.read()
        last_background = cv2.cvtColor(background_frame, cv2.COLOR_BGR2GRAY)
        last_background = cv2.GaussianBlur(last_background, (21, 21), 0)

        recording_active = False

        while True:
            ret, frame = capture.read()
            if not ret:
                raise RuntimeError("Failed to read frame from camera")

            gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_frame = cv2.GaussianBlur(gray_frame, (21, 21), 0)

            frame_diff = cv2.absdiff(last_background, gray_frame)
            thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)

            contours, _ = cv2.findContours(
                thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            motion_detected_in_frame = False
            for contour in contours:
                if cv2.contourArea(contour) < 0.002 * frame.shape[0] * frame.shape[1]:
                    continue
                (x, y, w, h) = cv2.boundingRect(contour)
                motion_detected_in_frame = True
                print("Motion detected")
                # ... (Draw rectangles around motion)
                cv2.rectangle(gray_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            if motion_detected_in_frame and not recording_active:
                recording_active = True
                # ... (Start recording timer)
            elif not motion_detected_in_frame and recording_active:
                # ... (Check if recording duration elapsed, then stop recording)
                pass

            # cv2.imshow("frame", gray_frame)
            cv2.imshow("frame", frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

            last_background = gray_frame


if __name__ == "__main__":
    main()
