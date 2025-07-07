# src/impedance/scan.py
import re, base64

SECRET_PATTERNS = [
    re.compile(r"sk_live_[0-9A-Za-z]{16,}"),  # Stripe live key (min 16 chars)
    re.compile(r"sk_test_[0-9A-Za-z]{16,}"),  # Stripe test key (min 16 chars)
    re.compile(r"AKIA[0-9A-Z]{16}"),          # AWS access key
]

_PATH_RE = re.compile(r"/[A-Za-z0-9_\-./]{3,}")    # non-aliased path

def contains_secret(text: str) -> bool:
    return any(p.search(text) for p in SECRET_PATTERNS)

def contains_raw_path(text: str) -> bool:
    return bool(_PATH_RE.search(text)) and "FILE_" not in text