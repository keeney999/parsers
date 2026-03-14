import asyncio
import re
from typing import List
from playwright.async_api import async_playwright, Browser, Page
from pydantic import BaseModel, Field
from loguru import logger
from .base_parser import BaseParser


class WBItem(BaseModel):
    name: str = Field(default='', description='Название товара')
    brand: str = Field(default='', description='Бренд')
    price: str = Field(default='', description='Цена')
    old_price: str = Field(default='', description='Старая цена (со скидкой)')
    rating: str = Field(default='', description='Рейтинг')
    reviews: str = Field(default='', description='Количество отзывов')
    link: str = Field(default='', description='Ссылка на товар')
    article: str = Field(default='', description='Артикул')


class WBParser(BaseParser):
    """Парсер Wildberries через Playwright (для динамических страниц)"""

    def __init__(self, config, search_query: str, max_pages: int = 2, headless: bool = True):
        super().__init__(config)
        self.search_query = search_query
        self.max_pages = max_pages
        self.headless = headless

    def parse(self) -> List[WBItem]:
        logger.info(f"Запуск Wildberries: '{self.search_query}', страниц: {self.max_pages}")
        asyncio.run(self._async_parse())
        return self.results

    async def _async_parse(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(
                user_agent=self.ua.random,
                viewport={'width': 1920, 'height': 1080},
                locale='ru-RU'
            )
            page = await context.new_page()

            for page_num in range(1, self.max_pages + 1):
                url = f"https://www.wildberries.ru/catalog/0/search.aspx?page={page_num}&search={self.search_query.replace(' ', '%20')}"
                logger.info(f"Загрузка страницы {page_num}")

                try:
                    await page.goto(url, wait_until='networkidle')
                    await page.wait_for_selector('.product-card__wrapper', timeout=30000)

                    # Скроллим для подгрузки lazy-load товаров
                    for _ in range(3):
                        await page.evaluate('window.scrollBy(0, 1000)')
                        await asyncio.sleep(1)

                    # Собираем карточки
                    cards = await page.query_selector_all('.product-card__wrapper')
                    logger.info(f"Найдено карточек: {len(cards)}")

                    for card in cards:
                        try:
                            item = WBItem()

                            # Название и бренд
                            brand_name = await card.query_selector('.product-card__brand-name')
                            if brand_name:
                                text = await brand_name.inner_text()
                                parts = text.split('/')
                                if len(parts) >= 2:
                                    item.brand = parts[0].strip()
                                    item.name = parts[1].strip()
                                else:
                                    item.name = text

                            # Цена
                            price = await card.query_selector('.price__lower-price')
                            if price:
                                item.price = await price.inner_text()

                            # Старая цена
                            old_price = await card.query_selector('.price__old-price')
                            if old_price:
                                item.old_price = await old_price.inner_text()

                            # Рейтинг
                            rating = await card.query_selector('.product-card__rating')
                            if rating:
                                item.rating = await rating.inner_text()

                            # Ссылка и артикул
                            link_elem = await card.query_selector('.product-card__link')
                            if link_elem:
                                href = await link_elem.get_attribute('href')
                                if href:
                                    item.link = f'https://www.wildberries.ru{href}'
                                    match = re.search(r'/(\d+)/', href)
                                    if match:
                                        item.article = match.group(1)

                            self.results.append(item)

                        except Exception as e:
                            logger.warning(f"Ошибка парсинга карточки: {e}")
                            continue

                    await self._random_delay_async(3, 6)

                except Exception as e:
                    logger.error(f"Ошибка на странице {page_num}: {e}")

            await browser.close()

    async def _random_delay_async(self, min_delay: float, max_delay: float):
        import random, asyncio
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"Задержка {delay:.2f} сек")
        await asyncio.sleep(delay)