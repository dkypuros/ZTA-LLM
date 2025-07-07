"""
Security Impedance Core Implementation

Reference implementation for "Zero-Trust Agentic LLM Orchestration on OpenShift"
providing multi-layer security controls: aliasing → padding → OPA → NetPolicy
"""

from .alias import alias_path, is_alias
from .padding import pad, PROMPT_PAD_TOKENS
from .scan import contains_secret, contains_raw_path

__version__ = "1.0.0"
__all__ = [
    "alias_path", 
    "is_alias",
    "pad", 
    "PROMPT_PAD_TOKENS",
    "contains_secret", 
    "contains_raw_path"
]