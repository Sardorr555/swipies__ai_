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
        default_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        self.user_agent = self.config.get("user_agent") or default_ua
        if "RAGFlow" in self.user_agent:
            self.user_agent = default_ua
        self.crawl_mode = self.config.get("crawl_mode", "website")
        self.max_pages = min(int(self.config.get("max_pages", 100)), 500)
        self.max_depth = min(int(self.config.get("max_depth", 3)), 10)
        self.delay = float(self.config.get("delay", 0.3))
        self.respect_robots = bool(self.config.get("respect_robots", False))
        self.use_js = bool(self.config.get("js_rendering", False))

        self.robots_checker = RobotsChecker(self.user_agent)
        self.cleaner = HTMLCleaner(self.config)
        self.markdown_converter = MarkdownConverter(extract_images=self.config.get("extract_images", True))
        self.deduplicator = Deduplicator()
        self.auth_handler = AuthHandler(self.config.get("auth"))

        self.cancelled = False

    def cancel(self):
        self.cancelled = True

    def _clean_url(self, u: str) -> str:
        if not u or not isinstance(u, str):
            return ""
        u = u.strip()
        if not u:
            return ""
        if not (u.startswith("http://") or u.startswith("https://")):
            u = "https://" + u
        # Strip trailing fragment and unwanted trailing slash
        u = u.split("#")[0].strip()
        return u

    async def crawl(self, start_urls: list, progress_callback=None) -> list:
        results = []
        queue = []
        visited = set()

        for raw_url in start_urls:
            cleaned = self._clean_url(raw_url)
            if cleaned:
                queue.append({"url": cleaned, "depth": 0, "parent": ""})

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
        }
        headers.update(self.auth_handler.get_headers())
        cookies = self.auth_handler.get_cookies()

        conn = aiohttp.TCPConnector(ssl=False)
        timeout = aiohttp.ClientTimeout(total=20, connect=10)

        async with aiohttp.ClientSession(headers=headers, cookies=cookies, connector=conn, timeout=timeout) as session:
            # If sitemap mode, inspect first URL for sitemap xml
            if self.crawl_mode == "sitemap" and queue:
                sitemap_item = queue[0]
                s_url = sitemap_item["url"]
                if not s_url.endswith(".xml") and "sitemap" not in s_url.lower():
                    s_url = urljoin(s_url, "/sitemap.xml")
                try:
                    async with session.get(s_url) as s_resp:
                        if s_resp.status == 200:
                            s_text = await s_resp.text()
                            locs = re.findall(r'<loc>\s*(https?://[^<\s]+)\s*</loc>', s_text, re.I)
                            for loc in locs[:self.max_pages]:
                                c_loc = self._clean_url(loc)
                                if c_loc and c_loc not in visited:
                                    queue.append({"url": c_loc, "depth": 1, "parent": s_url})
                except Exception as s_err:
                    logger.warning(f"Failed to fetch sitemap from {s_url}: {s_err}")

            while queue and len(results) < self.max_pages and not self.cancelled:
                item = queue.pop(0)
                url = self._clean_url(item["url"])
                depth = item["depth"]

                if not url or url in visited or depth > self.max_depth:
                    continue
                visited.add(url)

                parsed = urlparse(url)
                if not parsed.hostname or is_private_ip(parsed.hostname):
                    logger.warning(f"Blocked invalid or SSRF hostname: {url}")
                    continue

                if self.respect_robots and not await self.robots_checker.can_fetch(url, self.respect_robots):
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
                        async with session.get(url, allow_redirects=True) as resp:
                            status_code = resp.status
                            if resp.status != 200:
                                continue
                            content_type = resp.headers.get("Content-Type", "").lower()
                            if "text/html" not in content_type and "application/xhtml" not in content_type:
                                continue
                            try:
                                html_content = await resp.text()
                            except UnicodeDecodeError:
                                raw_bytes = await resp.read()
                                html_content = raw_bytes.decode("utf-8", errors="replace")

                    if not html_content or len(html_content.strip()) < 50:
                        continue

                    # Extract metadata
                    extractor = MetadataExtractor(url)
                    extracted_meta = extractor.extract(html_content, url)

                    # Clean HTML and convert to Markdown
                    cleaned_html = self.cleaner.clean(html_content)
                    markdown_text = self.markdown_converter.convert(cleaned_html)

                    if not markdown_text.strip():
                        continue

                    # Deduplication check
                    if self.deduplicator.is_duplicate_content(markdown_text):
                        continue

                    page_result = {
                        "url": url,
                        "canonical_url": extracted_meta.get("canonical_url") or url,
                        "title": extracted_meta.get("title") or parsed.path or url,
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
                        base_domain = parsed.netloc.lower().removeprefix("www.")
                        for a in soup.find_all('a', href=True):
                            href = a['href'].strip()
                            if not href or href.startswith(('javascript:', 'mailto:', 'tel:', '#', 'data:')):
                                continue
                            next_url = self._clean_url(urljoin(url, href))
                            p_next = urlparse(next_url)
                            next_domain = p_next.netloc.lower().removeprefix("www.")
                            if next_domain == base_domain and next_url not in visited:
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
