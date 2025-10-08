import pathlib
import os
import sys
from dataclasses import dataclass
import logging
from logging import getLogger
from datetime import datetime, timedelta
import arguably
import requests
import json
import cv2
from cv2.typing import MatLike


if "DEBUG" in os.environ:

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


_LOGGER = getLogger(__name__)


this_dir = pathlib.Path(__file__).parent


def main():

    auto_torch = AutoTorch()

    @arguably.command
    def on():
        auto_torch.set(True)

    @arguably.command
    def off():
        auto_torch.set(False)

    arguably.run()


@dataclass
class AutoTorch:

    # to avoid flashing at night, we will take action only if the last action was
    # at least an hour ago
    def __init__(
        self,
        ip_port: str = "192.168.0.91:8080",
        on_threshold: float = 60,
        off_threshold: float = 120,
        stable_for: float = 3600,
    ):
        self.stable_for = stable_for
        self.on_threshold = on_threshold
        self.off_threshold = off_threshold

        with open(this_dir / "credentials.json", "r") as f:
            credentials = json.load(f)
            username = credentials["webcam"]["username"]
            password = credentials["webcam"]["password"]

        self.base_url = f"{username}:{password}@{ip_port}"
        self.auth = (username, password)
        self.last_action: datetime | None = None
        self.current_on: bool | None = None

    def set(self, on: bool) -> None:
        # use the flash light of the phone to light up the region at night
        url = f"http://{self.base_url}/" + ("enabletorch" if on else "disabletorch")
        _LOGGER.error(
            "AutoTorch turned "
            + ("on" if on else "off")
            + " at "
            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        self.current_on = on
        self.last_action = datetime.now()
        requests.get(url, auth=self.auth)

    def run(self, frame: MatLike) -> None:
        if (
            self.last_action is not None
            and datetime.now() - self.last_action < timedelta(seconds=self.stable_for)
        ):
            return  # do nothing

        hsv_image = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        _, _, v_channel = cv2.split(hsv_image)
        brightness = v_channel.mean()
        if brightness < self.on_threshold and not self.current_on:
            self.set(True)
        elif brightness > self.off_threshold and self.current_on:
            self.set(False)


if __name__ == "__main__":
    main()
