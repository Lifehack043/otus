"""
Асинхронный краулер для Hacker News (news.ycombinator.com).

Краулер запускается каждые N секунд, парсит топ новостей,
сохраняет каждую новость и все ссылки из обсуждения.
"""

import asyncio
import json
import logging
import os
import re
import ssl
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Union
from urllib.parse import urljoin

import aiohttp
from bs4 import BeautifulSoup

# Флаг для отключения проверки SSL (fallback при проблемах с сертификатами)
_SSL_WARNING_SHOWN = False


def _create_ssl_context() -> Union[ssl.SSLContext, bool]:
    """Создаёт SSL-контекст, пробуя разные стратегии."""
    global _SSL_WARNING_SHOWN

    # Стратегия 1: certifi
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
        # Проверяем, что контекст действительно работает
        import socket
        with socket.create_connection("news.ycombinator.com", 443) as sock:
            with ctx.wrap_socket(sock, server_hostname="news.ycombinator.com"):
                return ctx
    except Exception:
        pass

    # Стратегия 2: системные сертификаты
    try:
        ctx = ssl.create_default_context()
        import socket
        with socket.create_connection("news.ycombinator.com", 443) as sock:
            with ctx.wrap_socket(sock, server_hostname="news.ycombinator.com"):
                return ctx
    except Exception:
        pass

    # Стратегия 3: не проверенный контекст (fallback)
    if not _SSL_WARNING_SHOWN:
        _SSL_WARNING_SHOWN = True
        logger.warning(
            "Не удалось проверить SSL-сертификат — используется не проверенный контекст. "
            "Для исправления на macOS выполните: "
            "/Applications/Python\\ 3.x/Install\\ Certificates.command "
            "или pip install --upgrade certifi"
        )
    return ssl._create_unverified_context()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Конфигурация
BASE_URL = "https://news.ycombinator.com"
INTERVAL_SECONDS = int(os.environ.get("CRAWL_INTERVAL", "60"))
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "./data"))
MAX_RETRIES = 3
REQUEST_TIMEOUT = 30


class NewsItem:
    """Представляет одну новость с Hacker News."""

    def __init__(
        self,
        title: str,
        url: str | None = None,
        score: str = "",
        author: str = "",
        time: str = "",
        comment_count: str = "",
        discussion_url: str = "",
        links: list[str] | None = None,
    ) -> None:
        self.title = title
        self.url = url
        self.score = score
        self.author = author
        self.time = time
        self.comment_count = comment_count
        self.discussion_url = discussion_url
        self.links = links or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "score": self.score,
            "author": self.author,
            "time": self.time,
            "comment_count": self.comment_count,
            "discussion_url": self.discussion_url,
            "links": self.links,
        }


class HackerNewsCrawler:
    """Асинхронный краулер для news.ycombinator.com."""

    def __init__(self) -> None:
        self.session: aiohttp.ClientSession | None = None
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            ssl_context = _create_ssl_context()
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    )
                },
            )
        return self.session

    async def fetch_page(self, url: str) -> str | None:
        """Асинхронно получает содержимое страницы с повторными попытками."""
        session = await self._get_session()
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.text()
                    logger.warning(
                        "HTTP %s для %s (попытка %d/%d)",
                        response.status,
                        url,
                        attempt,
                        MAX_RETRIES,
                    )
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.warning("Ошибка при запросе %s (попытка %d/%d): %s", url, attempt, MAX_RETRIES, e)
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(2**attempt)  # экспоненциальная задержка
        logger.error("Не удалось получить %s после %d попыток", url, MAX_RETRIES)
        return None

    async def parse_main_page(self) -> list[NewsItem]:
        """Парсит главную страницу и возвращает список топ новостей."""
        html = await self.fetch_page(BASE_URL)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        news_items: list[NewsItem] = []

        # Находим все строки с новостями (<tr class="athing">)
        news_rows = soup.find_all("tr", attrs={"class": "athing"})
        for row in news_rows:
            item = self._parse_news_row(row)
            if item:
                news_items.append(item)

        logger.info("Найдено %d новостей на главной странице", len(news_items))
        return news_items

    def _parse_news_row(self, row: BeautifulSoup) -> NewsItem | None:
        """Парсит отдельный <tr> с новостью."""
        # Находим span.titleline внутри td.title
        title_span = row.find("span", attrs={"class": "titleline"})
        if not title_span:
            return None

        title_link = title_span.find("a")
        if not title_link:
            return None

        title = title_link.get_text(strip=True)
        url = title_link.get("href", "")

        # Проверяем, что это новость (а не комментарий или другое)
        if not url or not url.startswith("http"):
            return None

        # Находим следующую строку (<tr>) с метаданными (subline)
        score = ""
        author = ""
        time_str = ""
        comment_count = ""
        discussion_url = ""

        next_row = row.find_next_sibling("tr")
        if next_row:
            subline = next_row.find("span", attrs={"class": "subline"})
            if subline:
                # Score
                score_span = subline.find("span", attrs={"class": "score"})
                if score_span:
                    score_text = score_span.get_text(strip=True)
                    score_match = re.search(r"(\d+)\s+points?", score_text)
                    if score_match:
                        score = score_match.group(1)

                # Автор
                author_link = subline.find("a", attrs={"class": "hnuser"})
                if author_link:
                    author = author_link.get_text(strip=True)

                # Время
                age_span = subline.find("span", attrs={"class": "age"})
                if age_span:
                    time_str = age_span.get("title", "")

                # Ссылки item?id=: первая в span.age — это время обсуждения,
                # вторая (вне span.age) — количество комментариев
                item_links = subline.find_all("a", href=True)
                for link in item_links:
                    href = link["href"]
                    if href.startswith("item?id="):
                        discussion_url = urljoin(BASE_URL, href)
                        text = link.get_text(strip=True)
                        # Если ссылка НЕ внутри span.age — это комментарии
                        parent_age = link.find_parent("span", attrs={"class": "age"})
                        if not parent_age:
                            comment_count = text

        return NewsItem(
            title=title,
            url=url,
            score=score,
            author=author,
            time=time_str,
            comment_count=comment_count,
            discussion_url=discussion_url,
        )

    async def parse_discussion(self, discussion_url: str) -> list[str]:
        """Парсит страницу обсуждения и извлекает все уникальные ссылки."""
        html = await self.fetch_page(discussion_url)
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        links_set: set[str] = set()

        # Ищем все ссылки в комментариях
        for tag in soup.find_all("a", href=True):
            href = tag["href"]
            # Фильтруем только внешние HTTP(S) ссылки
            if href.startswith(("http://", "https://")):
                links_set.add(href)

        links = sorted(links_set)
        logger.debug("Найдено %d ссылок в обсуждении %s", len(links), discussion_url)
        return links

    async def crawl_once(self) -> list[NewsItem]:
        """Выполняет один цикл краulin'а: парсит новости и их обсуждения."""
        logger.info("Начало цикла краulin'а...")

        # Парсим главную страницу
        news_items = await self.parse_main_page()

        # Для каждой новости параллельно парсим обсуждение
        async def enrich_news(item: NewsItem) -> NewsItem:
            if item.discussion_url:
                item.links = await self.parse_discussion(item.discussion_url)
            return item

        # Парсим обсуждения параллельно
        tasks = [enrich_news(item) for item in news_items]
        enriched_items = await asyncio.gather(*tasks)

        logger.info("Цикл краulin'а завершён. Обработано %d новостей.", len(enriched_items))
        return list(enriched_items)

    def save_results(self, news_items: list[NewsItem]) -> str:
        """Сохраняет результаты в JSON файл с timestamp в имени."""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = OUTPUT_DIR / f"hackernews_{timestamp}.json"

        result = {
            "crawl_time": datetime.now(timezone.utc).isoformat(),
            "source": BASE_URL,
            "total_news": len(news_items),
            "news": [item.to_dict() for item in news_items],
        }

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        logger.info("Результаты сохранены в %s", filename)
        return str(filename)

    async def run_cycle(self) -> str:
        """Запускает один полный цикл: краулинг + сохранение."""
        news_items = await self.crawl_once()
        if news_items:
            return self.save_results(news_items)
        logger.warning("Новости не найдены")
        return ""

    async def close(self) -> None:
        """Закрывает HTTP сессию."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def run_periodically(self) -> None:
        """Запускает краулер периодически каждые INTERVAL_SECONDS секунд."""
        logger.info("Краулер запущен. Интервал: %d сек.", INTERVAL_SECONDS)
        logger.info("Результаты сохраняются в: %s", OUTPUT_DIR)
        logger.info("Нажмите Ctrl+C для остановки.")

        try:
            while True:
                await self.run_cycle()
                await asyncio.sleep(INTERVAL_SECONDS)
        except KeyboardInterrupt:
            logger.info("Краулер остановлен пользователем.")
        finally:
            await self.close()


async def main() -> None:
    """Точка входа."""
    crawler = HackerNewsCrawler()

    # Если передан аргумент --once, выполняем один цикл
    import sys
    if "--once" in sys.argv:
        await crawler.run_cycle()
        await crawler.close()
    else:
        await crawler.run_periodically()


if __name__ == "__main__":
    asyncio.run(main())
