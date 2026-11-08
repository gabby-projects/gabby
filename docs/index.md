# Gabby Documentation

This is the entry point for Gabby's user, architecture, operator, and contributor documentation.
Gabby is an Agent Runtime and Governance Framework: it lets developers define agent
capabilities, govern tool use, and execute requests within explicit runtime contracts. Execution is
stateless between requests; the consuming application owns conversation history and durable memory.
It is designed to complement orchestration frameworks such as LangChain, CrewAI, and IBM BeeAI:
those frameworks can coordinate agents and workflows, while Gabby supplies governed execution for
configured agent requests. Gabby is not intended to replace the host application's orchestration layer.

Gabby is maintained in the `undreamt-oss` GitHub organization. The README introduces the project,
architecture documents explain ownership and contracts, focused guides explain capabilities, and the
roadmap and scorecard separate implementation from release evidence.

## Start here

- [Project overview and quick start](../README.md) — understand Gabby's governance and execution
  boundary and run the offline starter flow.
- [Complete user guide](README_GUIDE.md) — install Gabby, configure providers, define agents, use
  skills, tools, and knowledge, and run the Python, HTTP, and MCP interfaces.
- [Examples](../examples/README.md) — runnable offline examples and a hosted-service example.
- [CLI and API guide](../README.md#cli-and-api) — use the `gabby` developer command line and
  local service.
- [Python HTTP client](CLIENT.md) — call the stateless HTTP API from another Python application.
- [MCP integration](MCP.md) — expose an agent to a local MCP host or import tools from a host-owned
  MCP client.

## Architecture and contracts

- [Architecture overview](ARCHITECTURE.md) — component ownership, request lifecycle, state
  boundaries, policy enforcement, and deployment interfaces.
- [Extension contracts](EXTENSION_CONTRACTS.md) — interface responsibilities, lifecycle ownership,
  concurrency, and failure behavior.
- [Extension guide](EXTENSIONS.md) — build providers, tools, retrievers, policies, and other
  replaceable components.
- [API stability policy](API_STABILITY.md) — current pre-1.0 compatibility rules.
- [Proposed compatibility contract](COMPATIBILITY.md) — candidate public contract for a future 1.0
  release; it is not in force during 0.x.
- [Architecture decision records](architecture/adr/README.md) — accepted design choices and their
  consequences.

## Capabilities

- [Skill registry](SKILL_REGISTRY.md) — skill structure, exact versions, packages, signatures,
  trust, and registry operations.
- [Structured output](STRUCTURED_OUTPUT.md) — JSON Schema contracts for agent responses.
- [Approval handling](APPROVALS.md) — host-owned approval decisions and audit records.
- [SQLite data tool](SQLITE_DATA.md) — bounded read-only SQL against a host-selected database.
- [Sandboxed Python tool](PYTHON_TOOL.md) — execute bounded Python in a per-run container.
- [Training](TRAINING.md) — optional local LoRA adaptation and its separation from runtime
  specialization.

## Operations and security

- [Threat model](THREAT_MODEL.md) — trust boundaries, implemented controls, and residual risks.
- [Operations guide](OPERATIONS.md) — authentication, resource limits, storage, tracing, and
  deployment responsibilities.
- [Scaling and operational tradeoffs](SCALING_AND_OPERATIONS.md) — sync callbacks, vector scale,
  streaming, platform gates, and schema prototyping.
- [Container deployment](DEPLOYMENT_CONTAINER.md) and [Kubernetes reference](DEPLOYMENT_KUBERNETES.md).
- [Security policy](../SECURITY.md) — private vulnerability reporting.

## Contributing and release readiness

- [Contributing](../CONTRIBUTING.md) — development environment, required checks, and change
  expectations.
- [AI usage guide](AI_USAGE.md) — responsible use of AI tools while contributing, including review,
  validation, and data protection.
- [Repository governance](REPOSITORY_GOVERNANCE.md) — Gabby's contribution safeguards and repository
  settings maintainers must verify.
- [Release procedure](RELEASING.md) — tag validation, build, attestations, and PyPI publishing.
- [Project roadmap](../ROADMAP.md) and [readiness scorecard](PROJECT_SCORECARD.md) — current
  implementation evidence and open release gates.

## Release status

Gabby is pre-1.0 alpha software. Local tests and static checks establish only the behaviors they
exercise; they do not certify a hosted deployment, every model/provider combination, or every
container host and engine. Review the threat model and scorecard before using sensitive data or
making production claims. See [the 0.1.0a1 release notes](../CHANGELOG.md) for the scope of the
planned first alpha.
