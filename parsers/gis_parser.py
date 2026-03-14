from typing import List
from pydantic import BaseModel, Field
from loguru import logger
from .base_parser import BaseParser
from bs4 import BeautifulSoup


class GisItem(BaseModel):
    name: str = Field(default='', description='Название организации')
    phones: str = Field(default='', description='Телефоны')
    website: str = Field(default='', description='Сайт')
    address: str = Field(default='', description='Адрес')
    email: str = Field(default='', description='Email')
    working_hours: str = Field(default='', description='Режим работы')


class GisParser(BaseParser):
    """Парсер 2ГИС (API + HTML fallback)"""

    def __init__(self, config, city: str, category: str, max_pages: int = 3, mode: str = 'hybrid'):
        super().__init__(config)
        self.city = city
        self.category = category
        self.max_pages = max_pages
        self.mode = mode  # 'api', 'html', 'hybrid'

    def parse(self) -> List[GisItem]:
        logger.info(f"2ГИС: {self.city}, {self.category}, режим {self.mode}")

        if self.mode == 'api':
            self.results = self._parse_via_api()
        elif self.mode == 'html':
            self.results = self._parse_via_html()
        else:  # hybrid
            self.results = self._parse_via_api()
            if not self.results:
                logger.warning("API не сработал, переключаюсь на HTML")
                self.results = self._parse_via_html()

        return self.results

    def _parse_via_api(self) -> List[GisItem]:
        items = []
        for page in range(1, self.max_pages + 1):
            try:
                url = "https://catalog.api.2gis.ru/3.0/items"
                params = {
                    'q': self.category,
                    'city': self.city,
                    'page': page,
                    'page_size': 20,
                    'sort_point': '1',
                    'key': 'rujgbu0dav',  # публичный ключ (может устареть, но пока работает)
                }
                html = self._fetch_page(url, method="GET", params=params)
                if not html:
                    continue

                import json
                data = json.loads(html)
                if 'result' in data and 'items' in data['result']:
                    for org in data['result']['items']:
                        item = GisItem()
                        item.name = org.get('name', '')

                        phones = [p.get('formatted', '') for p in org.get('phones', [])]
                        item.phones = ', '.join(phones)

                        sites = [s.get('url', '') for s in org.get('sites', [])]
                        item.website = ', '.join(sites)

                        item.address = org.get('address_name', '')

                        items.append(item)
                logger.info(f"API страница {page}: загружено {len(data['result'].get('items', []))} орг.")
                self._random_delay(1, 2)

            except Exception as e:
                logger.error(f"Ошибка API на странице {page}: {e}")

        return items

    def _parse_via_html(self) -> List[GisItem]:
        items = []
        for page in range(1, self.max_pages + 1):
            try:
                url = f"https://2gis.ru/{self.city}/search/{self.category}/page/{page}"
                html = self._fetch_page(url)
                if not html:
                    continue

                soup = BeautifulSoup(html, 'lxml')
                cards = soup.find_all('div', {'class': '_1hfok3'})  # селектор может поменяться

                for card in cards:
                    item = GisItem()
                    name_elem = card.find('a', {'class': '_name'})
                    if name_elem:
                        item.name = name_elem.text.strip()

                    addr_elem = card.find('span', {'class': '_address'})
                    if addr_elem:
                        item.address = addr_elem.text.strip()

                    phone_elem = card.find('span', {'class': '_phone'})
                    if phone_elem:
                        item.phones = phone_elem.text.strip()

                    items.append(item)

                logger.info(f"HTML страница {page}: загружено {len(cards)} орг.")
                self._random_delay(3, 5)

            except Exception as e:
                logger.error(f"Ошибка HTML на странице {page}: {e}")

        return items