import re
from bs4 import BeautifulSoup

class MarkdownConverter:
    def __init__(self, extract_images: bool = True):
        self.extract_images = extract_images

    def convert(self, html_content: str) -> str:
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, 'html.parser')
        lines = []

        def process_node(node):
            if isinstance(node, str):
                text = node.strip()
                if text:
                    lines.append(text)
                return

            tag = node.name
            if not tag:
                return

            if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                level = int(tag[1])
                prefix = '#' * level
                text = node.get_text(strip=True)
                if text:
                    lines.append(f"\n{prefix} {text}\n")
            elif tag == 'p':
                text = node.get_text(strip=True)
                if text:
                    lines.append(f"\n{text}\n")
            elif tag in ['ul', 'ol']:
                for idx, li in enumerate(node.find_all('li', recursive=False)):
                    bullet = f"{idx + 1}." if tag == 'ol' else "-"
                    lines.append(f"{bullet} {li.get_text(strip=True)}")
                lines.append("")
            elif tag == 'blockquote':
                text = node.get_text(strip=True)
                if text:
                    lines.append(f"\n> {text}\n")
            elif tag in ['pre', 'code']:
                code_text = node.get_text()
                lines.append(f"\n```\n{code_text.strip()}\n```\n")
            elif tag == 'table':
                rows = node.find_all('tr')
                table_lines = []
                for row_idx, row in enumerate(rows):
                    cells = [cell.get_text(strip=True) for cell in row.find_all(['th', 'td'])]
                    if cells:
                        table_lines.append("| " + " | ".join(cells) + " |")
                        if row_idx == 0:
                            table_lines.append("| " + " | ".join(['---'] * len(cells)) + " |")
                if table_lines:
                    lines.append("\n" + "\n".join(table_lines) + "\n")
            elif tag == 'img' and self.extract_images:
                src = node.get('src', '')
                alt = node.get('alt', 'image')
                if src:
                    lines.append(f"\n![{alt}]({src})\n")
            elif tag == 'a':
                href = node.get('href', '')
                text = node.get_text(strip=True)
                if href and text:
                    lines.append(f"[{text}]({href})")
            else:
                for child in node.children:
                    process_node(child)

        process_node(soup)
        md = "\n".join(lines)
        md = re.sub(r'\n{3,}', '\n\n', md)
        return md.strip()
