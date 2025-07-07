package anthro.guard

import rego.v1

test_allow_valid_request if {
    allow with input as {
        "request": {
            "body": `{"method": "tools/list", "params": {}}`,
            "headers": {
                "content-length": "32",
                "x-request-id": "test-123"
            }
        },
        "source_address": "10.0.0.1"
    }
}

test_deny_unaliased_path if {
    not allow with input as {
        "request": {
            "body": `{"method": "tools/call", "params": {"name": "read_file", "args": {"path": "/etc/passwd"}}}`,
            "headers": {
                "content-length": "80",
                "x-request-id": "test-456"
            }
        },
        "source_address": "10.0.0.1"
    }
}

test_deny_secret_key if {
    not allow with input as {
        "request": {
            "body": `{"method": "tools/call", "params": {"api_key": "sk_test_1234567890abcdef1234567890"}}`,
            "headers": {
                "content-length": "100",
                "x-request-id": "test-789"
            }
        },
        "source_address": "10.0.0.1"
    }
}

test_deny_aws_key if {
    not allow with input as {
        "request": {
            "body": `{"method": "tools/call", "params": {"aws_key": "AKIAIOSFODNN7EXAMPLE"}}`,
            "headers": {
                "content-length": "80",
                "x-request-id": "test-abc"
            }
        },
        "source_address": "10.0.0.1"
    }
}

test_deny_jwt_token if {
    not allow with input as {
        "request": {
            "body": `{"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"}`,
            "headers": {
                "content-length": "200",
                "x-request-id": "test-def"
            }
        },
        "source_address": "10.0.0.1"
    }
}

test_deny_large_request if {
    not allow with input as {
        "request": {
            "body": `{"method": "tools/call", "params": {}}`,
            "headers": {
                "content-length": "2000000",  # 2MB > 1MB limit
                "x-request-id": "test-ghi"
            }
        },
        "source_address": "10.0.0.1"
    }
}

test_deny_blocked_tool if {
    not allow with input as {
        "request": {
            "body": `{"method": "tools/call", "params": {"name": "shell"}}`,
            "headers": {
                "content-length": "60",
                "x-request-id": "test-jkl"
            }
        },
        "source_address": "10.0.0.1"
    }
}

test_allow_aliased_path if {
    allow with input as {
        "request": {
            "body": `{"method": "tools/call", "params": {"name": "read_file", "args": {"path": "FILE_a1b2c3d4"}}}`,
            "headers": {
                "content-length": "90",
                "x-request-id": "test-mno"
            }
        },
        "source_address": "10.0.0.1"
    }
}

test_decision_log_generation if {
    decision_log.timestamp
    decision_log.source_ip
    decision_log.checks
    decision_log.verdict != null
}

test_violation_metrics if {
    violation_metrics.path_violations >= 0
    violation_metrics.secret_violations >= 0
    violation_metrics.entropy_violations >= 0
    violation_metrics.exfiltration_violations >= 0
}