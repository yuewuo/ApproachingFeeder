import json
from petlibro import PetLibroAPI
import asyncio
import arguably
import aiohttp
from functools import cached_property
import os
import logging
import sys

if "DEBUG" in os.environ:

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

if __name__ == "__main__":

    @arguably.command
    def feed(plate: int = 1):
        async def _feed(plate: int = 1):
            async with aiohttp.ClientSession() as session:
                feeder = WetFoodFeeder(session)
                await feeder.login()
                await feeder.manual_feed_now(plate)

        asyncio.run(_feed(plate=plate))

    @arguably.command
    def close():
        async def _close():
            async with aiohttp.ClientSession() as session:
                feeder = WetFoodFeeder(session)
                await feeder.login()
                await feeder.stop_feed_now()

        asyncio.run(_close())


class WetFoodFeeder:
    def __init__(self, session: aiohttp.ClientSession):

        with open("credentials.json", "r") as f:
            credentials = json.load(f)
            email = credentials["petlibro"]["email"]
            password = credentials["petlibro"]["password"]

        self.api = PetLibroAPI(
            session=session,
            time_zone="America/New_York",
            email=email,
            password=password,
            region="US",
        )

    async def login(self) -> None:
        self.devices = await self.api.list_devices()
        assert len(self.devices) > 0, "No devices found"
        self.device = find_wet_feeder(self.devices)
        assert self.device["online"], "Device is offline"
        self.deviceSn = self.device["deviceSn"]

    async def manual_feed_now(self, plate: int = 1) -> None:
        assert hasattr(self, "deviceSn"), "please call `login` first"
        await self.api.set_manual_feed_now(self.deviceSn, plate)

    async def stop_feed_now(self) -> None:
        assert hasattr(self, "deviceSn"), "please call `login` first"
        await self.api.set_stop_feed_now(self.deviceSn, 1)


def find_wet_feeder(devices: list) -> dict:
    for device in devices:
        if device["productName"] == "Polar Wet Food Feeder":
            return device
    raise RuntimeError("No wet feed found")


if __name__ == "__main__":
    arguably.run()
