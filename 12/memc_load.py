#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Конкурентная загрузка данных о установленных приложениях в Memcached.

Парсит TSV.gz файлы с выгрузкой логов трекера и загружает данные в Memcached
используя многопоточную обработку для повышения производительности.

Пример запуска:
    python memc_load.py --pattern=*.tsv.gz --dry

Пример боевого запуска:
    python memc_load.py --pattern=/data/appsinstalled/*.tsv.gz \\
        --idfa=memcached1:11211 --gaid=memcached2:11211
"""
import os
import gzip
import sys
import glob
import logging
import collections
import concurrent.futures
from optparse import OptionParser, Values

# brew install protobuf
# protoc --python_out=. ./appsinstalled.proto
# pip install protobuf
import appsinstalled_pb2  # type: ignore

# pip install python-memcached
import memcache  # type: ignore


NORMAL_ERR_RATE = 0.01
DEFAULT_WORKERS = 16
AppsInstalled = collections.namedtuple(
    "AppsInstalled", ["dev_type", "dev_id", "lat", "lon", "apps"]
)


def dot_rename(path: str) -> None:
    """Атомарно переименовывает файл, добавляя точку в начало имени.

    Args:
        path: Путь к файлу для переименования.
    """
    head, fn = os.path.split(path)
    # atomic in most cases
    os.rename(path, os.path.join(head, "." + fn))


class MemcachedClient:
    """Пул подключений к Memcached с разделением по адресам."""

    def __init__(self) -> None:
        """Инициализирует пустой пул подключений."""
        self._clients: dict[str, memcache.Client] = {}

    def get_client(self, memc_addr: str) -> memcache.Client:
        """Возвращает или создаёт клиент для указанного адреса.

        Args:
            memc_addr: Адрес Memcached сервера.

        Returns:
            Клиент memcache для указанного адреса.
        """
        if memc_addr not in self._clients:
            self._clients[memc_addr] = memcache.Client([memc_addr], debug=0)
        return self._clients[memc_addr]


# Глобальный пул клиентов (для использования в потоках)
_memc_pool = MemcachedClient()


def insert_appsinstalled(
    memc_addr: str, appsinstalled: AppsInstalled, dry_run: bool = False
) -> bool:
    """Вставляет запись о приложениях устройства в Memcached.

    Args:
        memc_addr: Адрес Memcached сервера.
        appsinstalled: Данные о приложениях устройства.
        dry_run: Если True, только логирует операцию без реальной записи.

    Returns:
        True при успешной операции, False при ошибке.
    """
    ua = appsinstalled_pb2.UserApps()
    ua.lat = appsinstalled.lat
    ua.lon = appsinstalled.lon
    key = f"{appsinstalled.dev_type}:{appsinstalled.dev_id}"
    ua.apps.extend(appsinstalled.apps)
    packed = ua.SerializeToString()

    try:
        if dry_run:
            logging.debug(
                f"{memc_addr} - {key} -> {str(ua).replace(chr(10), ' ')}"
            )
        else:
            client = _memc_pool.get_client(memc_addr)
            client.set(key, packed)
    except Exception as e:
        logging.exception(f"Cannot write to memc {memc_addr}: {e}")
        return False
    return True


def parse_appsinstalled(line: str) -> AppsInstalled | None:
    """Парсит строку TSV в объект AppsInstalled.

    Args:
        line: Строка из TSV файла.

    Returns:
        Объект AppsInstalled или None при ошибке парсинга.
    """
    line_parts = line.strip().split("\t")
    if len(line_parts) < 5:
        return None
    dev_type, dev_id, lat, lon, raw_apps = line_parts
    if not dev_type or not dev_id:
        return None
    try:
        apps = [int(a.strip()) for a in raw_apps.split(",")]
    except ValueError:
        apps = [
            int(a.strip()) for a in raw_apps.split(",") if a.strip().isdigit()
        ]
        logging.info(f"Not all user apps are digits: `{line}`")
    try:
        lat_f, lon_f = float(lat), float(lon)
    except ValueError:
        logging.info(f"Invalid geo coords: `{line}`")
        return None
    return AppsInstalled(dev_type, dev_id, lat_f, lon_f, apps)


def process_line(
    line: str,
    device_memc: dict[str, str],
    dry: bool,
) -> tuple[bool, bool]:
    """Обрабатывает одну строку TSV: парсит и загружает в Memcached.

    Args:
        line: Строка из TSV файла.
        device_memc: Словарь соответствия типа устройства и адреса Memcached.
        dry: Режим сухого запуска.

    Returns:
        Кортеж (success, is_error) где success - успех операции,
        is_error - была ли ошибка парсинга.
    """
    line = line.strip()
    if not line:
        return True, False

    appsinstalled = parse_appsinstalled(line)
    if not appsinstalled:
        return False, True

    memc_addr = device_memc.get(appsinstalled.dev_type)
    if not memc_addr:
        logging.error(f"Unknown device type: {appsinstalled.dev_type}")
        return False, True

    ok = insert_appsinstalled(memc_addr, appsinstalled, dry)
    return ok, False


def main(options: Values) -> None:
    """Основная функция загрузки данных.

    Обрабатывает файлы в хронологическом порядке, используя
    многопоточную обработку строк внутри каждого файла.

    Args:
        options: Объект с опциями командной строки.
    """
    device_memc = {
        "idfa": options.idfa,
        "gaid": options.gaid,
        "adid": options.adid,
        "dvid": options.dvid,
    }

    # Сортируем файлы для хронологической обработки
    files = sorted(glob.glob(options.pattern))

    for fn in files:
        processed = errors = 0
        logging.info(f"Processing {fn}")
        try:
            with gzip.open(fn, mode="rt", encoding="utf-8") as fd:
                lines = fd.readlines()

            with concurrent.futures.ThreadPoolExecutor(
                max_workers=options.workers
            ) as executor:
                # Отправляем все строки на обработку
                future_to_index = {
                    executor.submit(
                        process_line, line, device_memc, options.dry
                    ): i
                    for i, line in enumerate(lines)
                }

                # Собираем результаты
                for future in concurrent.futures.as_completed(future_to_index):
                    ok, is_error = future.result()
                    if is_error:
                        errors += 1
                    else:
                        processed += 1
        except OSError as e:
            logging.exception(f"Error opening file {fn}: {e}")
            continue

        if not processed:
            dot_rename(fn)
            continue

        err_rate = float(errors) / processed
        if err_rate < NORMAL_ERR_RATE:
            logging.info(
                f"Acceptable error rate ({err_rate}). Successful load"
            )
        else:
            logging.error(
                f"High error rate ({err_rate} > "
                f"{NORMAL_ERR_RATE}). Failed load"
            )
        dot_rename(fn)


def prototest() -> None:
    """Тест сериализации/десериализации protobuf сообщений."""
    sample = """idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23
gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"""
    for line in sample.splitlines():
        parts = line.strip().split("\t")
        if len(parts) != 5:
            continue
        dev_type, dev_id, lat, lon, raw_apps = parts
        apps = [int(a) for a in raw_apps.split(",") if a.strip().isdigit()]
        lat_f, lon_f = float(lat), float(lon)
        ua = appsinstalled_pb2.UserApps()
        ua.lat = lat_f
        ua.lon = lon_f
        ua.apps.extend(apps)
        packed = ua.SerializeToString()
        unpacked = appsinstalled_pb2.UserApps()
        unpacked.ParseFromString(packed)
        assert ua == unpacked


if __name__ == "__main__":
    op = OptionParser()
    op.add_option("-t", "--test", action="store_true", default=False)
    op.add_option("-l", "--log", action="store", default=None)
    op.add_option("--dry", action="store_true", default=False)
    op.add_option(
        "--pattern",
        action="store",
        default="/data/appsinstalled/*.tsv.gz",
    )
    op.add_option("--idfa", action="store", default="127.0.0.1:33013")
    op.add_option("--gaid", action="store", default="127.0.0.1:33014")
    op.add_option("--adid", action="store", default="127.0.0.1:33015")
    op.add_option("--dvid", action="store", default="127.0.0.1:33016")
    op.add_option(
        "--workers",
        type="int",
        action="store",
        default=DEFAULT_WORKERS,
    )
    (opts, args) = op.parse_args()

    log_level = logging.DEBUG if opts.dry else logging.INFO
    logging.basicConfig(
        filename=opts.log,
        level=log_level,
        format="[%(asctime)s] %(levelname).1s %(message)s",
        datefmt="%Y.%m.%d %H:%M:%S",
    )

    if opts.test:
        prototest()
        sys.exit(0)

    logging.info(f"Memc loader started with options: {opts}")
    try:
        main(opts)
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        sys.exit(1)
