from loguru import logger
from config import settings
from parsers.avito_parser import AvitoParser
from parsers.wb_parser import WBParser
from parsers.gis_parser import GisParser
from parsers.hh_parser import HHParser
from parsers.tg_parser import TGParser

def test_avito():
    logger.info("=== ТЕСТ AVITO ===")
    parser = AvitoParser(settings, search_query="iphone 13", region="moskva", max_pages=1)
    parser.parse()
    parser.save_results("avito_test", format="excel")
    logger.success("Avito тест завершён")

def test_wildberries():
    logger.info("=== ТЕСТ WILDBERRIES ===")
    parser = WBParser(settings, search_query="кроссовки", max_pages=1, headless=True)
    parser.parse()
    parser.save_results("wb_test", format="csv")
    logger.success("Wildberries тест завершён")

def test_gis():
    logger.info("=== ТЕСТ 2ГИС ===")
    parser = GisParser(settings, city="Новосибирск", category="автосервис", max_pages=1, mode="api")
    parser.parse()
    parser.save_results("2gis_test", format="json")
    logger.success("2ГИС тест завершён")

def test_hh():
    logger.info("=== ТЕСТ HEADHUNTER ===")
    parser = HHParser(settings, search_text="python разработчик", area=113, max_pages=1)
    parser.parse()
    parser.save_results("hh_test", format="excel")
    logger.success("HH тест завершён")

def test_telegram():
    logger.info("=== ТЕСТ TELEGRAM ===")
    # Внимание: для Telegram нужны настроенные API ключи в .env
    parser = TGParser(settings, channels=["durov"], limit=5, download_media=False)
    parser.parse()
    parser.save_results("tg_test", format="json")
    logger.success("Telegram тест завершён")

if __name__ == "__main__":
    # По умолчанию запускаем всё, но можно закомментировать ненужное
    test_avito()
    test_wildberries()
    test_gis()
    test_hh()
    # test_telegram()  # раскомментируй, если настроил Telegram
    logger.info("Все тесты выполнены. Результаты в папке results/")