# src/impedance/alias.py
import hashlib, os, pathlib, re

_ALIAS_PREFIX = "FILE_"

def alias_path(path: str) -> str:
    """Return 8-hex SHA-256 alias, e.g. /data/foo.csv -> FILE_a1b2c3d4"""
    # Normalize path without resolving to avoid container-specific absolute paths
    norm = os.path.normpath(path).replace('\\', '/')
    digest = hashlib.sha256(norm.encode()).hexdigest()[:8]
    return _ALIAS_PREFIX + digest

_ALIAS_RE = re.compile(fr"{_ALIAS_PREFIX}[0-9a-f]{{8}}")

def is_alias(token: str) -> bool:
    return bool(_ALIAS_RE.fullmatch(token))