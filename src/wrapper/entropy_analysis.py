"""
Entropy Analysis for High-Entropy String Detection

Implements statistical analysis to detect potential secrets and keys
based on Shannon entropy calculations, complementing regex-based detection.
"""

import math
import re
from typing import NamedTuple, List, Dict
from collections import Counter


class EntropyResult(NamedTuple):
    """Result of entropy analysis on a text segment."""
    text: str
    entropy: float
    length: int
    is_suspicious: bool
    analysis_details: Dict[str, float]


class EntropyAnalyzer:
    """
    Shannon entropy analysis for secret detection.
    
    Complements regex-based detection by identifying high-entropy
    strings that may be encoded secrets, keys, or tokens.
    """
    
    def __init__(
        self,
        min_length: int = 16,
        entropy_threshold: float = 4.5,
        suspicious_patterns: List[str] = None
    ):
        self.min_length = min_length
        self.entropy_threshold = entropy_threshold
        self.suspicious_patterns = suspicious_patterns or [
            r'[A-Za-z0-9+/]{20,}={0,2}',  # Base64-like
            r'[A-Fa-f0-9]{32,}',          # Hex strings
            r'[A-Za-z0-9_-]{20,}',        # URL-safe base64
            r'[A-Z0-9]{20,}',             # Upper case alphanumeric
        ]
        
        # Character sets for analysis
        self.charset_patterns = {
            'lowercase': r'[a-z]',
            'uppercase': r'[A-Z]',
            'digits': r'[0-9]',
            'special': r'[^A-Za-z0-9]',
            'base64_chars': r'[A-Za-z0-9+/=]',
            'hex_chars': r'[A-Fa-f0-9]'
        }
    
    def calculate_entropy(self, text: str) -> float:
        """
        Calculate Shannon entropy of a string.
        
        Args:
            text: String to analyze
            
        Returns:
            Shannon entropy value (bits per character)
        """
        if not text:
            return 0.0
        
        # Count character frequencies
        char_counts = Counter(text)
        text_length = len(text)
        
        # Calculate Shannon entropy
        entropy = 0.0
        for count in char_counts.values():
            probability = count / text_length
            if probability > 0:
                entropy -= probability * math.log2(probability)
        
        return entropy
    
    def analyze_text_segment(self, text: str) -> EntropyResult:
        """
        Perform comprehensive entropy analysis on a text segment.
        
        Args:
            text: Text segment to analyze
            
        Returns:
            EntropyResult with entropy and analysis details
        """
        entropy = self.calculate_entropy(text)
        
        # Additional analysis metrics
        analysis_details = {
            'entropy': entropy,
            'length': len(text),
            'unique_chars': len(set(text)),
            'char_diversity': len(set(text)) / len(text) if text else 0,
            'compression_ratio': self._estimate_compression_ratio(text),
        }
        
        # Character set analysis
        for charset_name, pattern in self.charset_patterns.items():
            matches = len(re.findall(pattern, text))
            analysis_details[f'{charset_name}_ratio'] = matches / len(text) if text else 0
        
        # Determine if suspicious
        is_suspicious = (
            entropy >= self.entropy_threshold and
            len(text) >= self.min_length and
            self._matches_suspicious_pattern(text)
        )
        
        return EntropyResult(
            text=text,
            entropy=entropy,
            length=len(text),
            is_suspicious=is_suspicious,
            analysis_details=analysis_details
        )
    
    def find_high_entropy_segments(self, text: str, window_size: int = 20) -> List[EntropyResult]:
        """
        Find high-entropy segments in a longer text using sliding window.
        
        Args:
            text: Full text to analyze
            window_size: Size of sliding window for analysis
            
        Returns:
            List of high-entropy segments found
        """
        high_entropy_segments = []
        
        # First, look for obvious patterns
        for pattern in self.suspicious_patterns:
            for match in re.finditer(pattern, text):
                segment = match.group(0)
                if len(segment) >= self.min_length:
                    result = self.analyze_text_segment(segment)
                    if result.is_suspicious:
                        high_entropy_segments.append(result)
        
        # Sliding window analysis for patterns we might have missed
        for i in range(len(text) - window_size + 1):
            segment = text[i:i + window_size]
            
            # Skip if this segment overlaps with already found segments (check interval overlap)
            segment_start, segment_end = i, i + window_size
            if any(self._intervals_overlap(segment_start, segment_end, 
                                         existing.analysis_details.get('start_pos', 0),
                                         existing.analysis_details.get('end_pos', len(existing.text)))
                   for existing in high_entropy_segments):
                continue
            
            result = self.analyze_text_segment(segment)
            if result.is_suspicious:
                # Extend the segment to find natural boundaries
                extended_segment = self._extend_segment(text, i, i + window_size)
                extended_result = self.analyze_text_segment(extended_segment)
                if extended_result.is_suspicious:
                    high_entropy_segments.append(extended_result)
        
        # Remove duplicates and overlapping segments
        return self._deduplicate_segments(high_entropy_segments)
    
    def _matches_suspicious_pattern(self, text: str) -> bool:
        """Check if text matches any suspicious patterns."""
        for pattern in self.suspicious_patterns:
            if re.match(pattern, text):
                return True
        return False
    
    def _estimate_compression_ratio(self, text: str) -> float:
        """
        Estimate compression ratio as a proxy for randomness.
        
        High-entropy strings typically compress poorly.
        """
        if not text:
            return 0.0
        
        try:
            import zlib
            compressed = zlib.compress(text.encode('utf-8'))
            return len(compressed) / len(text.encode('utf-8'))
        except ImportError:
            # Fallback: simple repetition analysis
            unique_chars = len(set(text))
            return unique_chars / len(text) if text else 0
    
    def _extend_segment(self, full_text: str, start: int, end: int) -> str:
        """
        Extend a segment to natural word/token boundaries.
        
        Args:
            full_text: Full text containing the segment
            start: Start position of segment
            end: End position of segment
            
        Returns:
            Extended segment text
        """
        # Extend backwards to word boundary
        while start > 0 and full_text[start - 1].isalnum():
            start -= 1
        
        # Extend forwards to word boundary
        while end < len(full_text) and full_text[end].isalnum():
            end += 1
        
        return full_text[start:end]
    
    def _intervals_overlap(self, start1: int, end1: int, start2: int, end2: int) -> bool:
        """Check if two intervals overlap."""
        return not (end1 <= start2 or end2 <= start1)
    
    def _deduplicate_segments(self, segments: List[EntropyResult]) -> List[EntropyResult]:
        """
        Remove duplicate and heavily overlapping segments.
        
        Args:
            segments: List of entropy results to deduplicate
            
        Returns:
            Deduplicated list
        """
        if not segments:
            return []
        
        # Sort by entropy (highest first)
        sorted_segments = sorted(segments, key=lambda x: x.entropy, reverse=True)
        deduplicated = []
        
        for segment in sorted_segments:
            # Check for significant overlap with existing segments
            overlaps = False
            for existing in deduplicated:
                overlap = self._calculate_overlap(segment.text, existing.text)
                if overlap > 0.7:  # 70% overlap threshold
                    overlaps = True
                    break
            
            if not overlaps:
                deduplicated.append(segment)
        
        return deduplicated
    
    def _calculate_overlap(self, text1: str, text2: str) -> float:
        """Calculate overlap ratio between two text strings."""
        if not text1 or not text2:
            return 0.0
        
        # Find longest common substring
        longer = text1 if len(text1) >= len(text2) else text2
        shorter = text2 if len(text1) >= len(text2) else text1
        
        max_overlap = 0
        for i in range(len(longer) - len(shorter) + 1):
            if longer[i:i + len(shorter)] == shorter:
                max_overlap = len(shorter)
                break
            
            # Check for partial overlaps
            for j in range(1, len(shorter)):
                if longer[i:i + j] == shorter[:j] or longer[i:i + j] == shorter[-j:]:
                    max_overlap = max(max_overlap, j)
        
        return max_overlap / min(len(text1), len(text2))
    
    def get_analysis_stats(self) -> Dict[str, any]:
        """Get analyzer configuration and statistics."""
        return {
            'min_length': self.min_length,
            'entropy_threshold': self.entropy_threshold,
            'suspicious_patterns_count': len(self.suspicious_patterns),
            'charset_patterns_count': len(self.charset_patterns)
        }