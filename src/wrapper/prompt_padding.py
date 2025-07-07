"""
Constant-Length Prompt Padding Implementation

Implements the prompt padding technique from the paper to prevent
side-channel inference based on prompt length variations.
"""

import time
import random
from typing import NamedTuple, Optional
from enum import Enum


class PaddingStrategy(Enum):
    """Different padding strategies for various use cases."""
    WHITESPACE = "whitespace"
    SEMANTIC_NOISE = "semantic_noise"
    STRUCTURED_PADDING = "structured"


class PaddedPrompt(NamedTuple):
    """Represents a padded prompt with metadata."""
    original_prompt: str
    padded_prompt: str
    original_length: int
    padded_length: int
    padding_added: int
    strategy_used: PaddingStrategy


class PromptPadder:
    """
    Constant-length prompt padding for side-channel resistance.
    
    Prevents information leakage through prompt length analysis by
    ensuring all prompts are padded to fixed lengths.
    """
    
    def __init__(
        self,
        target_length: int = 4096,
        strategy: PaddingStrategy = PaddingStrategy.WHITESPACE,
        add_timing_jitter: bool = True
    ):
        self.target_length = target_length
        self.strategy = strategy
        self.add_timing_jitter = add_timing_jitter
        
        # Semantic noise vocabulary for advanced padding
        self._noise_vocabulary = [
            "furthermore", "additionally", "consequently", "nevertheless",
            "specifically", "particularly", "essentially", "fundamentally",
            "accordingly", "subsequently", "alternatively", "conversely",
            "meanwhile", "simultaneously", "ultimately", "precisely"
        ]
        
        # Structured padding templates
        self._structured_templates = [
            "\n\n--- Additional context markers ---",
            "\n\n<!-- Padding section -->",
            "\n\n/* Security padding */",
            "\n\n## Metadata section"
        ]
    
    def pad_prompt(self, prompt: str) -> PaddedPrompt:
        """
        Pad prompt to target length using specified strategy.
        
        Args:
            prompt: Original prompt text
            
        Returns:
            PaddedPrompt with original and padded versions
        """
        if self.add_timing_jitter:
            self._add_timing_jitter()
            
        original_length = len(prompt)
        
        if original_length >= self.target_length:
            # Truncate if too long (with warning in production)
            padded_prompt = prompt[:self.target_length]
            padding_added = 0
        else:
            padding_needed = self.target_length - original_length
            padding_text = self._generate_padding(padding_needed)
            padded_prompt = prompt + padding_text
            padding_added = padding_needed
            
        return PaddedPrompt(
            original_prompt=prompt,
            padded_prompt=padded_prompt,
            original_length=original_length,
            padded_length=len(padded_prompt),
            padding_added=padding_added,
            strategy_used=self.strategy
        )
    
    def _generate_padding(self, length: int) -> str:
        """Generate padding text based on the selected strategy."""
        if self.strategy == PaddingStrategy.WHITESPACE:
            return " " * length
            
        elif self.strategy == PaddingStrategy.SEMANTIC_NOISE:
            return self._generate_semantic_noise(length)
            
        elif self.strategy == PaddingStrategy.STRUCTURED_PADDING:
            return self._generate_structured_padding(length)
            
        else:
            return " " * length  # Fallback to whitespace
    
    def _generate_semantic_noise(self, length: int) -> str:
        """
        Generate semantically neutral noise words.
        
        Creates realistic-looking text that doesn't convey information
        but maintains linguistic structure for LLM processing.
        """
        noise_text = "\n\nAdditional context: "
        remaining = length - len(noise_text)
        
        while remaining > 0:
            word = random.choice(self._noise_vocabulary)
            if remaining >= len(word) + 1:
                noise_text += word + " "
                remaining -= len(word) + 1
            else:
                noise_text += " " * remaining
                break
                
        return noise_text
    
    def _generate_structured_padding(self, length: int) -> str:
        """
        Generate structured padding that looks like legitimate content.
        
        Uses comment-like structures that blend with various content types.
        """
        template = random.choice(self._structured_templates)
        remaining = length - len(template)
        
        if remaining > 0:
            filler = " " * remaining
            return template + filler
        else:
            return template[:length]
    
    def _add_timing_jitter(self) -> None:
        """
        Add small random delays to prevent timing-based side channels.
        
        Implements the timing jitter mentioned in the paper's
        performance evaluation section.
        """
        jitter_ms = random.uniform(0.1, 2.0)  # 0.1-2ms jitter
        time.sleep(jitter_ms / 1000.0)
    
    def validate_padding(self, padded_prompt: PaddedPrompt) -> bool:
        """
        Validate that padding was applied correctly.
        
        Args:
            padded_prompt: The padded prompt to validate
            
        Returns:
            True if padding is valid, False otherwise
        """
        expected_length = self.target_length
        actual_length = len(padded_prompt.padded_prompt)
        
        # Allow slight variations for truncation cases
        return abs(actual_length - expected_length) <= 10
    
    def get_padding_stats(self) -> dict:
        """Get padding statistics for monitoring."""
        return {
            "target_length": self.target_length,
            "strategy": self.strategy.value,
            "timing_jitter_enabled": self.add_timing_jitter,
            "noise_vocabulary_size": len(self._noise_vocabulary)
        }


class AdaptivePadder:
    """
    Adaptive padding that adjusts target length based on content analysis.
    
    Future enhancement to reduce the 15% token overhead mentioned in the paper
    while maintaining security properties.
    """
    
    def __init__(self, base_padder: PromptPadder):
        self.base_padder = base_padder
        self._length_history = []
        self._max_history = 1000
    
    def adaptive_pad(self, prompt: str, content_type: Optional[str] = None) -> PaddedPrompt:
        """
        Apply adaptive padding based on content type and history.
        
        Args:
            prompt: Original prompt
            content_type: Optional content type hint for optimization
            
        Returns:
            Adaptively padded prompt
        """
        # Analyze prompt characteristics
        prompt_length = len(prompt)
        self._length_history.append(prompt_length)
        
        # Keep history bounded
        if len(self._length_history) > self._max_history:
            self._length_history = self._length_history[-self._max_history:]
        
        # Calculate adaptive target length
        if len(self._length_history) >= 10:
            avg_length = sum(self._length_history[-10:]) / 10
            # Set target to 120% of recent average, minimum 2048
            adaptive_target = max(int(avg_length * 1.2), 2048)
            self.base_padder.target_length = adaptive_target
        
        return self.base_padder.pad_prompt(prompt)