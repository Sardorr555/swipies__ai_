import time

class JobProgressTracker:
    def __init__(self, job_id: str, total_target: int = 100):
        self.job_id = job_id
        self.total_target = total_target
        self.pages_discovered = 0
        self.pages_processed = 0
        self.pages_failed = 0
        self.chunks_created = 0
        self.embeddings_completed = 0
        self.current_url = ""
        self.status = "running"  # running, completed, failed, cancelled
        self.logs = []
        self.start_time = time.time()

    def log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)
        if len(self.logs) > 200:
            self.logs.pop(0)

    def update_url(self, url: str, processed_count: int):
        self.current_url = url
        self.pages_processed = processed_count
        self.log(f"Processing URL: {url}")

    def to_dict(self) -> dict:
        elapsed = time.time() - self.start_time
        remaining = 0
        if self.pages_processed > 0 and self.total_target > self.pages_processed:
            avg_per_page = elapsed / self.pages_processed
            remaining = int((self.total_target - self.pages_processed) * avg_per_page)

        return {
            "job_id": self.job_id,
            "status": self.status,
            "pages_discovered": self.pages_discovered,
            "pages_processed": self.pages_processed,
            "pages_failed": self.pages_failed,
            "chunks_created": self.chunks_created,
            "embeddings_completed": self.embeddings_completed,
            "current_url": self.current_url,
            "elapsed_seconds": int(elapsed),
            "estimated_remaining_seconds": remaining,
            "logs": self.logs
        }
