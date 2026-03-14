
import sys


sys.path.append('.')

from loguru import logger
from config import settings
from parsers.avito_parser import AvitoParser
from parsers.wb_parser import WBParser
from parsers.gis_parser import GisParser
from parsers.hh_parser import HHParser
from parsers.tg_parser import TGParser
from parsers.yandex_parser import YandexParser


def test_avito():
    logger.info("=== Тест Avito ===")
    parser = AvitoParser(settings, search_query="iphone 13", region="moskva", max_pages=1)
    items = parser.parse()
    parser.save_results("avito_test", format="csv")
    logger.success(f"Avito: {len(items)} объявлений")


def test_wildberries():
    logger.info("=== Тест Wildberries ===")
    parser = WBParser(settings, search_query="кроссовки", max_pages=1, headless=True)
    parser.parse()
    parser.save_results("wb_test", format="json")
    logger.success("Wildberries тест завершён")


def test_gis():
    logger.info("=== Тест 2ГИС (API) ===")
    parser = GisParser(settings, city="Новосибирск", category="автосервис", max_pages=1, mode="api")
    items = parser.parse()
    parser.save_results("gis_api_test", format="excel")
    logger.success(f"2ГИС API: {len(items)} организаций")


def test_hh():
    logger.info("=== Тест HeadHunter ===")
    parser = HHParser(settings, search_text="python разработчик", area=113, max_pages=1)
    items = parser.parse()
    parser.save_results("hh_test", format="csv")
    logger.success(f"HH: {len(items)} вакансий")


def test_yandex():
    logger.info("=== Тест Яндекс.Карты ===")
    parser = YandexParser(settings, search_query="автосервис", city="москва", max_pages=1)
    items = parser.parse()
    parser.save_results("yandex_test", format="excel")
    logger.success(f"Яндекс: {len(items)} организаций")


def test_telegram():
    logger.info("=== Тест Telegram (требуются настройки) ===")
    if not settings.TG_API_ID or not settings.TG_API_HASH:
        logger.warning("Telegram не настроен, пропускаем")
        return
    parser = TGParser(settings, channels=["durov"], limit=5, download_media=False)
    parser.parse()
    parser.save_results("tg_test", format="json")
    logger.success("Telegram тест завершён")


if __name__ == "__main__":
    logger.info("=" * 50)
    logger.info("ЗАПУСК ТЕСТИРОВАНИЯ ВСЕХ ПАРСЕРОВ")
    logger.info("=" * 50)

    test_avito()
    test_wildberries()
    test_gis()
    test_hh()
    test_yandex()
    test_telegram()

    logger.success("Все тесты выполнены. Результаты в папке results/")