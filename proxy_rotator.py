import asyncio
import random
from typing import List, Optional
from dataclasses import dataclass
import httpx
from loguru import logger

@dataclass
class Proxy:
    url: str
    is_alive: bool = False
    response_time: float = 0.0

class ProxyRotator:
    def __init__(self, proxy_list: List[str], test_url: str = "https://httpbin.org/ip"):
        self.proxies = [Proxy(url=p) for p in proxy_list]
        self.test_url = test_url
        self.working_proxies: List[Proxy] = []
        self.current_index = 0

    async def test_proxy(self, proxy: Proxy) -> bool:
        try:
            start = asyncio.get_event_loop().time()
            # Правильный способ передачи прокси в httpx
            async with httpx.AsyncClient(
                proxies={"http://": proxy.url, "https://": proxy.url},
                timeout=10.0,
                follow_redirects=True
            ) as client:
                resp = await client.get(self.test_url)
                proxy.response_time = asyncio.get_event_loop().time() - start
                proxy.is_alive = resp.status_code == 200
                return proxy.is_alive
        except Exception as e:
            logger.debug(f"Прокси {proxy.url[:30]}... не работает: {e}")
            proxy.is_alive = False
            return False

    async def test_all_proxies(self, concurrency: int = 10):
        logger.info(f"Тестирование {len(self.proxies)} прокси...")
        tasks = [self.test_proxy(p) for p in self.proxies]
        results = await asyncio.gather(*tasks)
        self.working_proxies = [p for p, alive in zip(self.proxies, results) if alive]
        self.working_proxies.sort(key=lambda x: x.response_time)
        logger.success(f"Найдено {len(self.working_proxies)} рабочих прокси")
        return self.working_proxies

    def get_next_proxy(self) -> Optional[Proxy]:
        if not self.working_proxies:
            return None
        proxy = self.working_proxies[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.working_proxies)
        return proxy

    def get_random_proxy(self) -> Optional[Proxy]:
        if not self.working_proxies:
            return None
        return random.choice(self.working_proxies)

async def main():
    # Тестовые прокси (замени на свои)
    test_proxies = [
        "http://user:pass@123.45.67.89:8080",
        "http://111.222.333.444:8080"
    ]
    rotator = ProxyRotator(test_proxies)
    working = await rotator.test_all_proxies()
    if working:
        proxy = rotator.get_next_proxy()
        logger.info(f"Рабочий прокси: {proxy.url[:30]}..., время {proxy.response_time:.2f}с")
    else:
        logger.warning("Нет рабочих прокси")

if __name__ == "__main__":
    asyncio.run(main())