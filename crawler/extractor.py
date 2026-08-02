import json
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

DOCUMENT_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.xlsx', '.csv', '.txt', '.md'}

class MetadataExtractor:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def extract(self, html_content: str, current_url: str) -> dict:
        soup = BeautifulSoup(html_content, 'html.parser')
        metadata = {
            "title": "",
            "canonical_url": current_url,
            "language": "en",
            "description": "",
            "author": "",
            "publish_date": "",
            "headings": [],
            "json_ld": [],
            "open_graph": {},
            "document_links": [],
            "image_links": [],
            "breadcrumbs": []
        }

        # 1. Title
        title_tag = soup.find('title')
        if title_tag and title_tag.string:
            metadata["title"] = title_tag.string.strip()

        # 2. Canonical URL
        canonical_tag = soup.find('link', rel='canonical')
        if canonical_tag and canonical_tag.get('href'):
            metadata["canonical_url"] = urljoin(current_url, canonical_tag['href'])

        # 3. Language
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            metadata["language"] = html_tag['lang']

        # 4. Meta Description & Author & Dates
        meta_desc = soup.find('meta', attrs={'name': re.compile(r'description', re.I)})
        if meta_desc and meta_desc.get('content'):
            metadata["description"] = meta_desc['content'].strip()

        meta_author = soup.find('meta', attrs={'name': re.compile(r'author', re.I)})
        if meta_author and meta_author.get('content'):
            metadata["author"] = meta_author['content'].strip()

        meta_date = soup.find('meta', attrs={'name': re.compile(r'date|published_time', re.I)})
        if meta_date and meta_date.get('content'):
            metadata["publish_date"] = meta_date['content'].strip()

        # 5. OpenGraph
        for og in soup.find_all('meta', property=re.compile(r'^og:')):
            prop = og.get('property', '')[3:]
            metadata["open_graph"][prop] = og.get('content', '')

        if not metadata["title"] and metadata["open_graph"].get("title"):
            metadata["title"] = metadata["open_graph"]["title"]

        # 6. JSON-LD
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                if script.string:
                    data = json.loads(script.string)
                    metadata["json_ld"].append(data)
            except Exception:
                pass

        # 7. Headings Hierarchy
        for h in soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
            metadata["headings"].append({
                "level": int(h.name[1]),
                "text": h.get_text(strip=True)
            })

        # 8. Downloadable documents & Images
        for a in soup.find_all('a', href=True):
            href = urljoin(current_url, a['href'])
            parsed = urlparse(href)
            path = parsed.path.lower()
            for ext in DOCUMENT_EXTENSIONS:
                if path.endswith(ext):
                    metadata["document_links"].append({
                        "url": href,
                        "extension": ext,
                        "title": a.get_text(strip=True) or metadata["title"]
                    })
                    break

        for img in soup.find_all('img', src=True):
            src = urljoin(current_url, img['src'])
            metadata["image_links"].append({
                "src": src,
                "alt": img.get('alt', ''),
                "title": img.get('title', '')
            })

        return metadata
