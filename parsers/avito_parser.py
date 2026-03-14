from typing import List
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from loguru import logger
from .base_parser import BaseParser


class AvitoItem(BaseModel):
    title: str = Field(default='', description='Название')
    price: str = Field(default='', description='Цена')
    link: str = Field(default='', description='Ссылка')
    address: str = Field(default='', description='Адрес')
    date: str = Field(default='', description='Дата публикации')
    seller_name: str = Field(default='', description='Продавец')
    seller_rating: str = Field(default='', description='Рейтинг продавца')


class AvitoParser(BaseParser):
    """Парсер Avito с продвинутой антиблокировкой"""

    def __init__(self, config, search_query: str, region: str = "moskva", max_pages: int = 3):
        super().__init__(config)
        self.search_query = search_query
        self.region = region
        self.max_pages = max_pages

    def parse(self) -> List[AvitoItem]:
        logger.info(f"Запуск Avito: '{self.search_query}' в регионе '{self.region}', страниц: {self.max_pages}")

        base_url = f"https://www.avito.ru/{self.region}?q={self.search_query.replace(' ', '+')}&p={{}}"
        all_items = []

        for page in range(1, self.max_pages + 1):
            url = base_url.format(page)
            logger.info(f"Парсинг страницы {page}")

            html = self._fetch_page(url)
            if not html:
                logger.error(f"Не удалось загрузить страницу {page}")
                continue

            page_items = self._parse_page(html)
            all_items.extend(page_items)
            logger.info(f"Найдено {len(page_items)} объявлений на странице {page}")

            # Задержка между страницами
            self._random_delay(min_delay=3.0, max_delay=6.0)

        self.results = all_items
        return all_items

    def _parse_page(self, html: str) -> List[AvitoItem]:
        soup = BeautifulSoup(html, 'lxml')
        items = []

        # Селекторы Avito (могут меняться, но на 2026 год актуальны)
        cards = soup.find_all('div', {'data-marker': 'item'})

        for card in cards:
            try:
                item = AvitoItem()

                # Название и ссылка
                title_tag = card.find('a', {'data-marker': 'item-title'})
                if title_tag:
                    item.title = title_tag.text.strip()
                    item.link = 'https://www.avito.ru' + title_tag.get('href', '')

                # Цена
                price_tag = card.find('meta', {'itemprop': 'price'})
                if price_tag:
                    item.price = price_tag.get('content', '')
                else:
                    price_tag = card.find('span', {'class': 'price-price'})
                    if price_tag:
                        item.price = price_tag.text.strip()

                # Адрес
                address_tag = card.find('span', {'class': 'address'})
                if address_tag:
                    item.address = address_tag.text.strip()

                # Дата
                date_tag = card.find('div', {'data-marker': 'item-date'})
                if date_tag:
                    item.date = date_tag.text.strip()

                # Продавец
                seller_tag = card.find('a', {'data-marker': 'seller-link'})
                if seller_tag:
                    item.seller_name = seller_tag.text.strip()

                items.append(item)
            except Exception as e:
                logger.warning(f"Ошибка парсинга карточки: {e}")
                continue

        return items