# src/impedance/padding.py
from typing import Tuple

PROMPT_PAD_TOKENS = 4096           # paper §Architecture
_PAD_CHAR = " "

def pad(prompt: str, tokens: int = PROMPT_PAD_TOKENS) -> Tuple[str, int]:
    """Pad to exactly `tokens` length (characters ≈ tokens) & return (padded, added)."""
    deficit = max(tokens - len(prompt), 0)
    return prompt + (_PAD_CHAR * deficit), deficit