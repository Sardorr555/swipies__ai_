import re
from bs4 import BeautifulSoup, Comment

class HTMLCleaner:
    def __init__(self, options: dict = None):
        self.options = options or {}

    def _extract_script_templates_and_data(self, soup: BeautifulSoup) -> None:
        """
        Extract content from scripts if the static body text is sparse.
        Recovers template literals (e.g. `<h2>...</h2>`), JSON-LD article bodies,
        and structured copy before script tags are stripped.
        """
        body_text_len = len(soup.body.get_text(strip=True)) if soup.body else 0
        if body_text_len >= 800:
            return

        recovered_fragments = []
        bt = chr(96)
        for s in soup.find_all('script'):
            stext = s.get_text()
            if not stext:
                continue

            # JSON-LD structured data
            s_type = s.get('type', '').lower()
            if 'ld+json' in s_type:
                try:
                    import json
                    data = json.loads(stext)
                    def extract_ld(obj):
                        if isinstance(obj, dict):
                            for k in ['articleBody', 'text', 'description', 'answer']:
                                if k in obj and isinstance(obj[k], str) and len(obj[k].strip()) > 30:
                                    recovered_fragments.append(f"<p>{obj[k]}</p>")
                            for v in obj.values():
                                extract_ld(v)
                        elif isinstance(obj, list):
                            for item in obj:
                                extract_ld(item)
                    extract_ld(data)
                except Exception:
                    pass

            # JS template literals: `...`
            if bt in stext:
                parts = stext.split(bt)
                for p in parts:
                    val = p.strip()
                    if len(val) > 80 and any(tag in val for tag in ('<h1', '<h2', '<h3', '<h4', '<p', '<ul', '<ol', '<div', '<li', '<table', '<article', '<section')):
                        recovered_fragments.append(val)

        if recovered_fragments:
            container = soup.new_tag('div', attrs={'class': 'recovered-script-content'})
            for frag in recovered_fragments:
                try:
                    frag_soup = BeautifulSoup(frag, 'html.parser')
                    container.append(frag_soup)
                except Exception:
                    pass
            if soup.body:
                soup.body.append(container)
            elif soup:
                soup.append(container)

    def clean(self, html_content: str) -> str:
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, 'html.parser')

        # 0. Recover embedded templates / JSON-LD if body text is sparse
        self._extract_script_templates_and_data(soup)

        # 1. Remove comments
        for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
            comment.extract()

        # 2. Always remove script, style, svg, iframe, noscript, tracking
        tags_to_remove = ['script', 'style', 'svg', 'iframe', 'noscript', 'canvas', 'map', 'object', 'embed']
        for tag in soup.find_all(tags_to_remove):
            tag.decompose()

        # 3. Structural element removal based on options
        selectors_to_remove = []
        if self.options.get("ignore_nav", True):
            selectors_to_remove.extend(['nav', '[role="navigation"]', '.navbar', '.nav', '#nav', '.menu', '#menu'])
        if self.options.get("ignore_header", False):
            selectors_to_remove.extend(['header', '[role="banner"]', '.header', '#header'])
        if self.options.get("ignore_footer", True):
            selectors_to_remove.extend(['footer', '[role="contentinfo"]', '.footer', '#footer'])
        if self.options.get("ignore_sidebar", True):
            selectors_to_remove.extend(['aside', '.sidebar', '#sidebar', '.widget-area'])
        if self.options.get("remove_cookie_banner", True):
            selectors_to_remove.extend(['.cookie-banner', '#cookie-banner', '.cookie-consent', '.privacy-policy-banner', '[id*="cookie"]', '[class*="cookie"]'])
        if self.options.get("remove_ads", True):
            selectors_to_remove.extend(['.ad', '.ads', '.advertisement', '[id*="google_ads"]', '.ad-box'])

        for selector in selectors_to_remove:
            for element in soup.select(selector):
                element.decompose()

        # 4. Remove hidden elements
        for hidden in soup.find_all(attrs={"aria-hidden": "true"}):
            hidden.decompose()
        for hidden in soup.find_all(style=re.compile(r'display:\s*none|visibility:\s*hidden', re.I)):
            hidden.decompose()

        # 5. Clean attributes from remaining tags (keep href, src, alt, title)
        for tag in soup.find_all(True):
            allowed_attrs = {}
            if tag.name == 'a' and tag.has_attr('href'):
                allowed_attrs['href'] = tag['href']
            if tag.name == 'img':
                if tag.has_attr('src'):
                    allowed_attrs['src'] = tag['src']
                if tag.has_attr('alt'):
                    allowed_attrs['alt'] = tag['alt']
                if tag.has_attr('title'):
                    allowed_attrs['title'] = tag['title']
            tag.attrs = allowed_attrs

        # 6. Normalize whitespace
        cleaned_html = str(soup)
        cleaned_html = re.sub(r'\n\s*\n', '\n', cleaned_html)
        return cleaned_html
