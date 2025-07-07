"""
Deterministic Path Aliasing Implementation

Implements Algorithm 1 from the paper: converts file paths to deterministic
SHA256-based aliases to prevent organizational structure disclosure.
"""

import hashlib
import re
from typing import Dict, NamedTuple, Optional
from pathlib import Path


class AliasedPath(NamedTuple):
    """Represents an aliased path with its original and token forms."""
    original: str
    alias_token: str
    hash_digest: str


class PathAliaser:
    """
    Deterministic path aliasing following the Security Impedance pattern.
    
    Prevents disclosure of organizational file structure by replacing
    actual paths with SHA256-based deterministic tokens.
    """
    
    def __init__(self, prefix: str = "FILE_"):
        self.prefix = prefix
        self._alias_cache: Dict[str, AliasedPath] = {}
        self._reverse_cache: Dict[str, str] = {}
        
        # Regex patterns for path detection
        self._path_patterns = [
            r'/[a-zA-Z0-9_\-./~]{3,}',  # Unix-style paths
            r'[A-Za-z]:\\[a-zA-Z0-9_\-\\. ]{2,}',  # Windows paths
            r'~[a-zA-Z0-9_\-./]{2,}',  # Home directory paths
            r'\./[a-zA-Z0-9_\-./]{2,}',  # Relative paths
            r'\.\./[a-zA-Z0-9_\-./]{2,}',  # Parent directory paths
        ]
        
    def alias_path(self, path: str) -> AliasedPath:
        """
        Generate deterministic alias for a file path.
        
        Algorithm from paper:
        1. hash = SHA256(path)[:8]
        2. token = prefix + hash
        3. Store bidirectional mapping
        
        Args:
            path: Original file path
            
        Returns:
            AliasedPath with original, alias_token, and hash_digest
        """
        if path in self._alias_cache:
            return self._alias_cache[path]
            
        # Normalize path for consistent hashing (avoid container-specific absolute paths)
        normalized_path = os.path.normpath(path).replace('\\', '/')
        
        # Generate deterministic hash
        hash_object = hashlib.sha256(normalized_path.encode('utf-8'))
        hash_digest = hash_object.hexdigest()
        alias_hash = hash_digest[:8]
        
        # Create token
        alias_token = f"{self.prefix}{alias_hash}"
        
        # Store in caches
        aliased_path = AliasedPath(
            original=path,
            alias_token=alias_token,
            hash_digest=hash_digest
        )
        
        self._alias_cache[path] = aliased_path
        self._reverse_cache[alias_token] = path
        
        return aliased_path
    
    def resolve_alias(self, alias_token: str) -> Optional[str]:
        """
        Resolve an alias token back to its original path.
        
        Args:
            alias_token: The aliased token to resolve
            
        Returns:
            Original path if found, None otherwise
        """
        return self._reverse_cache.get(alias_token)
    
    def sanitize_text(self, text: str) -> str:
        """
        Replace all detected paths in text with their aliases.
        
        Args:
            text: Text potentially containing file paths
            
        Returns:
            Text with all paths replaced by alias tokens
        """
        sanitized_text = text
        
        for pattern in self._path_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                path = match.group(0)
                aliased = self.alias_path(path)
                sanitized_text = sanitized_text.replace(path, aliased.alias_token)
                
        return sanitized_text
    
    def get_stats(self) -> Dict[str, int]:
        """Get aliasing statistics for monitoring."""
        return {
            "total_aliases": len(self._alias_cache),
            "cache_size_bytes": sum(
                len(k.encode()) + len(v.original.encode()) + len(v.alias_token.encode())
                for k, v in self._alias_cache.items()
            )
        }
    
    def clear_cache(self) -> None:
        """Clear the alias cache (for testing/reset)."""
        self._alias_cache.clear()
        self._reverse_cache.clear()


class SecurePath:
    """
    Context manager for secure path handling.
    
    Automatically aliases paths and provides secure access patterns.
    """
    
    def __init__(self, aliaser: PathAliaser, original_path: str):
        self.aliaser = aliaser
        self.original_path = original_path
        self.aliased_path: Optional[AliasedPath] = None
        
    def __enter__(self) -> AliasedPath:
        self.aliased_path = self.aliaser.alias_path(self.original_path)
        return self.aliased_path
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass  # Could implement cleanup logic here
        
    @property
    def safe_path(self) -> str:
        """Get the safe alias token for use in prompts."""
        if self.aliased_path:
            return self.aliased_path.alias_token
        return self.aliaser.alias_path(self.original_path).alias_token