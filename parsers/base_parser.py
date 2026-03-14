import abc
import json
import random
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
import httpx
import pandas as pd
from fake_useragent import UserAgent
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pydantic import BaseModel


class BaseParser(abc.ABC):
    """Абстрактный базовый парсер со всей инфраструктурой"""

    def __init__(self, config: Any):
        self.config = config
        self.ua = UserAgent()
        self.session = self._create_session()
        self.results: List[BaseModel] = []

    def _create_session(self) -> httpx.Client:
        """Создаёт HTTPX сессию с поддержкой прокси и HTTP/2"""
        client_args = {
            'timeout': 30,
            'follow_redirects': True,
            'http2': True,
        }
        if self.config.PROXY_URL:
            client_args['proxies'] = self.config.PROXY_URL
        elif self.config.PROXY_LIST:
            # Рандомный прокси из списка
            proxy = random.choice(self.config.PROXY_LIST)
            client_args['proxies'] = proxy
            logger.info(f"Использую прокси: {proxy[:20]}...")
        return httpx.Client(**client_args)

    def _get_headers(self) -> Dict[str, str]:
        """Генерирует случайные заголовки как у реального браузера"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.TimeoutException, httpx.ConnectError))
    )
    def _fetch_page(self, url: str, method: str = "GET", **kwargs) -> Optional[str]:
        """Загружает страницу с повторными попытками"""
        try:
            headers = self._get_headers()
            if 'headers' in kwargs:
                headers.update(kwargs.pop('headers'))

            logger.debug(f"Загрузка: {url}")
            response = self.session.request(method, url, headers=headers, **kwargs)

            if response.status_code == 429:
                logger.warning("Слишком много запросов (429), жду 60 сек...")
                time.sleep(60)
                raise httpx.HTTPStatusError("Rate limited", request=response.request, response=response)
            elif response.status_code in (403, 404):
                logger.error(f"Доступ запрещён {response.status_code} – возможно заблокирован IP")
                # Пробуем сменить прокси, если есть список
                if self.config.PROXY_LIST:
                    logger.info("Смена прокси...")
                    self.session = self._create_session()
                    raise httpx.HTTPStatusError("Forbidden", request=response.request, response=response)
                else:
                    return None

            response.raise_for_status()
            return response.text

        except Exception as e:
            logger.error(f"Ошибка загрузки {url}: {e}")
            raise

    def _random_delay(self, min_delay: float = 2.0, max_delay: float = 5.0):
        """Случайная задержка между запросами"""
        delay = random.uniform(min_delay, max_delay)
        logger.debug(f"Задержка {delay:.2f} сек")
        time.sleep(delay)

    @abc.abstractmethod
    def parse(self, *args, **kwargs) -> List[BaseModel]:
        """Основной метод парсинга, должен быть реализован в наследнике"""
        pass

    def save_results(self, filename: str, format: str = "excel", fields: Optional[List[str]] = None):
        """Сохраняет результаты в нужном формате"""
        if not self.results:
            logger.warning("Нет данных для сохранения")
            return

        # Преобразуем Pydantic модели в словари
        data = [item.model_dump() for item in self.results]

        # Фильтрация полей
        if fields and fields != ['*']:
            data = [{k: v for k, v in item.items() if k in fields} for item in data]

        # Создаём папку output, если её нет
        output_dir = Path(self.config.OUTPUT_DIR)
        output_dir.mkdir(exist_ok=True)

        full_path = output_dir / filename

        if format == "excel":
            pd.DataFrame(data).to_excel(full_path.with_suffix(".xlsx"), index=False)
            logger.success(f"Сохранено в Excel: {full_path.with_suffix('.xlsx')}")
        elif format == "csv":
            pd.DataFrame(data).to_csv(full_path.with_suffix(".csv"), index=False, encoding='utf-8-sig')
            logger.success(f"Сохранено в CSV: {full_path.with_suffix('.csv')}")
        elif format == "json":
            with open(full_path.with_suffix(".json"), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.success(f"Сохранено в JSON: {full_path.with_suffix('.json')}")
        elif format == "html":
            html = self._to_html(data)
            with open(full_path.with_suffix(".html"), 'w', encoding='utf-8') as f:
                f.write(html)
            logger.success(f"Сохранено в HTML: {full_path.with_suffix('.html')}")
        else:
            logger.error(f"Неизвестный формат: {format}")

    def _to_html(self, data: List[Dict]) -> str:
        """Генерирует простую HTML-таблицу из данных"""
        if not data:
            return "<html><body>Нет данных</body></html>"

        html = "<html><head><meta charset='utf-8'></head><body><table border='1'>"
        # Заголовки
        html += "<tr>" + "".join([f"<th>{k}</th>" for k in data[0].keys()]) + "</tr>"
        # Строки
        for row in data:
            html += "<tr>" + "".join([f"<td>{v}</td>" for v in row.values()]) + "</tr>"
        html += "</table></body></html>"
        return html