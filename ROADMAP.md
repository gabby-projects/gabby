<!--
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright 2026-present Gabby Contributors.
-->

# Roadmap

Gabby is an **Agent Runtime and Governance Framework**. It governs a configured agent's model and
tool execution through instructions, skills, policies, approvals, verification, and bounded runtime
contracts. It is designed to complement orchestration frameworks; it does not provide a competing
multi-agent workflow builder. See the [project overview](README.md) and [architecture](docs/ARCHITECTURE.md)
for the current product boundary.

## Available today

- Async-first Python runtime with synchronous wrappers, a versioned FastAPI service, and a stateless
  HTTP client. The host owns conversation history, user identity, and durable application state.
- Hosted model integrations for OpenAI-compatible endpoints, Ollama, Hugging Face Inference
  Providers, Anthropic Messages, and Gemini GenerateContent. Gabby does not train models, change
  model weights, or load model adapters.
- Agent definitions and reusable skill packages, with deterministic or optional model-based skill
  selection, optional bounded planning, typed tool contracts, structured output validation, and
  explicit runtime policies.
- Governed tool execution with bounded calls, deadlines, cancellation, optional host approval,
  verification, tracing, and optional per-run container isolation for supported tools.
- Optional MCP client/server integration, OpenTelemetry spans, signed audit records, LF TRACE
  evidence, and lightweight HTTP adapters for LangGraph, CrewAI, and n8n. These integrations remain
  optional and do not replace the host application's orchestration or deployment responsibilities.
- Knowledge retrieval through injected retrievers, SQLite FTS5 lexical search and SQLite vector
  search, replaceable embedding and reranking providers, and built-in UTF-8 plain-text and Markdown
  ingestion. Specialized formats require a host-provided parser.
- Explicit, stateless child-agent delegation through `AgentTool`. The host still owns orchestration,
  routing, shared state, and coordination among agents.

## Current boundaries

- Gabby does not provide model training, fine-tuning, PEFT adapters, or other model-weight
  manipulation.
- Built-in file ingestion accepts `.txt`, `.log`, `.md`, and `.markdown`. It does not include PDF,
  OCR, office-document, email, archive, or structured-data parsers. See
  [ADR 0125](docs/architecture/adr/0125-plain-text-markdown-ingestion.md).
- Retrieval supplies reference context; it does not guarantee model behavior or enforce policy.
  Instructions guide responses, while runtime policy and capability checks govern execution.
- The service is single-tenant per instance. The host must authenticate callers and select
  user-specific configuration, retrieval scope, and storage.
- Built-in persistence is SQLite and is intended for local or single-service use. Gabby does not
  ship PostgreSQL storage adapters.
- MCP, OpenTelemetry, signed audit, and orchestrator adapters are optional integrations. They do not
  make Gabby a multi-agent workflow orchestrator or replace host ownership of identity, state,
  credentials, deployment, and telemetry retention.
- The starter skill bundles, prewarmed sandbox pool, and TypeScript, Go, and Rust clients are under
  development in the current work branch. Their presence in this checkout is not evidence of a
  published, signed release or production acceptance.

## Work to prioritize

1. Keep public documentation, examples, dependency metadata, and CI aligned with the supported
   runtime and its explicit boundaries.
2. Expand cross-platform and deployment acceptance for the existing sandbox, API, and service
   contracts; distinguish verified behavior from untested deployment assumptions.
3. Improve operational guidance for host-owned identity, tenant isolation, retrieval scoping,
   secrets, persistence, and observability integrations.
4. Strengthen contract tests around policy enforcement, cancellation, bounded execution, and
   host-injected extensions when those contracts change.

New capabilities should state their owner, trust boundary, lifecycle, limits, and failure behavior.
Update the relevant user guide and architecture decision record whenever a change alters a public
contract. Avoid implying that a model instruction, skill, or retrieved document can override
runtime-enforced governance.
