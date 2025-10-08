from motion_detector import MotionDetector, this_dir
from wet_feeder import WetFoodFeeder
from auto_deleter import AutoDeleter
from auto_torch import AutoTorch
import asyncio
import aiohttp
import arguably
from datetime import datetime, timedelta
from logging import getLogger
import logging

# TODO: in the future, automatically detect if there are still food in the plate and select the appropriate plate among 3

logging.basicConfig(
    filename="approach_feeder.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


_LOGGER = getLogger(__name__)


@arguably.command
def run_main(
    *,
    plate: int = 1,
    hourly_max_GB: float = 20,
    original_max_GB: float = 20,
    ip_port: str = "192.168.0.91:8080",
):
    asyncio.run(
        main(
            plate=plate,
            hourly_max_GB=hourly_max_GB,
            original_max_GB=original_max_GB,
            ip_port=ip_port,
        )
    )


async def main(plate: int, hourly_max_GB: float, original_max_GB: float, ip_port: str):
    """
    when motion is detected, feed until the motion is gone
    Feed at most 10 minutes for the past hour (at most 1/6 of the whole day) to keep the food fresh
    Feed at most 10 times in the past hour: if more than that, it's probably unnecessarily
    """
    auto_torch = AutoTorch(ip_port=ip_port)

    async with aiohttp.ClientSession() as session:
        feeder = WetFoodFeeder(session)
        await feeder.login()

        # stop feeding first to ensure that the reference image plate is closed
        try:
            await feeder.stop_feed_now()
        except Exception as e:
            _LOGGER.error(
                "Failed initial stop feeding at "
                + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
            _LOGGER.error(e)
        await asyncio.sleep(3)

        with MotionDetector(ip_port=ip_port) as detector:

            is_feeding = False
            past_hour_feeds: list[bool] = [False] * 3600
            past_hour_starts: list[bool] = [False] * 3600
            first_no_motion: datetime | None = None

            hourly_deleter = AutoDeleter(
                folder=this_dir / "recordings",
                file_prefix="hourly_",
                file_suffix=".mp4",
                size_limit=hourly_max_GB * 1024 * 1024 * 1024,
            )
            original_deleter = AutoDeleter(
                folder=this_dir / "recordings",
                file_prefix="original_",
                file_suffix=".mp4",
                size_limit=original_max_GB * 1024 * 1024 * 1024,
            )

            while True:
                if detector.frame is not None:
                    auto_torch.run(detector.frame)
                hourly_deleter.run()
                original_deleter.run()
                await asyncio.sleep(1)

                past_hour_feeds.append(is_feeding)
                past_hour_starts.append(False)
                while len(past_hour_feeds) > 3600:
                    past_hour_feeds.pop(0)
                while len(past_hour_starts) > 3600:
                    past_hour_starts.pop(0)

                if detector.is_motion_detected:
                    first_no_motion = None
                    # feed at most 10 times in the past hour: if more than that, it's probably unnecessarily
                    if not is_feeding and sum(past_hour_starts) < 10:
                        _LOGGER.info(
                            "Start feeding at "
                            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        past_hour_starts[-1] = True  # mark the last one as True
                        try:
                            await feeder.manual_feed_now(plate)
                        except Exception as e:
                            _LOGGER.error(
                                "Failed to start feeding at "
                                + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            _LOGGER.error(e)
                        is_feeding = True
                    # feeding too long: preserve freshness instead of feeding for too long (>10min)
                    elif is_feeding and sum(past_hour_feeds) > 10 * 60:
                        is_feeding = False
                        _LOGGER.info(
                            "Stop feeding because it has been feeding for too long at "
                            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        try:
                            await feeder.stop_feed_now()
                        except Exception as e:
                            _LOGGER.error(
                                "Failed to stop feeding at "
                                + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            _LOGGER.error(e)
                else:
                    if is_feeding:
                        if first_no_motion is None:
                            first_no_motion = datetime.now()
                            _LOGGER.info(
                                "First no motion at "
                                + first_no_motion.strftime("%Y-%m-%d %H:%M:%S")
                            )

                        # delay closing the plate for 30 seconds so that Momo gets enough time to eat
                        if datetime.now() - first_no_motion > timedelta(seconds=30):
                            is_feeding = False
                            first_no_motion = None
                            _LOGGER.info(
                                "Stop feeding at "
                                + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            try:
                                await feeder.stop_feed_now()
                            except Exception as e:
                                _LOGGER.error(e)


if __name__ == "__main__":
    arguably.run()
