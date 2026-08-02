import asyncio
import ipaddress
import logging
from urllib.parse import urljoin, urlparse
import aiohttp
from bs4 import BeautifulSoup

from crawler.robots import RobotsChecker
from crawler.cleaner import HTMLCleaner
from crawler.markdown import MarkdownConverter
from crawler.extractor import MetadataExtractor
from crawler.deduplicator import Deduplicator
from crawler.auth import AuthHandler

logger = logging.getLogger(__name__)

# Private subnet IP ranges to block SSRF
PRIVATE_SUBNETS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
]

def is_private_ip(hostname: str) -> bool:
    if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        ip = ipaddress.ip_address(hostname)
        return any(ip in net for net in PRIVATE_SUBNETS)
    except ValueError:
        return False

class AsyncWebCrawler:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.user_agent = self.config.get("user_agent", "RAGFlow-WebCrawler/1.0")
        self.crawl_mode = self.config.get("crawl_mode", "website")
        self.max_pages = self.config.get("max_pages", 100)
        self.max_depth = self.config.get("max_depth", 3)
        self.delay = self.config.get("delay", 0.5)
        self.respect_robots = self.config.get("respect_robots", True)
        self.use_js = self.config.get("js_rendering", False)

        self.robots_checker = RobotsChecker(self.user_agent)
        self.cleaner = HTMLCleaner(self.config)
        self.markdown_converter = MarkdownConverter(extract_images=self.config.get("extract_images", True))
        self.deduplicator = Deduplicator()
        self.auth_handler = AuthHandler(self.config.get("auth"))

        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    async def crawl(self, start_urls: list, progress_callback=None) -> list:
        results = []
        queue = []
        for url in start_urls:
            queue.append({"url": url, "depth": 0, "parent": ""})

        visited = set()
        headers = {"User-Agent": self.user_agent}
        headers.update(self.auth_handler.get_headers())
        cookies = self.auth_handler.get_cookies()

        async with aiohttp.ClientSession(headers=headers, cookies=cookies) as session:
            while queue and len(results) < self.max_pages and not self.cancelled:
                item = queue.pop(0)
                url = item["url"]
                depth = item["depth"]

                if url in visited or depth > self.max_depth:
                    continue
                visited.add(url)

                parsed = urlparse(url)
                if is_private_ip(parsed.hostname or ""):
                    logger.warning(f"Blocked SSRF attempt to private IP: {url}")
                    continue

                if not await self.robots_checker.can_fetch(url, self.respect_robots):
                    logger.info(f"Skipping {url} due to robots.txt restriction")
                    continue

                if self.deduplicator.is_duplicate_url(url):
                    continue

                try:
                    if progress_callback:
                        await progress_callback(url, len(results), self.max_pages)

                    html_content = ""
                    status_code = 200

                    if self.use_js:
                        html_content, status_code = await self._fetch_with_playwright(url)
                    
                    if not html_content:
                        async with session.get(url, timeout=15) as resp:
                            status_code = resp.status
                            if resp.status != 200:
                                continue
                            content_type = resp.headers.get("Content-Type", "")
                            if "text/html" not in content_type:
                                continue
                            html_content = await resp.text()

                    if not html_content:
                        continue

                    # Extract metadata
                    extractor = MetadataExtractor(url)
                    extracted_meta = extractor.extract(html_content, url)

                    # Clean HTML and convert to Markdown
                    cleaned_html = self.cleaner.clean(html_content)
                    markdown_text = self.markdown_converter.convert(cleaned_html)

                    # Deduplication check
                    if self.deduplicator.is_duplicate_content(markdown_text):
                        continue

                    page_result = {
                        "url": url,
                        "canonical_url": extracted_meta["canonical_url"],
                        "title": extracted_meta["title"],
                        "html": cleaned_html,
                        "markdown": markdown_text,
                        "metadata": extracted_meta,
                        "depth": depth,
                        "http_status": status_code
                    }
                    results.append(page_result)

                    # Discover next links if allowed by crawl_mode
                    if self.crawl_mode in ["website", "recursive"] and depth < self.max_depth:
                        soup = BeautifulSoup(html_content, 'html.parser')
                        for a in soup.find_all('a', href=True):
                            next_url = urljoin(url, a['href'])
                            p_next = urlparse(next_url)
                            if p_next.netloc == parsed.netloc and next_url not in visited:
                                queue.append({"url": next_url, "depth": depth + 1, "parent": url})

                    if self.delay > 0:
                        await asyncio.sleep(self.delay)

                except Exception as e:
                    logger.error(f"Error crawling {url}: {e}")

        return results

    async def _fetch_with_playwright(self, url: str) -> tuple:
        try:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(user_agent=self.user_agent)
                page = await context.new_page()
                resp = await page.goto(url, wait_until="networkidle", timeout=30000)
                status = resp.status if resp else 200
                content = await page.content()
                await browser.close()
                return content, status
        except Exception as e:
            logger.warning(f"Playwright rendering fallback to static fetch for {url}: {e}")
            return "", 0
