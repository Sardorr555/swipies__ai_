import logging
import urllib.robotparser
from urllib.parse import urlparse
import aiohttp

logger = logging.getLogger(__name__)

class RobotsChecker:
    def __init__(self, user_agent: str = "RAGFlow-WebCrawler/1.0"):
        self.user_agent = user_agent
        self.parsers = {}

    async def can_fetch(self, url: str, respect_robots: bool = True) -> bool:
        if not respect_robots:
            return True

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return False

        domain = f"{parsed.scheme}://{parsed.netloc}"
        if domain not in self.parsers:
            robots_url = f"{domain}/robots.txt"
            rp = urllib.robotparser.RobotFileParser()
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(robots_url, timeout=10) as resp:
                        if resp.status == 200:
                            content = await resp.text()
                            rp.parse(content.splitlines())
                        else:
                            rp.allow_all = True
            except Exception as e:
                logger.debug(f"Could not fetch robots.txt from {robots_url}: {e}")
                rp.allow_all = True
            self.parsers[domain] = rp

        rp = self.parsers[domain]
        return rp.can_fetch(self.user_agent, url)
