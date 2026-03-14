"""
Автоматическая ротация прокси с тестированием рабочих IP
Основано на ProxyRotator библиотеке
"""

import asyncio
import random
from typing import List, Optional
from dataclasses import dataclass
import httpx
from loguru import logger


@dataclass
class Proxy:
    """Модель прокси"""
    url: str  # http://user:pass@ip:port или http://ip:port
    type: str  # http, https, socks5
    is_alive: bool = False
    response_time: float = 0.0
    country: str = ''


class ProxyRotator:
    """Ротатор прокси с автоматической проверкой"""

    def __init__(self, proxy_list: List[str], test_url: str = "https://httpbin.org/ip"):
        self.proxies = [Proxy(url=p, type='http') for p in proxy_list]
        self.test_url = test_url
        self.current_index = 0
        self.working_proxies: List[Proxy] = []

    async def test_proxy(self, proxy: Proxy) -> bool:
        """Проверка, работает ли прокси"""
        try:
            start = asyncio.get_event_loop().time()

            async with httpx.AsyncClient(
                    proxies=proxy.url,
                    timeout=10.0,
                    follow_redirects=True
            ) as client:
                response = await client.get(self.test_url)
                proxy.response_time = asyncio.get_event_loop().time() - start
                proxy.is_alive = response.status_code == 200

                # Пробуем определить страну
                try:
                    data = response.json()
                    if 'origin' in data:
                        logger.debug(f"Прокси {proxy.url[:20]}... IP: {data['origin']}")
                except:
                    pass

                return proxy.is_alive

        except Exception as e:
            logger.debug(f"Прокси {proxy.url[:20]}... не работает: {e}")
            proxy.is_alive = False
            return False

    async def test_all_proxies(self, concurrency: int = 10):
        """Тестирование всех прокси параллельно"""
        logger.info(f"Тестирование {len(self.proxies)} прокси...")

        # Разбиваем на порции для параллельной проверки
        tasks = []
        for proxy in self.proxies:
            tasks.append(self.test_proxy(proxy))

        results = await asyncio.gather(*tasks)

        # Оставляем только рабочие
        self.working_proxies = [p for p, alive in zip(self.proxies, results) if alive]
        logger.success(f"Найдено {len(self.working_proxies)} рабочих прокси")

        # Сортируем по скорости ответа
        self.working_proxies.sort(key=lambda x: x.response_time)
        return self.working_proxies

    def get_next_proxy(self) -> Optional[Proxy]:
        """Получение следующего рабочего прокси (round-robin)"""
        if not self.working_proxies:
            return None

        proxy = self.working_proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.working_proxies)
        return proxy

    def get_random_proxy(self) -> Optional[Proxy]:
        """Случайный прокси"""
        if not self.working_proxies:
            return None
        return random.choice(self.working_proxies)


# Пример использования
async def main():
    # Список прокси из .env или файла
    proxy_list = [
        "http://user:pass@123.45.67.89:8080",
        "http://111.222.333.444:8080",
    ]

    rotator = ProxyRotator(proxy_list)

    # Тестируем все прокси
    working = await rotator.test_all_proxies()

    if working:
        # Берём прокси по очереди
        for _ in range(5):
            proxy = rotator.get_next_proxy()
            if proxy:
                logger.info(f"Использую прокси: {proxy.url[:30]}..., время ответа: {proxy.response_time:.2f}с")

                # Делаем запрос через прокси
                async with httpx.AsyncClient(proxies=proxy.url) as client:
                    resp = await client.get("https://httpbin.org/ip")
                    print(resp.json())


if __name__ == "__main__":
    asyncio.run(main())