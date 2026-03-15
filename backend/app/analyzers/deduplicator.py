"""Deduplication logic using URL normalization + SimHash title similarity."""
import hashlib
import logging

logger = logging.getLogger(__name__)

# Hamming distance threshold for SimHash title dedup (lower = stricter)
SIMHASH_THRESHOLD = 5


def url_fingerprint(url: str) -> str:
    """MD5 of normalized URL for quick exact-match dedup."""
    return hashlib.md5(url.lower().strip().encode()).hexdigest()


def title_simhash(title: str) -> str:
    """Compute a simple 64-bit SimHash of tokenized title words."""
    tokens = title.lower().split()
    v = [0] * 64
    for token in tokens:
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        for i in range(64):
            if h & (1 << i):
                v[i] += 1
            else:
                v[i] -= 1
    bits = sum(1 << i for i in range(64) if v[i] > 0)
    return format(bits, "016x")


def hamming_distance(h1: str, h2: str) -> int:
    """Hamming distance between two hex SimHash strings."""
    n1, n2 = int(h1, 16), int(h2, 16)
    xor = n1 ^ n2
    return bin(xor).count("1")


def is_duplicate_title(new_hash: str, existing_hashes: list[str]) -> bool:
    """Return True if any existing hash is within threshold."""
    for h in existing_hashes:
        if hamming_distance(new_hash, h) <= SIMHASH_THRESHOLD:
            return True
    return False
