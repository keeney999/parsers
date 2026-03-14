
import sys


sys.path.append('.')

from loguru import logger
from config import settings
from parsers.yandex_parser import YandexParser
from parsers.avito_parser import AvitoParser
from parsers.wb_parser import WBParser
from parsers.hh_parser import HHParser


def test_yandex():
    """Тест Яндекс.Карт"""
    logger.info("=== ТЕСТ ЯНДЕКС.КАРТЫ ===")
    parser = YandexParser(
        settings,
        search_query="автосервис",
        city="москва",
        max_pages=1
    )
    items = parser.parse()
    parser.save_results("yandex_test", format="excel")
    logger.success(f"Яндекс тест: {len(items)} организаций")


def test_avito_with_proxy():
    """Тест Avito с прокси"""
    logger.info("=== ТЕСТ AVITO (с прокси) ===")

    # Загружаем прокси из файла если есть
    try:
        with open('proxies.txt', 'r') as f:
            proxy_list = [line.strip() for line in f if line.strip()]
            if proxy_list:
                settings.PROXY_LIST = proxy_list
                logger.info(f"Загружено {len(proxy_list)} прокси")
    except:
        logger.warning("Файл proxies.txt не найден, работаем без прокси")

    parser = AvitoParser(
        settings,
        search_query="iphone",
        region="moskva",
        max_pages=1
    )
    items = parser.parse()
    parser.save_results("avito_test", format="csv")
    logger.success(f"Avito тест: {len(items)} объявлений")


def test_wildberries():
    """Тест Wildberries"""
    parser = WBParser(
        settings,
        search_query="кроссовки",
        max_pages=1,
        headless=True
    )
    parser.parse()
    parser.save_results("wb_test", format="json")


if __name__ == "__main__":
    # По очереди тестируем
    test_yandex()
    test_avito_with_proxy()
    test_wildberries()

    logger.success("Все тесты выполнены. Результаты в папке results/")