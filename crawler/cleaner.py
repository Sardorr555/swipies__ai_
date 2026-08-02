import re
from bs4 import BeautifulSoup, Comment

class HTMLCleaner:
    def __init__(self, options: dict = None):
        self.options = options or {}

    def clean(self, html_content: str) -> str:
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, 'html.parser')

        # 1. Remove comments
        for comment in soup.find_all(text=lambda text: isinstance(text, Comment)):
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
