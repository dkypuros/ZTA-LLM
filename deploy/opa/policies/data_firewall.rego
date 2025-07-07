# Data Firewall Policy - Layer 2 Security Impedance
# 
# Implements the OPA policy described in the paper for service mesh
# enforcement. Prevents data exfiltration through transit validation.
#
# NOTE: This is the FULL policy with entropy and size checks.
# See security-impedance-core/policies/firewall.rego for minimal reference implementation.

package anthro.guard

import rego.v1

# Default deny - security by default
default allow := false

# Decision log for audit trail
default decision_log := {}

# Main allow rule - all conditions must be met
allow if {
    not has_unaliased_paths
    not has_obvious_secrets
    not has_suspicious_entropy
    not has_exfiltration_patterns
    has_valid_schema
    within_size_limits
    not has_malicious_tools
}

# Generate detailed decision log
decision_log := {
    "timestamp": time.now_ns(),
    "request_id": input.request.headers["x-request-id"],
    "user_agent": input.request.headers["user-agent"],
    "source_ip": input.request.remote_addr,
    "checks": {
        "unaliased_paths": has_unaliased_paths,
        "obvious_secrets": has_obvious_secrets,
        "suspicious_entropy": has_suspicious_entropy,
        "exfiltration_patterns": has_exfiltration_patterns,
        "valid_schema": has_valid_schema,
        "size_limits": within_size_limits,
        "malicious_tools": has_malicious_tools
    },
    "verdict": allow,
    "blocked_content_sample": blocked_content_sample
}

# Check for unaliased file paths
has_unaliased_paths if {
    some path_match in path_violations
    path_match
}

path_violations contains violation if {
    # Unix-style paths
    regex.match(`/[a-zA-Z0-9_\-./~]{3,}`, input.request.body)
    not regex.match(`FILE_[a-f0-9]{8}`, input.request.body)
    violation := "unaliased_unix_path"
}

path_violations contains violation if {
    # Windows-style paths  
    regex.match(`[A-Za-z]:\\[a-zA-Z0-9_\-\\. ]{2,}`, input.request.body)
    violation := "unaliased_windows_path"
}

path_violations contains violation if {
    # Relative paths that should be aliased
    regex.match(`\.\./[a-zA-Z0-9_\-./]{2,}`, input.request.body)
    violation := "unaliased_relative_path"
}

# Check for obvious secrets (complementing Layer 1)
has_obvious_secrets if {
    some secret_match in secret_violations
    secret_match
}

secret_violations contains violation if {
    # API keys
    regex.match(`(?i)sk[-_](?:test|live)[-_][a-zA-Z0-9]{24,}`, input.request.body)
    violation := "stripe_secret_key"
}

secret_violations contains violation if {
    # AWS credentials
    regex.match(`AKIA[0-9A-Z]{16}`, input.request.body)
    violation := "aws_access_key"
}

secret_violations contains violation if {
    # Generic API key patterns
    regex.match(`(?i)api[-_]?key[-_]?[:=]\s*["\']?[a-zA-Z0-9_-]{16,}`, input.request.body)
    violation := "generic_api_key"
}

secret_violations contains violation if {
    # JWT tokens
    regex.match(`eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*`, input.request.body)
    violation := "jwt_token"
}

secret_violations contains violation if {
    # Private keys
    contains(input.request.body, "-----BEGIN") 
    contains(input.request.body, "PRIVATE KEY-----")
    violation := "private_key"
}

# Check for suspicious high-entropy content
has_suspicious_entropy if {
    some entropy_pattern in entropy_violations
    entropy_pattern
}

entropy_violations contains violation if {
    # Long base64-like strings
    regex.match(`[A-Za-z0-9+/]{40,}={0,2}`, input.request.body)
    violation := "base64_content"
}

entropy_violations contains violation if {
    # Long hex strings (potential hashes/keys)
    regex.match(`[A-Fa-f0-9]{32,}`, input.request.body)
    violation := "hex_content"
}

# Check for data exfiltration patterns
has_exfiltration_patterns if {
    some exfil_pattern in exfiltration_violations
    exfil_pattern
}

exfiltration_violations contains violation if {
    # Database dump patterns
    contains(strings.to_lower(input.request.body), "select * from")
    violation := "sql_dump_attempt"
}

exfiltration_violations contains violation if {
    # File system enumeration
    regex.match(`(?i)(ls|dir|find)\s+[a-zA-Z0-9_\-./]+`, input.request.body)
    violation := "filesystem_enumeration"
}

exfiltration_violations contains violation if {
    # Log file access patterns
    contains(strings.to_lower(input.request.body), "/var/log/")
    violation := "log_access_attempt"
}

exfiltration_violations contains violation if {
    # Config file access
    regex.match(`(?i)(config|\.env|\.ini|\.conf)`, input.request.body)
    violation := "config_access_attempt"
}

# Schema validation
has_valid_schema if {
    # Check if request body is valid JSON
    json.is_valid(input.request.body)
    
    # Parse and validate structure
    request_data := json.unmarshal(input.request.body)
    
    # Required fields for MCP requests
    request_data.method
    request_data.params
    
    # Method must be in allowed list
    request_data.method in allowed_methods
}

allowed_methods := {
    "tools/list",
    "tools/call", 
    "resources/list",
    "resources/read",
    "prompts/list",
    "prompts/get"
}

# Size limits to prevent abuse
within_size_limits if {
    content_length := to_number(input.request.headers["content-length"])
    content_length <= max_content_length
}

max_content_length := 1048576  # 1MB limit

# Tool safety validation
has_malicious_tools if {
    request_data := json.unmarshal(input.request.body)
    request_data.method == "tools/call"
    
    # Check tool name against blocklist
    tool_name := request_data.params.name
    tool_name in blocked_tools
}

blocked_tools := {
    "shell",
    "exec", 
    "eval",
    "subprocess",
    "system",
    "file_write",
    "network_request"
}

# Generate sample of blocked content for logging (sanitized)
blocked_content_sample := sample if {
    not allow
    content := input.request.body
    sample := strings.substring(content, 0, 100)
} else := ""

# Helper functions - using built-in OPA string functions

# Rate limiting helpers (for future enhancement)
rate_limit_key := sprintf("rate_limit:%s", [input.request.remote_addr])

# Monitoring and metrics
violation_metrics := {
    "path_violations": count(path_violations),
    "secret_violations": count(secret_violations), 
    "entropy_violations": count(entropy_violations),
    "exfiltration_violations": count(exfiltration_violations)
}