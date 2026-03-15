import asyncio
import random
import re
from typing import List, Optional
from pydantic import BaseModel, Field
from loguru import logger
from playwright.async_api import async_playwright
from .base_parser import BaseParser

class WBItem(BaseModel):
    name: str = Field(default='', description='Название товара')
    brand: str = Field(default='', description='Бренд')
    price: str = Field(default='', description='Цена')
    old_price: str = Field(default='', description='Старая цена')
    rating: float = Field(default=0.0, description='Рейтинг')
    reviews: int = Field(default=0, description='Количество отзывов')
    link: str = Field(default='', description='Ссылка на товар')
    article: str = Field(default='', description='Артикул')


class WBParser(BaseParser):
    """Парсер Wildberries с гарантированным перехватом API"""

    def __init__(self, config, search_query: str, max_pages: int = 2, headless: bool = True):
        super().__init__(config)
        self.search_query = search_query
        self.max_pages = max_pages
        self.headless = headless
        self.api_response = None

    def parse(self) -> List[WBItem]:
        logger.info(f"Запуск Wildberries: '{self.search_query}', страниц: {self.max_pages}")
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

            for page_num in range(1, self.max_pages + 1):
                url = f"https://www.wildberries.ru/catalog/0/search.aspx?page={page_num}&search={self.search_query.replace(' ', '%20')}"
                logger.info(f"Загрузка страницы {page_num}")

                # Очищаем предыдущий ответ
                self.api_response = None

                # Перехватываем нужный API-запрос
                async def handle_route(route):
                    if "/__internal/u-recom/personal/ru/common/v8/search" in route.request.url:
                        logger.debug(f"Перехвачен API запрос: {route.request.url}")
                        # Ждём реальный ответ от сервера
                        response = await route.fetch()
                        self.api_response = response
                        await route.fulfill(response=response)
                    else:
                        await route.continue_()

                await page.route("**/*", handle_route)

                # Переходим на страницу и ждём загрузки
                await page.goto(url, wait_until="networkidle")

                # Даём дополнительное время на выполнение JavaScript
                await page.wait_for_timeout(5000)

                try:
                    data = await self.api_response.json()
                    products = data.get("data", {}).get("products", [])
                    logger.info(f"Страница {page_num}: получено {len(products)} товаров")

                    for p in products:
                        item = WBItem()
                        item.name = p.get("name", "")
                        item.brand = p.get("brand", "")
                        price_info = p.get("sizes", [{}])[0].get("price", {})
                        item.price = str(price_info.get("product", ""))
                        item.old_price = str(price_info.get("total", ""))
                        item.rating = p.get("rating", 0.0)
                        item.reviews = p.get("feedbacks", 0)
                        item.link = f"https://www.wildberries.ru/catalog/{p.get('id', '')}/detail.aspx"
                        item.article = str(p.get("id", ""))
                        self.results.append(item)

                except Exception as e:
                    logger.error(f"Ошибка парсинга JSON: {e}")

                await self._random_delay_async(3, 6)

            await browser.close()

    async def _random_delay_async(self, min_delay: float, max_delay: float):
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"Задержка {delay:.2f} сек")
        await asyncio.sleep(delay)