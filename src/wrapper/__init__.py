"""
ZTA-LLM Security Wrapper Module

Layer 1 security controls implementing the Security Impedance framework.
Provides deterministic path aliasing, constant-length prompt padding,
and multi-pattern secret detection.
"""

from .path_aliasing import PathAliaser, AliasedPath
from .prompt_padding import PromptPadder, PaddedPrompt
from .secret_detection import SecretDetector, SecretMatch
from .entropy_analysis import EntropyAnalyzer, EntropyResult

__all__ = [
    "PathAliaser",
    "AliasedPath", 
    "PromptPadder",
    "PaddedPrompt",
    "SecretDetector",
    "SecretMatch",
    "EntropyAnalyzer",
    "EntropyResult"
]

__version__ = "1.0.0"