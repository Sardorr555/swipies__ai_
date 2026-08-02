import asyncio
import logging
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
from crawler.robots import RobotsChecker
from crawler.auth import AuthHandler

logger = logging.getLogger(__name__)

class WebsitePreviewAnalyzer:
    def __init__(self, user_agent: str = "RAGFlow-WebCrawler/1.0"):
        self.user_agent = user_agent
        self.robots_checker = RobotsChecker(user_agent)

    async def analyze(self, start_url: str, crawl_mode: str = "website", max_pages: int = 50, auth_config: dict = None) -> dict:
        auth_handler = AuthHandler(auth_config)
        headers = {"User-Agent": self.user_agent}
        headers.update(auth_handler.get_headers())
        cookies = auth_handler.get_cookies()

        result = {
            "title": "",
            "detected_pages": 0,
            "estimated_token_count": 0,
            "estimated_chunks": 0,
            "detected_language": "en",
            "detected_pdfs": 0,
            "detected_images": 0,
            "estimated_embedding_cost": 0.0,
            "estimated_crawl_time_seconds": 0
        }

        visited = set()
        queue = [start_url]
        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc

        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            while queue and len(visited) < min(max_pages, 20):
                url = queue.pop(0)
                if url in visited:
                    continue
                visited.add(url)

                try:
                    async with session.get(url, timeout=10) as resp:
                        if resp.status != 200:
                            continue
                        content_type = resp.headers.get("Content-Type", "")
                        if "text/html" not in content_type:
                            if "pdf" in content_type:
                                result["detected_pdfs"] += 1
                            continue

                        html = await resp.text()
                        soup = BeautifulSoup(html, 'html.parser')

                        if not result["title"]:
                            t = soup.find('title')
                            result["title"] = t.get_text(strip=True) if t else start_url

                        # Count text tokens estimation (1 token ~= 4 chars)
                        text = soup.get_text()
                        result["estimated_token_count"] += len(text) // 4
                        result["detected_images"] += len(soup.find_all('img'))

                        # Extract internal links if crawling mode is not single_page
                        if crawl_mode != "single_page":
                            for a in soup.find_all('a', href=True):
                                href = urljoin(url, a['href'])
                                p = urlparse(href)
                                if p.netloc == base_domain and href not in visited and href not in queue:
                                    queue.append(href)

                except Exception as e:
                    logger.debug(f"Preview fetch error on {url}: {e}")

        result["detected_pages"] = len(visited)
        result["estimated_chunks"] = max(1, result["estimated_token_count"] // 500)
        # $0.0001 per 1k tokens standard embedding estimate
        result["estimated_embedding_cost"] = round((result["estimated_token_count"] / 1000) * 0.0001, 5)
        result["estimated_crawl_time_seconds"] = max(2, len(visited) * 1)

        return result
