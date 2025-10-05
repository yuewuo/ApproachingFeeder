from motion_detector import MotionDetector
from wet_feeder import WetFoodFeeder
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
def run_main(*, plate: int = 1):
    asyncio.run(main(plate=plate))


async def main(plate: int = 1):
    """
    when motion is detected, feed until the motion is gone
    Feed at most 10 minutes for the past hour (at most 1/6 of the whole day) to keep the food fresh
    """
    with MotionDetector() as detector:
        async with aiohttp.ClientSession() as session:
            feeder = WetFoodFeeder(session)
            await feeder.login()

            is_feeding = False
            past_hour_feeds: list[bool] = [False] * 60
            while True:
                await asyncio.sleep(1)

                past_hour_feeds.append(is_feeding)
                while len(past_hour_feeds) > 60:
                    past_hour_feeds.pop(0)

                first_no_motion: datetime | None = None
                if detector.is_motion_detected:
                    if not is_feeding:
                        _LOGGER.info(
                            "Start feeding at "
                            + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        )
                        try:
                            await feeder.manual_feed_now(plate)
                        except Exception as e:
                            _LOGGER.error(
                                "Failed to start feeding at "
                                + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            _LOGGER.error(e)
                        is_feeding = True
                    # feeding too long: preserve freshness instead of feeding for too long
                    elif sum(past_hour_feeds) > 10:
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

                        # delay closing the plate for 30 seconds so that Momo gets enough time to eat
                        if datetime.now() - first_no_motion > timedelta(seconds=30):
                            is_feeding = False
                            _LOGGER.info(
                                "Stop feeding at "
                                + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            )
                            try:
                                await feeder.stop_feed_now()
                            except Exception as e:
                                _LOGGER.error(e)
                            first_no_motion = None


if __name__ == "__main__":
    arguably.run()
