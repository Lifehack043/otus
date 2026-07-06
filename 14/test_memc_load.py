"""Тесты для memc_load.py"""
import os
import gzip
import tempfile
import shutil
import unittest
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from memc_load import (
    parse_appsinstalled,
    process_line,
    dot_rename,
    MemcachedClient,
    prototest,
)


class TestParseAppsInstalled(unittest.TestCase):
    """Тесты для функции parse_appsinstalled."""

    def test_valid_idfa_line(self):
        """Проверка корректного парсинга строки с IDFA."""
        line = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567,3,7,23"
        result = parse_appsinstalled(line)
        self.assertIsNotNone(result)
        self.assertEqual(result.dev_type, "idfa")
        self.assertEqual(result.dev_id, "1rfw452y52g2gq4g")
        self.assertEqual(result.lat, 55.55)
        self.assertEqual(result.lon, 42.42)
        self.assertEqual(result.apps, [1423, 43, 567, 3, 7, 23])

    def test_valid_gaid_line(self):
        """Проверка корректного парсинга строки с GAID."""
        line = "gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424"
        result = parse_appsinstalled(line)
        self.assertIsNotNone(result)
        self.assertEqual(result.dev_type, "gaid")
        self.assertEqual(result.apps, [7423, 424])

    def test_invalid_line_too_few_fields(self):
        """Проверка обработки строки с недостаточным количеством полей."""
        line = "idfa\t1rfw452y52g2gq4g\t55.55"
        result = parse_appsinstalled(line)
        self.assertIsNone(result)

    def test_empty_dev_type(self):
        """Проверка обработки строки с пустым типом устройства."""
        line = "\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43"
        result = parse_appsinstalled(line)
        self.assertIsNone(result)

    def test_empty_dev_id(self):
        """Проверка обработки строки с пустым ID устройства."""
        line = "idfa\t\t55.55\t42.42\t1423,43"
        result = parse_appsinstalled(line)
        self.assertIsNone(result)

    def test_invalid_coords(self):
        """Проверка обработки строки с невалидными координатами."""
        line = "idfa\t1rfw452y52g2gq4g\tabc\t42.42\t1423,43"
        result = parse_appsinstalled(line)
        self.assertIsNone(result)

    def test_partial_invalid_apps(self):
        """Проверка обработки строки с частично невалидными ID приложений."""
        line = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,abc,567"
        result = parse_appsinstalled(line)
        self.assertIsNotNone(result)
        self.assertEqual(result.apps, [1423, 567])


class TestProcessLine(unittest.TestCase):
    """Тесты для функции process_line."""

    def test_empty_line(self):
        """Проверка обработки пустой строки."""
        device_memc = {"idfa": "127.0.0.1:11211"}
        success, is_error = process_line("", device_memc, dry=True)
        self.assertTrue(success)
        self.assertFalse(is_error)

    def test_valid_line_dry_run(self):
        """Проверка обработки валидной строки в режиме dry run."""
        line = "idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43"
        device_memc = {"idfa": "127.0.0.1:11211"}
        success, is_error = process_line(line, device_memc, dry=True)
        self.assertTrue(success)
        self.assertFalse(is_error)

    def test_unknown_device_type(self):
        """Проверка обработки строки с неизвестным типом устройства."""
        line = "unknown\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43"
        device_memc = {"idfa": "127.0.0.1:11211"}
        success, is_error = process_line(line, device_memc, dry=True)
        self.assertFalse(success)
        self.assertTrue(is_error)

    def test_invalid_line(self):
        """Проверка обработки невалидной строки."""
        line = "invalid_line"
        device_memc = {"idfa": "127.0.0.1:11211"}
        success, is_error = process_line(line, device_memc, dry=True)
        self.assertFalse(success)
        self.assertTrue(is_error)


class TestDotRename(unittest.TestCase):
    """Тесты для функции dot_rename."""

    def test_rename_adds_dot_prefix(self):
        """Проверка что файл переименовывается с точкой в начале."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            dot_rename(test_file)
            self.assertFalse(os.path.exists(test_file))
            self.assertTrue(os.path.exists(os.path.join(tmpdir, ".test.txt")))


class TestMemcachedClient(unittest.TestCase):
    """Тесты для класса MemcachedClient."""

    def test_get_client_creates_new(self):
        """Проверка создания нового клиента."""
        pool = MemcachedClient()
        client = pool.get_client("127.0.0.1:11211")
        self.assertIsNotNone(client)

    def test_get_client_reuses_existing(self):
        """Проверка повторного использования клиента."""
        pool = MemcachedClient()
        client1 = pool.get_client("127.0.0.1:11211")
        client2 = pool.get_client("127.0.0.1:11211")
        self.assertIs(client1, client2)

    def test_get_client_different_addresses(self):
        """Проверка создания разных клиентов для разных адресов."""
        pool = MemcachedClient()
        client1 = pool.get_client("127.0.0.1:11211")
        client2 = pool.get_client("127.0.0.1:11212")
        self.assertIsNot(client1, client2)


class TestProtoTest(unittest.TestCase):
    """Тесты для функции prototest."""

    def test_prototest_runs_without_error(self):
        """Проверка что prototest выполняется без ошибок."""
        prototest()  # Не должен выбрасывать исключение


class TestIntegration(unittest.TestCase):
    """Интеграционные тесты."""

    def setUp(self):
        """Создаёт временный каталог для тестов."""
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        """Очищает временный каталог."""
        shutil.rmtree(self.tmpdir)

    def test_process_tsv_file_dry_run(self):
        """Проверка обработки TSV файла в режиме dry run."""
        from memc_load import main

        # Создаём тестовый TSV.gz файл
        test_file = os.path.join(self.tmpdir, "20170929000000.tsv.gz")
        with gzip.open(test_file, "wt", encoding="utf-8") as f:
            f.write("idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423,43,567\n")
            f.write("gaid\t7rfw452y52g2gq4g\t55.55\t42.42\t7423,424\n")
            f.write("\n")  # Пустая строка
            f.write("idfa\t2rfw452y52g2gq4g\t-10.5\t20.3\t100,200\n")

        # Создаём опции
        options = SimpleNamespace(
            dry=True,
            test=False,
            log=None,
            pattern=os.path.join(self.tmpdir, "*.tsv.gz"),
            idfa="127.0.0.1:33013",
            gaid="127.0.0.1:33014",
            adid="127.0.0.1:33015",
            dvid="127.0.0.1:33016",
            workers=4,
        )

        # Запускаем main
        main(options)

        # Проверяем что файл был переименован
        self.assertFalse(os.path.exists(test_file))
        self.assertTrue(
            os.path.exists(os.path.join(self.tmpdir, ".20170929000000.tsv.gz"))
        )

    def test_files_processed_in_order(self):
        """Проверка что файлы обрабатываются в хронологическом порядке."""
        from memc_load import main

        # Создаём несколько тестовых файлов
        timestamps = ["20170929000200", "20170929000000", "20170929000100"]
        files = []
        for ts in timestamps:
            test_file = os.path.join(self.tmpdir, f"{ts}.tsv.gz")
            with gzip.open(test_file, "wt", encoding="utf-8") as f:
                f.write("idfa\t1rfw452y52g2gq4g\t55.55\t42.42\t1423\n")
            files.append(test_file)

        options = SimpleNamespace(
            dry=True,
            test=False,
            log=None,
            pattern=os.path.join(self.tmpdir, "*.tsv.gz"),
            idfa="127.0.0.1:33013",
            gaid="127.0.0.1:33014",
            adid="127.0.0.1:33015",
            dvid="127.0.0.1:33016",
            workers=4,
        )

        main(options)

        # Все файлы должны быть переименованы
        for ts in timestamps:
            processed = os.path.join(self.tmpdir, f".{ts}.tsv.gz")
            self.assertTrue(os.path.exists(processed))


if __name__ == "__main__":
    unittest.main()
