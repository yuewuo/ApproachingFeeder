import json
from petlibro import PetLibroAPI
import asyncio
import aiohttp
from functools import cached_property


async def main():
    # await test_login()
    # await test_feed_now(plate=2)
    await test_stop_feed_now()


async def test_login():
    async with aiohttp.ClientSession() as session:
        feeder = WetFoodFeeder(session)
        print(await feeder.deviceSn)


async def test_feed_now(plate: int = 1):
    async with aiohttp.ClientSession() as session:
        feeder = WetFoodFeeder(session)
        await feeder.manual_feed_now(plate)


async def test_stop_feed_now():
    async with aiohttp.ClientSession() as session:
        feeder = WetFoodFeeder(session)
        await feeder.stop_feed_now()


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

    @cached_property
    async def devices(self) -> list:
        devices = await self.api.list_devices()
        assert len(devices) > 0, "No devices found"
        return devices

    @cached_property
    async def device(self) -> dict:
        device = find_wet_feeder(await self.devices)
        assert device["online"], "Device is offline"
        return device

    @cached_property
    async def deviceSn(self) -> str:
        return (await self.device)["deviceSn"]

    async def manual_feed_now(self, plate: int = 1) -> None:
        deviceSn = await self.deviceSn
        await self.api.set_manual_feed_now(deviceSn, plate)

    async def stop_feed_now(self) -> None:
        deviceSn = await self.deviceSn
        await self.api.set_stop_feed_now(deviceSn, 1)


def find_wet_feeder(devices: list) -> dict:
    for device in devices:
        if device["productName"] == "Polar Wet Food Feeder":
            return device
    raise RuntimeError("No wet feed found")


if __name__ == "__main__":
    asyncio.run(main())
