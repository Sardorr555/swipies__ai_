import hashlib
import time

class IncrementalScheduler:
    @staticmethod
    def is_modified(existing_doc_meta: dict, new_etag: str = None, new_last_modified: str = None, new_checksum: str = None) -> bool:
        if not existing_doc_meta:
            return True

        if new_etag and existing_doc_meta.get("etag"):
            return new_etag != existing_doc_meta.get("etag")

        if new_last_modified and existing_doc_meta.get("last_modified"):
            return new_last_modified != existing_doc_meta.get("last_modified")

        if new_checksum and existing_doc_meta.get("checksum"):
            return new_checksum != existing_doc_meta.get("checksum")

        return True

    @staticmethod
    def calculate_next_run(cron_expr: str or str = "daily") -> int:
        now = int(time.time())
        if cron_expr == "hourly":
            return now + 3600
        elif cron_expr == "daily":
            return now + 86400
        elif cron_expr == "weekly":
            return now + 604800
        elif cron_expr == "monthly":
            return now + 2592000
        return now + 86400
