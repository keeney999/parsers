import asyncio
from typing import List
from pathlib import Path
from pydantic import BaseModel, Field
from loguru import logger
from telethon import TelegramClient
from telethon.tl.types import Message
from .base_parser import BaseParser


class TGPost(BaseModel):
    channel: str = Field(default='', description='Канал')
    date: str = Field(default='', description='Дата')
    text: str = Field(default='', description='Текст')
    views: int = Field(default=0, description='Просмотры')
    forwards: int = Field(default=0, description='Пересылки')
    replies: int = Field(default=0, description='Ответы')
    link: str = Field(default='', description='Ссылка')
    has_media: bool = Field(default=False, description='Есть медиа')
    media_path: str = Field(default='', description='Путь к скачанному медиа')


class TGParser(BaseParser):
    """Парсер Telegram каналов через Telethon"""

    def __init__(self, config, channels: List[str], limit: int = 50, download_media: bool = False):
        super().__init__(config)
        self.channels = channels
        self.limit = limit
        self.download_media = download_media
        self.client = None

    def parse(self) -> List[TGPost]:
        logger.info(f"Telegram: каналы {self.channels}, лимит {self.limit}")
        asyncio.run(self._async_parse())
        return self.results

    async def _async_parse(self):
        # Проверяем наличие API данных
        if not self.config.TG_API_ID or not self.config.TG_API_HASH or not self.config.TG_PHONE:
            logger.error("Не заданы TG_API_ID, TG_API_HASH или TG_PHONE в конфиге")
            return

        self.client = TelegramClient(
            'session/telegram_session',
            self.config.TG_API_ID,
            self.config.TG_API_HASH
        )

        await self.client.start(phone=self.config.TG_PHONE)
        logger.info("Клиент Telegram запущен")

        for channel in self.channels:
            try:
                entity = await self.client.get_entity(channel)
                posts = []

                async for msg in self.client.iter_messages(entity, limit=self.limit):
                    if not msg.text and not msg.media:
                        continue

                    post = TGPost()
                    post.channel = channel
                    post.date = msg.date.strftime('%Y-%m-%d %H:%M:%S')
                    post.text = msg.text or ''
                    post.views = getattr(msg, 'views', 0)
                    post.forwards = getattr(msg, 'forwards', 0)

                    if msg.replies:
                        post.replies = msg.replies.replies

                    post.link = f"https://t.me/{channel}/{msg.id}"
                    post.has_media = msg.media is not None

                    if self.download_media and msg.media:
                        media_dir = Path(self.config.OUTPUT_DIR) / 'telegram_media' / channel
                        media_dir.mkdir(parents=True, exist_ok=True)
                        try:
                            path = await msg.download_media(file=str(media_dir))
                            post.media_path = str(path)
                        except Exception as e:
                            logger.error(f"Ошибка скачивания медиа: {e}")

                    posts.append(post)

                self.results.extend(posts)
                logger.info(f"Канал {channel}: собрано {len(posts)} постов")

            except Exception as e:
                logger.error(f"Ошибка при обработке канала {channel}: {e}")

        await self.client.disconnect()