import pathlib
import os
import sys
from dataclasses import dataclass
import logging
from logging import getLogger
from datetime import datetime


if "DEBUG" in os.environ:

    logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)


_LOGGER = getLogger(__name__)


this_dir = pathlib.Path(__file__).parent


def main():
    deleter = AutoDeleter(folder=this_dir / "recordings", size_limit=500 * 1024 * 1024)
    print("folder size: ", deleter.get_folder_size())
    print("to be deleted: ", deleter.to_be_deleted(deleter.get_filepaths()))
    input("Press Enter to continue...")
    deleter.run()


@dataclass
class AutoDeleter:
    folder: pathlib.Path
    file_prefix: str = "hourly_"
    file_suffix: str = ".mp4"
    size_limit: float = 20 * 1024 * 1024 * 1024  # 20GB, 0.5GB per hour

    def run(self):
        filepaths = self.get_filepaths()
        self.delete_oldest_files(filepaths)

    def get_filepaths(self) -> list[pathlib.Path]:
        filenames: list[tuple[pathlib.Path, float]] = []
        for filename in os.listdir(self.folder):
            if not filename.startswith(self.file_prefix):
                continue
            if not filename.endswith(self.file_suffix):
                continue
            filepath = self.folder / filename
            mtime = os.path.getmtime(filepath)
            filenames.append((filepath, mtime))
        filenames.sort(key=lambda x: x[1])
        return [filepath for filepath, _ in filenames]

    def size_of(self, filepaths: list[pathlib.Path]) -> int:
        total_size = 0
        for filepath in filepaths:
            total_size += os.path.getsize(filepath)
        return total_size

    def get_folder_size(self) -> int:
        return self.size_of(self.get_filepaths())

    def to_be_deleted(self, filepaths: list[pathlib.Path]) -> list[pathlib.Path]:
        to_be_deleted = []
        size = 0
        for filepath in reversed(filepaths):
            file_size = os.path.getsize(filepath)
            if size + file_size > self.size_limit:
                to_be_deleted.append(filepath)
            else:
                size += file_size
        return to_be_deleted

    def delete_oldest_files(self, filepaths: list[pathlib.Path]) -> None:
        to_be_deleted = self.to_be_deleted(filepaths)
        if to_be_deleted:
            _LOGGER.info(
                f"Deleting oldest files {to_be_deleted} at "
                + datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )
        for filepath in to_be_deleted:
            os.remove(filepath)


if __name__ == "__main__":
    main()
