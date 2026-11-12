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

# Gabby Threat Model

**Status:** initial project threat model; review required before a hosted production claim.  
**Scope:** Gabby core runtime, built-in container-backed shell/filesystem tools, FastAPI service, and
their direct dependencies. The consuming application and deployment add their own assets and
threats.

## Security objectives

Gabby should execute each request with isolated transient state, enforce tool permissions outside
the model, constrain built-in shell and filesystem actions to the configured run environment, bound
common compute and request resources, and avoid exposing provider or tool secrets in API errors.
These controls reduce risk; they do not make arbitrary model output or extension code trustworthy.

## Assets

- Host files, mounted workspaces, knowledge databases, and any data returned by application tools.
- Provider credentials, API bearer tokens, and secrets held by the consuming application.
- The host process, container engine, operating-system kernel, and deployment identity.
- Agent definitions, skills, tool implementations, container images, and Python dependencies.
- Service availability, execution budgets, and any traces or telemetry retained by the deployment.

## Trust boundaries

1. **Caller to service:** requests, supplied context, identity credentials, and request volume are
   untrusted. The HTTP API authenticates execution routes, validates request shape, limits request
   body size and total receive time, coalesces accepted body chunks into one bounded replay buffer,
   and acquires the per-process request/run capacity before reading agent requests. This bounds
   simultaneously buffered agent bodies; `/health` bypasses admission. The `serve` command restricts unauthenticated
   use to loopback; an embedded ASGI deployment that opts out of authentication must enforce its
   own network boundary. The deployment still owns TLS, request-rate limits, ingress controls, and
   distributed capacity management.
2. **Model to runtime:** model text, tool names, arguments, and claimed verification results are
   untrusted. Gabby validates tool identity, arguments, permissions, policy, budgets, and declared
   output schemas before or after the corresponding operation. Instructions and retrieved text are
   not enforcement mechanisms.
3. **Runtime to model, embedding, or vector provider:** request messages and retrieval inputs may
   leave the Gabby process. Hosted model calls can include user input, caller context, selected skill
   instructions, retrieved documents, tool schemas, and tool observations. An embedding provider may
   receive source document text during indexing and task queries during retrieval. A remote vector
   store may retain document text, metadata, and embeddings. Gabby does not control external
   provider retention, routing, or residency. Use only provider and data-handling arrangements
   approved for the data and workload.
4. **Knowledge and environment data to model:** retrieved documents, workspace files, tool output,
   and caller context can contain prompt injection or false information. They are reference data;
   their contents must not change runtime policy or instruction priority.
5. **Gabby process to extension code:** injected Python tools, providers, retrievers, parsers,
   verifiers, and authenticators execute in the host process unless their owner supplies an isolated
   implementation. They are trusted code. Sandbox enforcement rejects host-trusted tools by
   default; setting `policies.require_sandbox: false` is an explicit host trust decision. The
   `sandboxed_python_tool()` helper runs importable handlers inside the configured sandbox.
6. **Runtime to container engine:** the Docker or Podman daemon controls the operating-system
   boundary. Access to its socket or API is highly privileged. A compromised engine, daemon
   credential, kernel, or hypervisor can defeat container isolation.
7. **Container to workspace:** the configured directory is deliberately exposed to the agent. A
   read-only mount permits reads; a read-write mount permits changes to that host directory. The
   mount does not isolate files from the consuming application that owns the directory.
8. **Service to deployment:** Gabby serves one configured agent and one tenant per service instance.
   The deployment must route tenants to separate instances and keep their credentials, storage,
   traces, and sandbox configuration separate.

## Main threats and current controls

| Threat | Current controls | Residual risk |
|---|---|---|
| Prompt injection asks the agent to use an unintended tool or abandon its persona | A default payload filter rejects simple direct instruction-override patterns in user and tool text before text-model calls; explicit tool grants, allowlists, permission checks, schemas, step limits, and runtime-enforced policy still govern actions | The filter is heuristic and may miss obfuscated or indirect attacks. A model may still be manipulated into a harmful action permitted by configuration. Review granted capabilities and verify high-impact outcomes. |
| An agent performs a high-impact action without human review | Tools can require a host approval decision after arguments are validated; missing handlers, invalid decisions, errors, and deadline expiry deny execution; authenticated HTTP principal is passed separately to the approval handler | The application owns reviewer identity, approval UX, and audit retention. Embedded callers must provide only a host-authenticated principal; an approval handler should not treat model context or user metadata as identity. |
| Sensitive prompts, source documents, or retrieval queries leave the application through hosted model, embedding, or vector services | Built-in model and embedding providers require HTTPS for remote endpoints and allow HTTP only on loopback; API credentials stay in host-managed environment variables; the host selects providers and stores | Custom providers and stores own transport security. Gabby cannot enforce provider retention, data residency, or downstream routing. The deployment must approve each model, embedding provider, and vector store for the data. |
| Provider errors expose prompts, credentials, or private upstream details | Built-in model, embedding, and reranking adapters omit HTTP error bodies and suppress HTTP transport and response-parsing exception chains from direct errors; traces record stable error categories, and HTTP/SSE routes return bounded sanitized errors | Custom providers own their exception messages and causes. Direct callers should avoid logging custom-provider exceptions without reviewing the provider contract. |
| Malicious code or a hostile file attempts to access the host | Built-in shell/filesystem tools and Python tools marked sandboxed require per-run isolation by default; Python source and arguments are staged through private read-only mounts; network is disabled; Linux containers default to non-root UID/GID `65532:65532` with numeric non-root overrides, read-only root filesystems, dropped capabilities, `no-new-privileges`, and a bounded `/tmp`; Docker/Podman can select an installed runtime such as gVisor `runsc`; custom `EngineAdapter` implementations can provide microVM backends; image references beginning with an engine option or containing whitespace/control characters are rejected; Windows containers request Hyper-V isolation and Gabby requires Docker Engine 29.1.4 or newer before launch; remote engine API URLs require HTTPS and local HTTP is loopback-only; deployments can require an immutable image digest | Operators must configure an available sandbox; otherwise sandboxed tools fail closed. A custom adapter must enforce and test isolation itself; Gabby does not ship or certify Firecracker or other microVM backends. Digest pinning remains opt-in and operators must enable it and review the selected digest. Windows containers inherit their image-defined user. Native Windows uses whole-number CPU counts and requires an explicit process-limit opt-out because Docker does not document that control for Windows; live enforcement remains unverified. A configured image and its contents remain trusted inputs. Container escape, daemon compromise, kernel flaws, and unsafe engine configuration remain possible. Linux containers share the host kernel unless the selected runtime provides a stronger boundary. |
| A custom domain tool executes outside its intended boundary or receives forged arguments | `tool.execute` uses a fixed agent-configured argv inside the run container, passes arguments as bounded JSON in a random per-call file on a read-only per-run mount, applies the run deadline and output limit, validates declared output schemas, and removes each request file after use. Linux live checks cover Docker and Podman CLI/API adapters. | The configured image, executable, and tool implementation are trusted inputs. The tool can read every argument passed to it and any workspace content exposed to the run. Other host/engine combinations have not been live-validated. |
| A path escapes the configured workspace | Built-in filesystem operations validate paths, reject symlink components, and fail closed when archive entries conflict about a component's type; the consuming application must keep the workspace quiescent for the full run; live checks verify configured workspace mount modes | Gabby cannot enforce that host-side precondition. If another process mutates the workspace during a run, separate archive path checks and operations may race. A read-write mount grants write access to its entire configured directory. |
| A crafted skill archive writes outside its registry, installs corrupted resources, or impersonates a publisher | `.gabskill` installs reject traversal, absolute and non-portable paths, case-folded or Unicode-normalized path collisions, symlinks, special files, duplicate entries, unsupported compression, oversized archives and files, manifest mismatches, and invalid checksums; detached Ed25519 signatures bind the exact archive and canonical file manifest to a host-trusted key ID before extraction, and signature verification is required for installs by default. Host applications must inject `SkillTrustPolicy` with trusted keys before an agent can load installed packages by default. `gabby skill audit --trusted-key KEY_ID=PATH` verifies signed installed content and flags revoked, unknown, or invalid records. Revocation checks remain injectable, and the built-in SQLite store persists signer revocations. | Unsigned installs and loading require explicit development overrides. Hosts must provision trusted public keys out of band and inject the policy. A valid signature establishes publisher key possession, not safety of the skill instructions, which remain untrusted prompt content and can influence a model. Review skill behavior and grant only intended tools and knowledge access. Local provenance can be edited or removed by a registry writer, trusted public-key material remains a construction-time snapshot. Registry directories, trust-key configuration, and package source trees are host-managed. |
| A malicious or compromised skill registry redirects clients, leaks credentials, or substitutes a package | The async client requires HTTPS remotely, rejects redirects and credential-bearing registry URLs, derives artifact paths from the configured origin rather than catalog URLs, bounds catalog/package/signature responses and request deadlines, requires an exact version, verifies a publisher signature from a host-managed key, and checks signed package identity before final install | Catalog metadata is untrusted and may hide or replay older signed versions. Signing keys establish authority only to the extent that the host trust map is correct; provisioning, rotation, revocation, and registry write authorization remain operator responsibilities. A correctly signed skill may still contain unsafe instructions. |
| Tool code accesses credentials or performs unrelated host actions | Python handlers are labeled `host_trusted`; sandbox enforcement rejects them by default unless the host sets `require_sandbox: false`; `sandboxed_python_tool()` and `python_run_tool()` execute Python only inside the configured per-run sandbox; provider credentials are configured outside agent YAML | The host application can register unsafe handlers or pass secrets to them when explicitly opting out. Sandboxed Python can still use everything exposed by its image, mounted workspace, and kernel. |
| Agent execution consumes excessive resources | Agent YAML is limited to 10 MiB, skill manifests to 1 MiB, each skill text resource to 10 MiB with bounded reads, and one agent to 256 resolved skills with combined agent/global/skill text limited to its model-request budget capped at 16 MiB; run deadlines, step limits, tool timeouts, per-tool serialized result caps, a 100-document retrieval ceiling and 1 MiB default retrieval-context cap, a shared 1 MiB sandbox stdout/stderr cap that stops CLI engine output early, per-process API concurrency cap, container CPU/memory/process limits, bounded plain-text and Markdown ingestion, and a 65,536-dimension ceiling on stored vectors | Retrieval result checks happen after the custom retriever returns, so they do not bound its internal allocations or work before return. Tool result caps likewise apply after a trusted host handler returns. Custom parsers are trusted in-process code and may consume unbounded CPU or memory; isolate complex or hostile-input parsers outside the runtime. Exact SQLite vector search scans all eligible records and costs O(records × dimensions), so hosts must bound corpus size or move large indexes to a specialized backend. The host-trusted callback pool has bounded workers and queue, and skips timed-out callbacks that have not started; already-running synchronous tool handlers can observe a `ToolContext` cancellation token when they opt in, but handlers that ignore it cannot be forcibly stopped. Disk usage in a read-write workspace is not quota-limited. |
| Unauthenticated or excessive API requests exhaust the service | Run/stream endpoints require an authenticator unless local unauthenticated mode is explicitly selected; optional JWT auth verifies a fixed asymmetric algorithm, issuer, audience, expiration, and subject from a configured HTTPS JWKS endpoint or bounded OIDC discovery with exact issuer matching; custom authenticator calls have a configurable five-second default timeout and fail with sanitized HTTP 503 on error or timeout; optional issuer-scope mapping translates claims to Gabby capabilities and drops unmapped claims; an injected revocation checker can require `jti` and check it on every request, returning unavailable on backend failure; the built-in SQLite checker persists issuer-scoped revocations and exposes expired-record cleanup; route requirements are checked against the principal before execution; the per-process slot is acquired before buffering a request body, which is then bounded by bytes and total receive time; active run/stream and body admission return HTTP 429 when full; `/health` bypasses admission | Scope mappings and route requirements remain host-configured. Custom authenticators must clean up resources when cancellation propagates. Revocation propagation across distributed stores remains host-owned; requests racing with revocation can pass if the check happens first. Authentication remains single-tenant. Per-process admission does not limit concurrent connections. The host owns request-rate and connection limiting, distributed quotas, TLS, and process supervision. `/health` is public. |
| Container image or package is malicious or changes after review | Agent definitions select images; `require_image_digest` can reject mutable image tags; networking is disabled after container start; Python dependencies use a lockfile; release wheel and source distributions receive signed GitHub build provenance attestations | Digest enforcement is opt-in and image pulls happen through the host engine. Consumers must verify artifact attestations against the expected repository and signer workflow; provenance does not prove that source code or build dependencies are benign. |
| Secrets or private data reach an external text model or appear in results | A default payload filter redacts common email, phone, and recognizable token patterns from outbound text-model requests and response text; hosts can add pre- and post-call filters; credentials stay outside agent YAML; retrieved text is marked as untrusted reference data | Redaction patterns are heuristic and incomplete; streaming default redaction evaluates each provider delta, so a pattern split across chunks may evade redaction. The default filter preserves structured tool-call arguments. Providers, tools, and tracers may log or transmit data elsewhere. Successful tool results may contain sensitive values. Trace retention, access controls, and deletion are deployment concerns and need stronger end-to-end review. |
| One tenant reads or affects another tenant's data | One agent and tenant per service instance; run state is request-scoped | A shared deployment can still misroute requests or reuse external stores/secrets across instances. Gabby does not provide shared-process tenant isolation. |

## Explicitly out of scope for current guarantees

- A malicious host administrator, kernel, hypervisor, container daemon, or Python extension.
- Network isolation for host-trusted tools, providers, ingestion processes, or the image-pull phase.
- Allowlisted container egress, distributed request quotas, distributed token
  revocation propagation,
  and multi-tenant authorization.
- Disk quotas for writable workspace mounts or durable application-managed state.
- Automatic safety certification of user-supplied images, skills, tools, or model providers.

## Release acceptance gates

Before claiming hosted production readiness, the project should maintain evidence for:

- Each supported host/engine/adapter combination: network denial, CPU/memory/process limits,
  read-only and read-write mounts, cleanup after success/failure/cancellation, and Windows Hyper-V
  isolation where applicable.
- Deployment evidence that no host process mutates a mounted workspace during an agent run; component
  checks are defense in depth and not a substitute for workspace quiescence.
- Authentication, TLS termination, rate limiting, tenant routing, secret handling, log/trace
  retention, and recovery procedures in the actual deployment architecture.
- Image digest policy, verification of dependency/release provenance, and security response process.
- Resource exhaustion including workspace disk growth, stuck synchronous callbacks, and concurrent
  request bursts.

See [SECURITY.md](../SECURITY.md) for private vulnerability reporting and
[ADR 0003](architecture/adr/0003-container-sandbox.md) for the accepted sandbox design.
