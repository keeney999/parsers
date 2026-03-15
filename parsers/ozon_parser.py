import asyncio
import random
from typing import List
from pydantic import BaseModel, Field
from loguru import logger
from playwright.async_api import async_playwright
from .base_parser import BaseParser

class OzonItem(BaseModel):
    name: str = Field(default='', description='Название товара')
    price: str = Field(default='', description='Цена')
    old_price: str = Field(default='', description='Старая цена')
    rating: float = Field(default=0.0, description='Рейтинг')
    reviews: int = Field(default=0, description='Количество отзывов')
    link: str = Field(default='', description='Ссылка на товар')
    article: str = Field(default='', description='Артикул')


class OzonParser(BaseParser):
    """Парсер Ozon с гарантированным перехватом API"""

    def __init__(self, config, search_query: str, max_pages: int = 1, headless: bool = True):
        super().__init__(config)
        self.search_query = search_query
        self.max_pages = max_pages
        self.headless = headless
        self.api_responses = []

    def parse(self) -> List[OzonItem]:
        logger.info(f"Ozon: поиск '{self.search_query}', страниц: {self.max_pages}")
        asyncio.run(self._async_parse())
        return self.results

    async def _async_parse(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            page = await browser.new_page()
            await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru']});
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            """)

            # Очищаем список ответов перед каждой страницей
            self.api_responses = []

            # Перехватываем API-запросы поиска
            async def handle_route(route):
                if "/api/entrypoint-api.bx/page/json/v2" in route.request.url and "search" in route.request.url:
                    logger.debug(f"Перехвачен API запрос: {route.request.url}")
                    response = await route.fetch()
                    self.api_responses.append(response)
                    await route.fulfill(response=response)
                else:
                    await route.continue_()

            await page.route("**/*", handle_route)

            for page_num in range(1, self.max_pages + 1):
                url = f"https://www.ozon.ru/search/?text={self.search_query}&page={page_num}"
                logger.info(f"Загрузка страницы {page_num}")

                # Очищаем ответы для новой страницы
                self.api_responses = []

                await page.goto(url, wait_until="networkidle")
                await page.wait_for_timeout(7000)  # ждём загрузки всех API

                if not self.api_responses:
                    logger.error("Не удалось перехватить API-ответ")
                    # Сохраняем HTML для отладки
                    html = await page.content()
                    with open(f"debug_ozon_page_{page_num}.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    logger.info(f"Сохранён HTML страницы в debug_ozon_page_{page_num}.html")
                    continue

                # Берём последний ответ (обычно он содержит результаты поиска)
                api_response = self.api_responses[-1]

                try:
                    data = await api_response.json()
                    items = self._extract_products(data)
                    logger.info(f"Страница {page_num}: получено {len(items)} товаров")
                    self.results.extend(items)

                except Exception as e:
                    logger.error(f"Ошибка парсинга JSON: {e}")

                await self._random_delay_async(3, 6)

            await browser.close()

    def _extract_products(self, data):
        """Извлечение товаров из JSON Ozon (универсальный поиск)"""
        products = []
        try:
            # Рекурсивно ищем все объекты с полем 'sku'
            def find_sku_objects(obj, found=None):
                if found is None:
                    found = []
                if isinstance(obj, dict):
                    if 'sku' in obj:
                        found.append(obj)
                    for value in obj.values():
                        find_sku_objects(value, found)
                elif isinstance(obj, list):
                    for item in obj:
                        find_sku_objects(item, found)
                return found

            items_with_sku = find_sku_objects(data)
            logger.debug(f"Найдено объектов с SKU: {len(items_with_sku)}")

            for raw in items_with_sku:
                try:
                    item = OzonItem()
                    item.article = str(raw.get('sku', ''))
                    item.name = raw.get('title', '') or raw.get('name', '')

                    # Ищем цену
                    if 'price' in raw:
                        price_info = raw['price']
                        if isinstance(price_info, dict):
                            item.price = str(price_info.get('price', ''))
                            item.old_price = str(price_info.get('oldPrice', ''))

                    # Ищем рейтинг
                    if 'rating' in raw:
                        item.rating = float(raw.get('rating', 0))

                    # Ищем отзывы
                    if 'feedbacksCount' in raw:
                        item.reviews = int(raw.get('feedbacksCount', 0))

                    item.link = f"https://www.ozon.ru/product/{item.article}/"

                    if item.name and item.article:
                        products.append(item)

                except Exception as e:
                    logger.warning(f"Ошибка при парсинге товара: {e}")
                    continue

        except Exception as e:
            logger.warning(f"Не удалось извлечь товары: {e}")

        return products

    async def _random_delay_async(self, min_delay: float, max_delay: float):
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"Задержка {delay:.2f} сек")
        await asyncio.sleep(delay)