import time

class MetadataBuilder:
    @staticmethod
    def build_chunk_metadata(dataset_id: str, source_url: str, extracted_meta: dict, chunk_index: int, total_chunks: int, depth: int = 0) -> dict:
        return {
            "dataset_id": dataset_id,
            "source_url": source_url,
            "canonical_url": extracted_meta.get("canonical_url", source_url),
            "title": extracted_meta.get("title", ""),
            "language": extracted_meta.get("language", "en"),
            "description": extracted_meta.get("description", ""),
            "author": extracted_meta.get("author", ""),
            "publish_date": extracted_meta.get("publish_date", ""),
            "last_modified": extracted_meta.get("publish_date", ""),
            "chunk_number": chunk_index,
            "total_chunks": total_chunks,
            "depth": depth,
            "heading_hierarchy": [h.get("text") for h in extracted_meta.get("headings", [])],
            "content_type": "text/markdown",
            "import_timestamp": int(time.time()),
            "http_status": 200
        }
