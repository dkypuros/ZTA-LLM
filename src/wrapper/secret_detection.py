"""
Multi-Pattern Secret Detection Implementation

Implements regex-based secret detection as described in the paper's
Layer 1 security controls. Detects API keys, certificates, passwords,
and other sensitive patterns.
"""

import re
import base64
from typing import List, NamedTuple, Dict, Pattern
from enum import Enum


class SecretType(Enum):
    """Types of secrets that can be detected."""
    API_KEY = "api_key"
    AWS_KEY = "aws_key"
    STRIPE_KEY = "stripe_key"
    JWT_TOKEN = "jwt_token"
    PRIVATE_KEY = "private_key"
    PASSWORD = "password"
    CONNECTION_STRING = "connection_string"
    CERTIFICATE = "certificate"
    HIGH_ENTROPY = "high_entropy"


class SecretMatch(NamedTuple):
    """Represents a detected secret with context."""
    secret_type: SecretType
    matched_text: str
    start_position: int
    end_position: int
    confidence: float
    context: str


class SecretDetector:
    """
    Multi-pattern secret detection for prompt sanitization.
    
    Implements the regex-based secret detection mentioned in the paper's
    Layer 1 application guards.
    """
    
    def __init__(self, sensitivity_level: str = "high"):
        self.sensitivity_level = sensitivity_level
        self._compile_patterns()
        
    def _compile_patterns(self) -> None:
        """Compile regex patterns for different secret types."""
        
        # API Key patterns
        self.patterns: Dict[SecretType, List[Pattern]] = {
            SecretType.API_KEY: [
                re.compile(r'(?i)api[_-]?key[_-]?[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?'),
                re.compile(r'(?i)apikey[_-]?[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?'),
                re.compile(r'(?i)api[_-]?token[_-]?[:=]\s*["\']?([a-zA-Z0-9_-]{16,})["\']?'),
            ],
            
            SecretType.AWS_KEY: [
                re.compile(r'AKIA[0-9A-Z]{16}'),  # AWS Access Key ID
                re.compile(r'(?i)aws[_-]?access[_-]?key[_-]?id[_-]?[:=]\s*["\']?(AKIA[0-9A-Z]{16})["\']?'),
                re.compile(r'(?i)aws[_-]?secret[_-]?access[_-]?key[_-]?[:=]\s*["\']?([a-zA-Z0-9/+=]{40})["\']?'),
            ],
            
            SecretType.STRIPE_KEY: [
                re.compile(r'sk_test_[a-zA-Z0-9]{24,}'),  # Stripe test secret key
                re.compile(r'sk_live_[a-zA-Z0-9]{24,}'),  # Stripe live secret key
                re.compile(r'pk_test_[a-zA-Z0-9]{24,}'),  # Stripe test publishable key
                re.compile(r'pk_live_[a-zA-Z0-9]{24,}'),  # Stripe live publishable key
            ],
            
            SecretType.JWT_TOKEN: [
                re.compile(r'eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*'),  # JWT pattern
            ],
            
            SecretType.PRIVATE_KEY: [
                re.compile(r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----'),
                re.compile(r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----'),
                re.compile(r'-----BEGIN\s+EC\s+PRIVATE\s+KEY-----'),
            ],
            
            SecretType.PASSWORD: [
                re.compile(r'(?i)password[_-]?[:=]\s*["\']?([^"\'\s]{8,})["\']?'),
                re.compile(r'(?i)passwd[_-]?[:=]\s*["\']?([^"\'\s]{8,})["\']?'),
                re.compile(r'(?i)pwd[_-]?[:=]\s*["\']?([^"\'\s]{8,})["\']?'),
            ],
            
            SecretType.CONNECTION_STRING: [
                re.compile(r'(?i)mongodb://[^:\s]+:[^@\s]+@[^/\s]+'),
                re.compile(r'(?i)mysql://[^:\s]+:[^@\s]+@[^/\s]+'),
                re.compile(r'(?i)postgresql://[^:\s]+:[^@\s]+@[^/\s]+'),
                re.compile(r'(?i)Server=.+;Database=.+;User\s+Id=.+;Password=.+'),
            ],
            
            SecretType.CERTIFICATE: [
                re.compile(r'-----BEGIN\s+CERTIFICATE-----'),
                re.compile(r'-----BEGIN\s+PUBLIC\s+KEY-----'),
            ]
        }
    
    def detect_secrets(self, text: str) -> List[SecretMatch]:
        """
        Detect all secrets in the given text.
        
        Args:
            text: Text to scan for secrets
            
        Returns:
            List of SecretMatch objects for each detected secret
        """
        matches = []
        
        for secret_type, patterns in self.patterns.items():
            for pattern in patterns:
                for match in pattern.finditer(text):
                    secret_match = SecretMatch(
                        secret_type=secret_type,
                        matched_text=match.group(0),
                        start_position=match.start(),
                        end_position=match.end(),
                        confidence=self._calculate_confidence(secret_type, match.group(0)),
                        context=self._extract_context(text, match.start(), match.end())
                    )
                    matches.append(secret_match)
        
        # Add high-entropy string detection
        if self.sensitivity_level in ["high", "paranoid"]:
            matches.extend(self._detect_high_entropy(text))
        
        return sorted(matches, key=lambda x: x.start_position)
    
    def _calculate_confidence(self, secret_type: SecretType, text: str) -> float:
        """Calculate confidence score for a detected secret."""
        confidence = 0.8  # Base confidence
        
        # Adjust based on secret type specificity
        if secret_type in [SecretType.AWS_KEY, SecretType.STRIPE_KEY]:
            confidence = 0.95  # Very specific patterns
        elif secret_type == SecretType.JWT_TOKEN:
            if self._is_valid_jwt_structure(text):
                confidence = 0.9
        elif secret_type == SecretType.PASSWORD:
            confidence = 0.6  # More generic pattern
            
        return confidence
    
    def _is_valid_jwt_structure(self, token: str) -> bool:
        """Validate JWT structure."""
        parts = token.split('.')
        if len(parts) != 3:
            return False
            
        try:
            # Try to decode header and payload
            base64.urlsafe_b64decode(parts[0] + '==')
            base64.urlsafe_b64decode(parts[1] + '==')
            return True
        except Exception:
            return False
    
    def _extract_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Extract context around a secret match."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        context = text[context_start:context_end]
        
        # Mask the actual secret in the context
        secret_length = end - start
        masked_secret = "*" * min(secret_length, 10)
        return context.replace(text[start:end], masked_secret)
    
    def _detect_high_entropy(self, text: str) -> List[SecretMatch]:
        """
        Detect high-entropy strings that might be secrets.
        
        Implements entropy analysis mentioned in the paper.
        """
        matches = []
        
        # Look for strings that might be base64-encoded secrets
        b64_pattern = re.compile(r'[A-Za-z0-9+/]{20,}={0,2}')
        
        for match in b64_pattern.finditer(text):
            candidate = match.group(0)
            entropy = self._calculate_entropy(candidate)
            
            if entropy > 4.5:  # High entropy threshold
                secret_match = SecretMatch(
                    secret_type=SecretType.HIGH_ENTROPY,
                    matched_text=candidate,
                    start_position=match.start(),
                    end_position=match.end(),
                    confidence=min(entropy / 6.0, 0.9),  # Scale entropy to confidence
                    context=self._extract_context(text, match.start(), match.end())
                )
                matches.append(secret_match)
        
        return matches
    
    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not text:
            return 0.0
            
        # Count character frequencies
        char_counts = {}
        for char in text:
            char_counts[char] = char_counts.get(char, 0) + 1
        
        # Calculate entropy
        entropy = 0.0
        text_length = len(text)
        
        for count in char_counts.values():
            probability = count / text_length
            if probability > 0:
                entropy -= probability * (probability.bit_length() - 1)
        
        return entropy
    
    def sanitize_text(self, text: str, replacement: str = "[REDACTED]") -> str:
        """
        Remove detected secrets from text.
        
        Args:
            text: Text to sanitize
            replacement: String to replace secrets with
            
        Returns:
            Sanitized text with secrets replaced
        """
        secrets = self.detect_secrets(text)
        sanitized = text
        
        # Replace secrets in reverse order to maintain positions
        for secret in reversed(secrets):
            if secret.confidence >= 0.7:  # Only replace high-confidence matches
                sanitized = (
                    sanitized[:secret.start_position] +
                    replacement +
                    sanitized[secret.end_position:]
                )
        
        return sanitized
    
    def get_detection_stats(self) -> Dict[str, int]:
        """Get detection statistics for monitoring."""
        pattern_count = sum(len(patterns) for patterns in self.patterns.values())
        return {
            "total_patterns": pattern_count,
            "secret_types": len(self.patterns),
            "sensitivity_level": self.sensitivity_level
        }