# ZTA-LLM Project Structure

## Architecture Overview

Based on the Security Impedance framework from the paper, the system implements multi-layer defense:

```
┌─────────────────┐
│   User Input    │
└────────┬────────┘
         │
    ┌────▼────┐        ┌──────────────┐
    │ Wrapper │        │ Prompt Guard │ Layer 1: Application
    │  + Alias├────────┤  + Padding   │ (In-process validation)
    └────┬────┘        └──────────────┘
         │
    ┌────▼────┐        ┌──────────────┐
    │  Envoy  │        │     OPA      │ Layer 2: Service Mesh
    │  Sidecar├────────┤ Data Firewall│ (Transit validation)
    └────┬────┘        └──────────────┘
         │
    ┌────▼────┐        ┌──────────────┐
    │ Network │        │   Egress     │ Layer 3: Infrastructure
    │ Policy  ├────────┤   Firewall   │ (Network isolation)
    └────┬────┘        └──────────────┘
         │
         ▼
   [Anthropic API / Local vLLM]
```

## Directory Structure

```
ZTA-LLM/
├── README.md                      # Main documentation
├── CHANGELOG.md                   # Version history
├── docker-compose.yml             # Development environment
├── Makefile                       # Build automation
├── 
├── src/                           # Core source code
│   ├── wrapper/                   # Layer 1: Application guards
│   │   ├── __init__.py
│   │   ├── path_aliasing.py       # Deterministic path aliasing
│   │   ├── prompt_padding.py      # Constant-length padding
│   │   ├── secret_detection.py    # Regex-based secret detection
│   │   └── entropy_analysis.py    # High-entropy string detection
│   │
│   ├── agent_client/              # Anthropic Claude integration
│   │   ├── __init__.py
│   │   ├── claude_wrapper.py      # Secure Claude API wrapper
│   │   ├── mcp_client.py          # MCP protocol implementation
│   │   └── request_sanitizer.py   # Request validation
│   │
│   ├── mcp_server/                # Tool router and validation
│   │   ├── __init__.py
│   │   ├── server.py              # Main MCP server
│   │   ├── tool_registry.py       # Tool management
│   │   ├── schema_validator.py    # JSON schema validation
│   │   └── local_inference.py     # vLLM integration
│   │
│   ├── security/                  # Security frameworks
│   │   ├── __init__.py
│   │   ├── formal_verification.py # Lean 4 stubs
│   │   ├── red_team.py            # Security testing
│   │   └── performance.py         # Benchmarking
│   │
│   └── monitoring/                # Observability
│       ├── __init__.py
│       ├── metrics.py             # Performance tracking
│       └── audit_logger.py        # Security audit logs
│
├── deploy/                        # Deployment manifests
│   ├── docker/                    # Container definitions
│   │   ├── Dockerfile.wrapper     # Layer 1 container
│   │   ├── Dockerfile.mcp         # MCP server container
│   │   └── Dockerfile.vllm        # Local inference container
│   │
│   ├── k8s/                       # Kubernetes manifests
│   │   ├── base/                  # Core components
│   │   ├── security/              # SecurityContextConstraints, Gatekeeper
│   │   ├── mesh/                  # Istio + OPA policies
│   │   └── monitoring/            # Prometheus, Grafana
│   │
│   └── gitops/                    # ArgoCD applications
│       ├── app-of-apps.yaml
│       └── environments/
│
├── test/                          # Test suites
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   ├── security/                  # Red team tests
│   │   ├── test_secret_injection.py
│   │   ├── test_context_accumulation.py
│   │   └── test_tool_reflection.py
│   └── performance/               # Performance benchmarks
│
├── data/                          # Sample datasets
│   ├── synthetic_pii/             # Test PII data
│   ├── fake_api_keys/             # Test secrets
│   └── file_structures/           # Test directory structures
│
├── docs/                          # Documentation
│   ├── architecture.md            # Detailed architecture
│   ├── security_model.md          # Threat model and mitigations
│   ├── deployment_guide.md        # Deployment instructions
│   └── api_reference.md           # API documentation
│
└── ci/                            # CI/CD configuration
    ├── github-actions/             # GitHub Actions workflows
    ├── security-scans/             # Security regression tests
    └── benchmarks/                 # Automated performance tests
```

## Key Technical Components

### Layer 1: Application Guards
- **Path Aliasing**: SHA256-based deterministic aliasing to prevent path disclosure
- **Prompt Padding**: Constant-length padding to prevent side-channel attacks
- **Secret Detection**: Regex patterns for API keys, certificates, etc.
- **Entropy Analysis**: Statistical detection of high-entropy strings

### Layer 2: Service Mesh Enforcement
- **OPA Policies**: Rego-based data firewall rules
- **Istio Integration**: Service mesh for traffic interception
- **Schema Validation**: Strict JSON schema enforcement
- **Transit Encryption**: mTLS for all internal communication

### Layer 3: Infrastructure Security
- **NetworkPolicy**: Kubernetes-native egress restrictions
- **SecurityContextConstraints**: Pod-level security controls
- **Seccomp/AppArmor**: Syscall and file access restrictions
- **Egress Firewall**: IP-level traffic filtering

## Development Phases

1. **Phase 1**: Docker containerized development environment
2. **Phase 2**: Core security impedance implementation
3. **Phase 3**: MCP server and tool integration
4. **Phase 4**: Red team testing and validation
5. **Phase 5**: Kubernetes deployment and GitOps
6. **Phase 6**: Performance optimization and monitoring