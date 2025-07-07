"""
Integrated Security Wrapper - Layer 1 Implementation

Combines all Layer 1 security controls into a unified interface.
Implements the Security Impedance framework's application-level guards.
"""

import time
from typing import Dict, List, Optional, NamedTuple
from dataclasses import dataclass
from enum import Enum

from .path_aliasing import PathAliaser, AliasedPath
from .prompt_padding import PromptPadder, PaddedPrompt, PaddingStrategy
from .secret_detection import SecretDetector, SecretMatch
from .entropy_analysis import EntropyAnalyzer, EntropyResult


class SecurityLevel(Enum):
    """Security enforcement levels."""
    PERMISSIVE = "permissive"
    NORMAL = "normal"  
    STRICT = "strict"
    PARANOID = "paranoid"


class ValidationResult(NamedTuple):
    """Result of security validation."""
    is_safe: bool
    blocked_reason: Optional[str]
    secrets_found: List[SecretMatch]
    entropy_alerts: List[EntropyResult]
    processing_time_ms: float


@dataclass
class SecurityConfig:
    """Configuration for security wrapper."""
    security_level: SecurityLevel = SecurityLevel.NORMAL
    prompt_padding_enabled: bool = True
    path_aliasing_enabled: bool = True
    secret_detection_enabled: bool = True
    entropy_analysis_enabled: bool = True
    
    # Padding configuration
    padding_target_length: int = 4096
    padding_strategy: PaddingStrategy = PaddingStrategy.WHITESPACE
    
    # Detection thresholds
    secret_confidence_threshold: float = 0.7
    entropy_threshold: float = 4.5
    
    # Performance settings
    max_processing_time_ms: float = 15.0  # Paper claims <15ms overhead


class SecurityWrapper:
    """
    Integrated Layer 1 security wrapper.
    
    Implements the complete application-level security impedance
    as described in the paper. Provides unified interface for
    all Layer 1 controls.
    """
    
    def __init__(self, config: SecurityConfig = None):
        self.config = config or SecurityConfig()
        
        # Initialize components based on configuration
        self.path_aliaser = PathAliaser() if self.config.path_aliasing_enabled else None
        
        self.prompt_padder = PromptPadder(
            target_length=self.config.padding_target_length,
            strategy=self.config.padding_strategy
        ) if self.config.prompt_padding_enabled else None
        
        self.secret_detector = SecretDetector(
            sensitivity_level=self.config.security_level.value
        ) if self.config.secret_detection_enabled else None
        
        self.entropy_analyzer = EntropyAnalyzer(
            entropy_threshold=self.config.entropy_threshold
        ) if self.config.entropy_analysis_enabled else None
        
        # Statistics tracking
        self._stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'secrets_detected': 0,
            'entropy_alerts': 0,
            'avg_processing_time_ms': 0.0
        }
    
    def process_prompt(self, prompt: str, context: Dict = None) -> Dict:
        """
        Process a prompt through all Layer 1 security controls.
        
        Args:
            prompt: Original prompt text
            context: Optional context dictionary
            
        Returns:
            Dictionary with processing results and sanitized prompt
        """
        start_time = time.time()
        context = context or {}
        
        try:
            # Step 1: Validate prompt safety
            validation_result = self.validate_prompt(prompt)
            
            if not validation_result.is_safe:
                self._stats['blocked_requests'] += 1
                return {
                    'status': 'blocked',
                    'reason': validation_result.blocked_reason,
                    'secrets_found': validation_result.secrets_found,
                    'entropy_alerts': validation_result.entropy_alerts,
                    'processing_time_ms': validation_result.processing_time_ms
                }
            
            # Step 2: Apply path aliasing
            sanitized_prompt = prompt
            path_mappings = {}
            
            if self.path_aliaser:
                sanitized_prompt = self.path_aliaser.sanitize_text(sanitized_prompt)
                # Store path mappings for later resolution
                path_mappings = {
                    alias.alias_token: alias.original 
                    for alias in self.path_aliaser._alias_cache.values()
                }
            
            # Step 3: Apply prompt padding
            padded_result = None
            if self.prompt_padder:
                padded_result = self.prompt_padder.pad_prompt(sanitized_prompt)
                sanitized_prompt = padded_result.padded_prompt
            
            processing_time = (time.time() - start_time) * 1000
            
            # Update statistics
            self._update_stats(validation_result, processing_time)
            
            return {
                'status': 'success',
                'original_prompt': prompt,
                'sanitized_prompt': sanitized_prompt,
                'path_mappings': path_mappings,
                'padding_info': padded_result._asdict() if padded_result else None,
                'validation_info': validation_result._asdict(),
                'processing_time_ms': processing_time,
                'security_level': self.config.security_level.value
            }
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            return {
                'status': 'error',
                'error': str(e),
                'processing_time_ms': processing_time
            }
    
    def validate_prompt(self, prompt: str) -> ValidationResult:
        """
        Validate prompt against all security checks.
        
        Args:
            prompt: Prompt text to validate
            
        Returns:
            ValidationResult indicating safety and any issues found
        """
        start_time = time.time()
        secrets_found = []
        entropy_alerts = []
        blocked_reason = None
        
        # Secret detection
        if self.secret_detector:
            secrets_found = self.secret_detector.detect_secrets(prompt)
            high_confidence_secrets = [
                s for s in secrets_found 
                if s.confidence >= self.config.secret_confidence_threshold
            ]
            
            if high_confidence_secrets:
                blocked_reason = f"Detected {len(high_confidence_secrets)} high-confidence secrets"
        
        # Entropy analysis for suspicious strings
        if self.entropy_analyzer and not blocked_reason:
            entropy_alerts = self.entropy_analyzer.find_high_entropy_segments(prompt)
            
            if self.config.security_level == SecurityLevel.PARANOID and entropy_alerts:
                blocked_reason = f"Detected {len(entropy_alerts)} high-entropy segments"
        
        # Additional checks based on security level
        if not blocked_reason:
            blocked_reason = self._apply_security_level_checks(prompt)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Check processing time constraint - fail-closed for all security levels
        if processing_time > self.config.max_processing_time_ms:
            blocked_reason = "processing-timeout"
        
        is_safe = blocked_reason is None
        
        return ValidationResult(
            is_safe=is_safe,
            blocked_reason=blocked_reason,
            secrets_found=secrets_found,
            entropy_alerts=entropy_alerts,
            processing_time_ms=processing_time
        )
    
    def _apply_security_level_checks(self, prompt: str) -> Optional[str]:
        """Apply additional checks based on security level."""
        
        if self.config.security_level == SecurityLevel.PERMISSIVE:
            return None
        
        # Check prompt length
        if len(prompt) > 50000:  # Very large prompts are suspicious
            if self.config.security_level in [SecurityLevel.STRICT, SecurityLevel.PARANOID]:
                return "Prompt exceeds maximum safe length"
        
        # Check for obvious data exfiltration attempts
        suspicious_phrases = [
            "print all", "dump all", "show me everything", "export all data",
            "cat /etc/passwd", "ls -la", "SELECT * FROM", "SHOW TABLES"
        ]
        
        prompt_lower = prompt.lower()
        for phrase in suspicious_phrases:
            if phrase in prompt_lower:
                if self.config.security_level in [SecurityLevel.STRICT, SecurityLevel.PARANOID]:
                    return f"Detected suspicious phrase: {phrase}"
        
        return None
    
    def _update_stats(self, validation_result: ValidationResult, processing_time: float):
        """Update internal statistics."""
        self._stats['total_requests'] += 1
        
        if validation_result.secrets_found:
            self._stats['secrets_detected'] += len(validation_result.secrets_found)
        
        if validation_result.entropy_alerts:
            self._stats['entropy_alerts'] += len(validation_result.entropy_alerts)
        
        # Update rolling average processing time
        current_avg = self._stats['avg_processing_time_ms']
        total_requests = self._stats['total_requests']
        
        self._stats['avg_processing_time_ms'] = (
            (current_avg * (total_requests - 1) + processing_time) / total_requests
        )
    
    def get_statistics(self) -> Dict:
        """Get security wrapper statistics."""
        return {
            **self._stats,
            'config': {
                'security_level': self.config.security_level.value,
                'components_enabled': {
                    'path_aliasing': self.config.path_aliasing_enabled,
                    'prompt_padding': self.config.prompt_padding_enabled,
                    'secret_detection': self.config.secret_detection_enabled,
                    'entropy_analysis': self.config.entropy_analysis_enabled
                }
            }
        }
    
    def resolve_path_alias(self, alias_token: str) -> Optional[str]:
        """Resolve a path alias back to original path."""
        if self.path_aliaser:
            return self.path_aliaser.resolve_alias(alias_token)
        return None
    
    def reset_statistics(self):
        """Reset statistics counters."""
        self._stats = {
            'total_requests': 0,
            'blocked_requests': 0,
            'secrets_detected': 0,
            'entropy_alerts': 0,
            'avg_processing_time_ms': 0.0
        }


# Convenience factory functions
def create_development_wrapper() -> SecurityWrapper:
    """Create a wrapper configured for development use."""
    config = SecurityConfig(
        security_level=SecurityLevel.NORMAL,
        padding_target_length=2048,  # Smaller for dev
        max_processing_time_ms=50.0  # More lenient for dev
    )
    return SecurityWrapper(config)


def create_production_wrapper() -> SecurityWrapper:
    """Create a wrapper configured for production use."""
    config = SecurityConfig(
        security_level=SecurityLevel.STRICT,
        padding_target_length=4096,
        max_processing_time_ms=15.0
    )
    return SecurityWrapper(config)


def create_paranoid_wrapper() -> SecurityWrapper:
    """Create a wrapper with maximum security settings."""
    config = SecurityConfig(
        security_level=SecurityLevel.PARANOID,
        padding_target_length=8192,
        entropy_threshold=4.0,  # Lower threshold = more sensitive
        secret_confidence_threshold=0.5,  # Lower threshold = more sensitive
        max_processing_time_ms=25.0  # Allow more time for thorough analysis
    )
    return SecurityWrapper(config)