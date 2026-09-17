import asyncio
import logging
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup
from crawler.robots import RobotsChecker
from crawler.auth import AuthHandler

logger = logging.getLogger(__name__)

class WebsitePreviewAnalyzer:
    def __init__(self, user_agent: str = None):
        default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self.user_agent = user_agent or default_ua
        if "RAGFlow" in self.user_agent:
            self.user_agent = default_ua
        self.robots_checker = RobotsChecker(self.user_agent)

    def _clean_url(self, u: str) -> str:
        if not u or not isinstance(u, str):
            return ""
        u = u.strip()
        if not u:
            return ""
        if not (u.startswith("http://") or u.startswith("https://")):
            u = "https://" + u
        return u.split("#")[0].strip()

    async def analyze(self, start_url: str, crawl_mode: str = "website", max_pages: int = 50, auth_config: dict = None) -> dict:
        start_url = self._clean_url(start_url)
        if not start_url:
            return {"title": "Website Dataset", "detected_pages": 0, "estimated_token_count": 0, "estimated_chunks": 0}

        auth_handler = AuthHandler(auth_config)
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
        }
        headers.update(auth_handler.get_headers())
        cookies = auth_handler.get_cookies()

        parsed_start = urlparse(start_url)
        base_domain = parsed_start.netloc.lower().removeprefix("www.")

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
        conn = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=15, connect=8)

        async with aiohttp.ClientSession(headers=headers, cookies=cookies, connector=conn, timeout=timeout) as session:
            while queue and len(visited) < min(max_pages, 20):
                url = self._clean_url(queue.pop(0))
                if not url or url in visited:
                    continue
                visited.add(url)

                try:
                    async with session.get(url, allow_redirects=True) as resp:
                        if resp.status != 200:
                            continue
                        content_type = resp.headers.get("Content-Type", "").lower()
                        if "text/html" not in content_type and "application/xhtml" not in content_type:
                            if "pdf" in content_type:
                                result["detected_pdfs"] += 1
                            continue

                        try:
                            html = await resp.text()
                        except UnicodeDecodeError:
                            raw = await resp.read()
                            html = raw.decode("utf-8", errors="replace")

                        soup = BeautifulSoup(html, 'html.parser')

                        if not result["title"]:
                            t = soup.find('title')
                            title_text = t.get_text(strip=True) if t else ""
                            result["title"] = title_text or parsed_start.netloc or start_url

                        # Count text tokens estimation (1 token ~= 4 chars)
                        text = soup.get_text()
                        result["estimated_token_count"] += len(text) // 4
                        result["detected_images"] += len(soup.find_all('img'))

                        # Extract internal links if crawling mode is not single_page
                        if crawl_mode != "single_page":
                            for a in soup.find_all('a', href=True):
                                href = a['href'].strip()
                                if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#', 'data:')):
                                    continue
                                full_href = self._clean_url(urljoin(url, href))
                                p = urlparse(full_href)
                                next_domain = p.netloc.lower().removeprefix("www.")
                                if next_domain == base_domain and full_href not in visited and full_href not in queue:
                                    queue.append(full_href)

                except Exception as e:
                    logger.debug(f"Preview fetch error on {url}: {e}")

        if not result["title"]:
            result["title"] = parsed_start.netloc or "Website Dataset"
        result["detected_pages"] = max(1, len(visited))
        result["estimated_token_count"] = max(200, result["estimated_token_count"])
        result["estimated_chunks"] = max(1, result["estimated_token_count"] // 500)
        result["estimated_embedding_cost"] = round((result["estimated_token_count"] / 1000) * 0.0001, 5)
        result["estimated_crawl_time_seconds"] = max(2, len(visited) * 1)

        return result
