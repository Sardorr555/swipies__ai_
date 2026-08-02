import hashlib
import re

class Deduplicator:
    def __init__(self):
        self.seen_urls = set()
        self.seen_checksums = set()
        self.seen_hashes = set()

    def is_duplicate_url(self, url: str) -> bool:
        normalized = url.rstrip('/').lower()
        if normalized in self.seen_urls:
            return True
        self.seen_urls.add(normalized)
        return False

    def is_duplicate_content(self, text_content: str) -> bool:
        if not text_content:
            return True
        cleaned = re.sub(r'\s+', '', text_content)
        checksum = hashlib.sha256(cleaned.encode('utf-8')).hexdigest()
        if checksum in self.seen_checksums:
            return True
        self.seen_checksums.add(checksum)
        return False

    def compute_simhash(self, text: str) -> int:
        words = re.findall(r'\w+', text.lower())
        v = [0] * 64
        for word in words:
            h = int(hashlib.md5(word.encode('utf-8')).hexdigest(), 16)
            for i in range(64):
                bit = (h >> i) & 1
                if bit:
                    v[i] += 1
                else:
                    v[i] -= 1
        fingerprint = 0
        for i in range(64):
            if v[i] >= 0:
                fingerprint |= (1 << i)
        return fingerprint

    def is_near_duplicate(self, text: str, threshold: int = 3) -> bool:
        if not text:
            return True
        sh = self.compute_simhash(text)
        for existing in self.seen_hashes:
            # Hamming distance
            dist = bin(sh ^ existing).count('1')
            if dist <= threshold:
                return True
        self.seen_hashes.add(sh)
        return False
