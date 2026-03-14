import json
from typing import List
from pydantic import BaseModel, Field
from loguru import logger
from .base_parser import BaseParser


class YandexItem(BaseModel):
    name: str = Field(default='', description='Название организации')
    category: str = Field(default='', description='Категория')
    address: str = Field(default='', description='Адрес')
    phones: str = Field(default='', description='Телефоны')
    website: str = Field(default='', description='Сайт')
    rating: float = Field(default=0.0, description='Рейтинг')
    reviews_count: int = Field(default=0, description='Количество отзывов')
    working_hours: str = Field(default='', description='Режим работы')
    link: str = Field(default='', description='Ссылка на картах')


class YandexParser(BaseParser):
    """Парсер Яндекс Карт (работает через API поиска и внутренние запросы)"""

    def __init__(self, config, search_query: str, city: str = "москва", max_pages: int = 3):
        super().__init__(config)
        self.search_query = search_query
        self.city = city
        self.max_pages = max_pages

    def parse(self) -> List[YandexItem]:
        logger.info(f"Яндекс.Карты: '{self.search_query}' в городе '{self.city}', страниц: {self.max_pages}")

        all_items = []

        for page in range(self.max_pages):
            try:
                # Яндекс использует внутреннее API для поиска организаций
                url = "https://search-maps.yandex.ru/v1/"
                params = {
                    'text': f"{self.search_query}, {self.city}",
                    'type': 'biz',
                    'lang': 'ru_RU',
                    'results': 50,  # максимум на страницу
                    'skip': page * 50,
                    'apikey': self._get_api_key()  # ключ в настройках
                }

                # Для Яндекса обязательно нужно ставить нормальные заголовки
                headers = {
                    **self._get_headers(),
                    'Referer': 'https://yandex.ru/maps',
                    'Origin': 'https://yandex.ru'
                }

                html = self._fetch_page(url, params=params, headers=headers)
                if not html:
                    continue

                data = json.loads(html)

                if 'features' not in data:
                    logger.warning(f"Нет данных на странице {page}")
                    break

                for feature in data['features']:
                    try:
                        props = feature.get('properties', {})
                        company_meta = props.get('CompanyMetaData', {})

                        item = YandexItem()
                        item.name = company_meta.get('name', '')
                        item.address = company_meta.get('address', '')
                        item.category = company_meta.get('rubric', {}).get('name', '')

                        # Телефоны
                        phones = []
                        for phone in company_meta.get('Phones', []):
                            if 'formatted' in phone:
                                phones.append(phone['formatted'])
                        item.phones = ', '.join(phones)

                        item.website = company_meta.get('url', '')
                        item.rating = company_meta.get('rating', 0.0)
                        item.reviews_count = company_meta.get('reviewsCount', 0)

                        # Ссылка на картах
                        if 'id' in props:
                            item.link = f"https://yandex.ru/maps/org/{props['id']}"

                        all_items.append(item)

                    except Exception as e:
                        logger.warning(f"Ошибка парсинга организации: {e}")
                        continue

                logger.info(f"Страница {page}: загружено {len(data.get('features', []))} организаций")

                # Яндекс жёстко банит, задержка обязательна
                self._random_delay(min_delay=3.0, max_delay=7.0)

            except Exception as e:
                logger.error(f"Ошибка на странице {page}: {e}")
                break

        self.results = all_items
        return all_items

    def _get_api_key(self) -> str:
        """Получение API ключа Яндекс.Карт (из .env)"""
        # Стандартный бесплатный ключ для тестирования
        # В продакшене нужно получить свой на https://developer.tech.yandex.ru/
        return getattr(self.config, 'YANDEX_API_KEY', 'test_key_123')