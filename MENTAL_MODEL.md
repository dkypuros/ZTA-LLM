# Mental Model: Understanding ZTA-LLM Security Architecture

> **🧠 START HERE** for the high-level picture before diving into code.

This document explains how we wrapped the unmodified Model Context Protocol (MCP) in a production-grade security envelope. The goal is to block data exfiltration and other abuses while keeping performance tight and compatibility perfect.

---

## The Core Insight: Security Impedance

Security impedance is deliberate resistance. We slow or stop malicious requests without interrupting legitimate traffic—much like electrical impedance restricts harmful current without breaking the circuit.

**Key principle**: MCP's wire format stays untouched. Instead, we place three concentric validation layers around every request and response.

---

## 🎯 The Big Picture

### What We Built

We took stock MCP and slid it into a three-layer **security onion** that keeps sensitive content private while adding only microseconds of latency:

```
┌─────────────────────────────────────────────────────────────┐
│                    External Agent (Claude)                  │
│                   ▲ Standard MCP calls                     │
└─────────────────────┼───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│ Layer 1: Application Guards (FastAPI Wrapper)               │
│ • Path aliasing: /etc/passwd → FILE_abc123                 │
│ • Secret scrubbing: sk_live_xxx → [REDACTED]               │
│ • Prompt padding: constant length to hide size signals     │
└─────────────────────┼───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│ Layer 2: Service Mesh (Envoy + OPA Data Firewall)           │
│ • Transit validation: examine every MCP message            │
│ • Policy enforcement: block unaliased paths & secrets      │
│ • Audit logging: full decision trail                       │
└─────────────────────┼───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│ Layer 3: Infrastructure (Kubernetes Network Policies)      │
│ • Network isolation: approved egress only                  │
│ • Container security: non-root, read-only filesystem       │
│ • Resource limits: reduce DoS surface                      │
└─────────────────────┼───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              Internal MCP Server & vLLM                    │
│                    (Private Inference)                     │
└─────────────────────────────────────────────────────────────┘
```

### The Hybrid Split

**Public planning (outside OpenShift)**
Claude (via Anthropic API) handles tool orchestration and "thinking." It speaks plain MCP but never sees unmasked secrets or raw paths.

**Private inference (inside OpenShift)**
A vLLM server performs heavy model work with real data. Three security layers plus network policies prevent leakage.

---

## 🔐 How We Extended MCP Without Breaking It

### Protocol Stays the Same

No new fields, verbs, or tags. Any vanilla MCP client still works.

### Server Behavior Tightened

* Stricter JSON-schema checks
* One-megabyte request cap
* Explicit method allow-list
* Per-tool execution timeouts
* `security_validated: true` added to responses for at-a-glance assurance

These checks live in `src/mcp_server/server.py`, invisible to clients but uncompromising on safety.

### Extending the Model Context Protocol

The original MCP spec only defined the basic JSON-RPC-style verbs—tools/list, tools/call, resources/read, and so on—and left trust decisions to the application that used it. In our implementation the wire format stays compatible, but the server now insists on extra guardrails before it will accept a call. First, every request body must satisfy a stricter JSON schema; second, the server time-boxes tool execution, tracks request sizes, and blocks any method that is not on an explicit allow-list. Those checks are enforced inside the `MCPServer` class, so from a client's point of view MCP looks unchanged yet behaves much more cautiously.

### Two Defensive Rings Around MCP

* **Wrapper layer** (Python) aliases paths, scrubs secrets, pads prompts.
* **Mesh layer** (Envoy + OPA) rejects what the wrapper missed—unaliased paths, API keys, high-entropy blobs, oversize bodies—and logs every verdict.

If both layers pass, the MCP server proceeds. If either fails, the request dies before reaching the model.

### Tags and Metadata

We avoided new MCP keys. Instead:

* Envoy injects headers (`X-ZTA-Security-Layer`, `X-Request-ID`).
* OPA writes structured decision logs.
* MCP responses include `security_validated` and timing fields—but those stay within the JSON-RPC response envelope, so compatibility remains.

---

## 🏗️ Where the Agent Code Lives and Where the Model Lives

* The **Claude Code-SDK agent** runs outside. It drives workflows but receives only aliased paths and redacted secrets.
* The **vLLM inference engine** runs inside OpenShift, isolated by NetworkPolicy; only outbound to Anthropic planning is allowed.

Requests flow:

1. Agent sends MCP call.
2. Wrapper cleans and validates.
3. Envoy → OPA firewall enforces Rego rules.
4. MCP server does schema and timeout checks.
5. vLLM generates the answer inside the cluster.

Private data never leaves Layer 3.

---

## 🛡️ The Three Security Layers in Practice

### Layer 1 – Application Guards

Located in `src/wrapper/`. Performs deterministic path aliasing, multi-pattern secret detection with entropy analysis, constant-length padding, and initial schema validation. Adds roughly 0.02 ms per call.

### Layer 2 – Service Mesh

Defined in `deploy/envoy/` and `deploy/opa/`. Envoy streams every request body to OPA; Rego policies veto raw paths, secrets, oversize payloads, banned tool names, and other exfiltration indicators. Adds ~0.12 ms.

### Layer 3 – Infrastructure

Kubernetes manifests in `deploy/k8s/`. Egress is whitelisted, containers run non-root with read-only filesystems, seccomp/AppArmor profiles are enabled, and resources are capped. Latency impact is negligible.

---

## 🚀 Design Decisions

Compatibility first, defense-in-depth, fail-safe by default, transparent auditing, and micro-second-level performance overhead—all validated by automated tests (`TEST_RESULTS.md`).

---

## 📁 Where to Look Next

`src/wrapper/` for Layer 1 code.
`deploy/opa/policies/` for Rego firewall.
`src/mcp_server/` for tightened MCP logic.
`test_*` scripts for validation evidence.

---

## 🔍 Validation Snapshot

Full test suites show 0.234 ms average overhead, every known secret-injection or path-traversal attack blocked, and zero changes required in existing MCP clients.

This enhanced document keeps the original structure but clarifies rationale, responsibilities, and file locations so new contributors find the right entry points fast.