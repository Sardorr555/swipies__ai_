import pytest
from crawler.cleaner import HTMLCleaner
from crawler.markdown import MarkdownConverter
from crawler.extractor import MetadataExtractor
from crawler.deduplicator import Deduplicator
from crawler.robots import RobotsChecker
from crawler.scheduler import IncrementalScheduler

def test_html_cleaner():
    cleaner = HTMLCleaner({"ignore_nav": True, "ignore_footer": True, "remove_ads": True})
    html = """
    <html>
        <head><script>alert('xss')</script><style>body {color: red;}</style></head>
        <body>
            <nav>Navigation menu</nav>
            <div class="ad">Advertisement</div>
            <article><h1>Main Article Header</h1><p>Main content paragraph.</p></article>
            <footer>Footer copyright</footer>
        </body>
    </html>
    """
    cleaned = cleaner.clean(html)
    assert "<script>" not in cleaned
    assert "<style>" not in cleaned
    assert "Navigation menu" not in cleaned
    assert "Advertisement" not in cleaned
    assert "Footer copyright" not in cleaned
    assert "Main Article Header" in cleaned
    assert "Main content paragraph." in cleaned


def test_markdown_converter():
    converter = MarkdownConverter()
    html = "<h1>Title</h1><p>Paragraph text</p><ul><li>Item 1</li><li>Item 2</li></ul>"
    md = converter.convert(html)
    assert "# Title" in md
    assert "Paragraph text" in md
    assert "- Item 1" in md
    assert "- Item 2" in md


def test_metadata_extractor():
    extractor = MetadataExtractor("https://example.com/page")
    html = """
    <html>
        <head>
            <title>Test Page Title</title>
            <meta name="description" content="Test Page Description" />
            <meta name="author" content="Test Author" />
        </head>
        <body>
            <h1>Heading 1</h1>
            <a href="/docs/guide.pdf">Download PDF Guide</a>
        </body>
    </html>
    """
    meta = extractor.extract(html, "https://example.com/page")
    assert meta["title"] == "Test Page Title"
    assert meta["description"] == "Test Page Description"
    assert meta["author"] == "Test Author"
    assert len(meta["document_links"]) == 1
    assert meta["document_links"][0]["url"] == "https://example.com/docs/guide.pdf"


def test_deduplicator():
    dedup = Deduplicator()
    assert not dedup.is_duplicate_url("https://example.com/page1")
    assert dedup.is_duplicate_url("https://example.com/page1/")

    assert not dedup.is_duplicate_content("Unique paragraph 1")
    assert dedup.is_duplicate_content("Unique paragraph 1")


def test_incremental_scheduler():
    scheduler = IncrementalScheduler()
    existing_meta = {"checksum": "abc12345", "etag": "v1"}
    assert not scheduler.is_modified(existing_meta, new_etag="v1", new_checksum="abc12345")
    assert scheduler.is_modified(existing_meta, new_etag="v2", new_checksum="abc12345")
