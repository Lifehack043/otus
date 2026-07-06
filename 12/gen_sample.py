"""Утилита для генерации tsv.gz файлов со случайными данными устройств"""

import argparse
import datetime
import gzip
import hashlib
import os
import random

DEV_ID_TYPES = ["idfa", "gaid", "adid", "dvid"]
MAX_DEV_ID = 100_000_000
APPS = [str(a) for a in range(10_000)]
NUM_FILES = 3
FILE_SIZE = 0.5 * 1024**3  # 512 MiB


def random_point() -> tuple[float, float]:
    """Возвращает случайную пару (широта, долгота)."""
    return random.uniform(-180, 180), random.uniform(-90, 90)


def gen_line() -> str:
    """Генерирует одну строку TSV со случайными данными устройства."""
    dev_type = random.choice(DEV_ID_TYPES)
    dev_id = hashlib.md5(str(random.randint(1, MAX_DEV_ID)).encode("utf-8")).hexdigest()
    lat, lon = random_point()
    apps = random.sample(APPS, random.randint(1, 100))
    return "\t".join([dev_type, dev_id, str(lat), str(lon), ",".join(apps)])


def main(directory: str) -> None:
    """Генерирует `NUM_FILES` сжатых TSV файлов. Каждый файл заполняется и сжимается примерно до `FILE_SIZE / 2` байт данных"""

    utc_now = datetime.datetime.now(tz=datetime.timezone.utc)
    start_day = utc_now.replace(hour=0, minute=0, second=0, microsecond=0)

    for i in range(NUM_FILES):
        timestamp = (start_day + datetime.timedelta(minutes=i)).strftime("%Y%m%d%H%M%S")
        path = os.path.join(directory, f"{timestamp}.tsv.gz")
        with gzip.open(path, mode="wt", encoding="utf-8") as fd:
            written = 0
            while written < FILE_SIZE:
                line = gen_line() + "\n"
                fd.write(line)
                written += len(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", help="Куда сохранить файл")
    args = parser.parse_args()
    main(args.directory)
