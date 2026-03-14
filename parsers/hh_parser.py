from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from loguru import logger
from .base_parser import BaseParser


class HHItem(BaseModel):
    name: str = Field(default='', description='Название вакансии')
    employer: str = Field(default='', description='Компания')
    salary: str = Field(default='', description='Зарплата')
    experience: str = Field(default='', description='Требуемый опыт')
    schedule: str = Field(default='', description='График')
    employment: str = Field(default='', description='Тип занятости')
    description: str = Field(default='', description='Описание (сниппет)')
    link: str = Field(default='', description='Ссылка на вакансию')


class HHParser(BaseParser):
    """Парсер HeadHunter через официальное API"""

    def __init__(self, config, search_text: str, area: int = 113, max_pages: int = 3):
        super().__init__(config)
        self.search_text = search_text
        self.area = area
        self.max_pages = max_pages

    def parse(self) -> List[HHItem]:
        logger.info(f"HeadHunter: '{self.search_text}', регион {self.area}, страниц: {self.max_pages}")

        for page in range(self.max_pages):
            try:
                url = "https://api.hh.ru/vacancies"
                params = {
                    'text': self.search_text,
                    'area': self.area,
                    'page': page,
                    'per_page': 20,
                }
                data = self._fetch_page(url, params=params)
                if not data:
                    break

                import json
                vacancies = json.loads(data)
                if 'items' not in vacancies:
                    break

                for vac in vacancies['items']:
                    item = HHItem()
                    item.name = vac.get('name', '')
                    item.employer = vac.get('employer', {}).get('name', '')
                    item.salary = self._parse_salary(vac.get('salary'))
                    item.link = vac.get('alternate_url', '')

                    if 'experience' in vac:
                        item.experience = vac['experience'].get('name', '')
                    if 'schedule' in vac:
                        item.schedule = vac['schedule'].get('name', '')
                    if 'employment' in vac:
                        item.employment = vac['employment'].get('name', '')

                    snippet = vac.get('snippet', {})
                    item.description = snippet.get('requirement', '') + '\n' + snippet.get('responsibility', '')

                    self.results.append(item)

                logger.info(f"Страница {page}: загружено {len(vacancies['items'])} вакансий")

                # Проверка, есть ли ещё страницы
                if page >= vacancies.get('pages', 0) - 1:
                    break

                self._random_delay(0.5, 1.0)  # hh просит не чаще 1 запроса в секунду

            except Exception as e:
                logger.error(f"Ошибка на странице {page}: {e}")
                break

        return self.results

    def _parse_salary(self, salary: Optional[Dict]) -> str:
        if not salary:
            return "не указана"
        fr = salary.get('from')
        to = salary.get('to')
        cur = salary.get('currency', 'rub')
        if fr and to:
            return f"{fr} - {to} {cur}"
        elif fr:
            return f"от {fr} {cur}"
        elif to:
            return f"до {to} {cur}"
        return "не указана"