# Gabby project scorecard

This scorecard gives a consistent estimate of progress toward the production-grade OSS objective.
Keep category weights fixed so reports remain comparable. Update a category only when implementation
or evidence changes; do not count roadmap items as delivered.

## Method

Each category is scored from 0–100 based on acceptance criteria that are implemented, documented,
and verified at the stated scope. A prototype or unit test for a narrower case earns partial credit.
The overall score is the sum of `weight × category score`, divided by 100. The score tracks product
readiness, not lines of code or test count. Fixed weights, category scores, and evidence summaries
are maintained in [`project-scorecard.toml`](project-scorecard.toml), the machine-readable source of
truth. Validate it and this report with `python scripts/check_scorecard.py`; CI runs the same check.

## Historical snapshot (2026-10-03)

This scorecard predates the November 2026 removal of local model manipulation, specialized
ingestion parsers, PostgreSQL adapters, MCP integrations, and the OpenTelemetry adapter. Its
percentages and detailed evidence describe the earlier tree; they are not a score or inventory of
the current project. Recalculate the scorecard before using it to make current readiness claims.

| Category | Weight | Score | Main evidence and remaining work |
|---|---:|---:|---|
| Architecture and contracts | 15% | 95% | Async core, stateless contract, policies with a run-scoped injectable policy-engine factory and typed async authorization contract, with principal delivery, denial, sanitization, and run-deadline tests, immutable resolved plan with shared YAML/programmatic definition and skill validation, bounded finite-JSON configuration snapshots that reject cycles, unsupported objects, excessive depth and size, construction-time global instructions with explicit precedence, fail-closed unknown-key checks for Gabby-owned configuration, `/v1` boundary, durable fenced writer ownership for hybrid index generations, request-scoped ToolContext with construction-validated per-tool environment resource grants, matching bounded HTTP/embedded run-input validation with JSON-normalized request snapshots, mandatory input/output JSON Schemas validated at construction and runtime, stable ToolErrorCode contracts across observations, traces, and SSE, and a named v1 core Python export contract with package-root regression coverage exist. Behavioral contract tests for all promised lifecycle and failure semantics, exact optional integration support per release, and v1.0 release-note confirmation remain. |
| Agent runtime and skills | 20% | 99% | Tool loop with per-run `max_tool_calls` budget that rejects oversized batches before execution and optional bounded concurrent dispatch for complete batches of explicitly `parallel_safe` host handlers, with sequential defaults, deterministic tool-result ordering, and tracer-preserving fallback, opt-in typed transient model retries across reasoning, planning, and skill-selection calls with deadline-bound backoff and no partial stream replay, shared global and agent instructions applied to built-in model-based skill selection and planning, typed host-injected human approval with deny-by-default behavior for marked tools, an injectable async skill selector with deterministic and model-driven strategies, an opt-in planner with bounded structured plans and up to three opt-in revisions from bounded tool observations, validated results, traced selector and planner usage, and end-to-end model-planned tool execution through observation to final response with combined usage and trace evidence, dependency activation, portable SemVer skill packages with exact agent and dependency pins and registry version selection, deterministic local ZIP packing, bounded checksum-verified install with persisted signer evidence, v2 detached Ed25519 signatures binding archive and canonical manifest, trusted-key installed-content audit with tamper detection and revoked-key reporting, and exact-version uninstall, programmatic skill metadata capped at 1 MiB and 10,000 values, optional detached Ed25519 publisher signatures verified against host-managed trust keys with bounded KEY_ID.pub directory loading, an async static HTTPS registry client with bounded catalog search, exact-version discovery, host-provided auth headers, same-origin artifact retrieval, mandatory signature checks, and package identity validation, plus `gabby skill catalog build` and `build_static_skill_registry()` for bounded generation of signed static artifact trees and validated catalogs, confined Markdown instructions and activation-scoped examples, typed verifier results, per-run state, event streaming, stable coded tool failures with handler-detail redaction, and bounded sync callback workers that skip queued work after timeout or cancellation, plus a request-scoped cooperative tool cancellation token and an `AgentTool` adapter for explicit stateless child-agent delegation with direct and indirect cycle/depth, timeout, and byte bounds and opt-in principal forwarding, are implemented. The opt-in `sqlite_query_tool()` provides parameterized, read-only local database access through a named host resource, with permission checks and query/result bounds. The opt-in `python_run_tool()` executes bounded source in the configured per-run sandbox through a private read-only input mount and returns bounded stdout/stderr. Bounded skill package inspection reports validated capability claims and file digests with optional trusted-key verification without installing into a consumer registry. Signed remote skill dependency-closure fetching validates exact pins, signatures, and the complete bounded graph before retry-safe per-package installation. Trusted installed skills are reverified before every run and stream, with fail-closed integrity errors and successful checks recorded in traces. Static catalogs receive a generation timestamp, and consumers can require a maximum age through the Python API or CLI; timestamps remain unsigned discovery metadata. YAML and programmatic agent definitions can also require bounded JSON Schema validated final outputs; strict parsing, duplicate-key rejection, parsed result metadata, and buffered structured streaming are covered. File-backed and programmatic skills also carry bounded Draft 2020-12 input and output schemas; active skill input contracts validate the stateless request envelope before reasoning, output contracts compose with the agent schema, package inspection preserves them, and focused config, runtime, package, and streaming acceptance passes. Registry hosting, multi-instance trust-key and revocation distribution, tamper-proof local provenance, deployment-specific freshness policy, and wider runtime acceptance remain. |
| Model and knowledge providers | 15% | 98% | Hosted and host-injected model providers, SQLite lexical and vector stores, pluggable embedding and reranking providers, hybrid retrieval with generation coordination, bounded retrieval context, and built-in root-confined UTF-8 plain-text/Markdown ingestion. Hosts inject specialized parsers when required. Selected hosted provider acceptance remained. |
| Security and sandboxing | 20% | 77% | Runtime policy enforcement, fail-closed rejection of unknown policy and sandbox keys, bounded agent/skill YAML and text reads with equivalent programmatic-definition validation, cross-platform case-folded and Unicode-normalized skill archive path collision checks, a 256-skill per-agent resolution limit and a model-request-bounded aggregate instruction/text budget capped at 16 MiB, stable sanitized HTTP/SSE execution errors, built-in model/embedding/reranking provider error-body, transport-text, and chained-traceback redaction, per-tool UTF-8 input caps enforced before host/sandbox handler execution and serialized result caps with oversized nested strings rejected before encoding, a shared 1 MiB sandbox stdout/stderr budget that stops CLI engine commands on overflow and removes the run container, optional OCI SHA-256 image digest enforcement, issuer/audience/expiry/subject-validated JWT authentication with bounded HTTPS JWKS retrieval and strict scope-claim parsing, optional fail-closed JWT issuer-scope-to-capability mapping, per-request revocation checks and a durable SQLite revocation store keyed by issuer and token ID with explicit expiration cleanup, route-specific run/stream capability enforcement, a default non-root Linux container identity with numeric per-agent override, bounded, identity-checked detached signature sidecar reads with path-swap and oversized-file regression tests, nonblocking trust-key reads that reject FIFO substitution, concurrent file replacement, symlink entries, and catalogs over the key-count bound; the CLI explicit-key loader rejects path swaps, symlink substitution, FIFO substitution, and key-size changes, optional host-injected `SkillTrustPolicy` enforcement of trusted v2 installed-skill signatures at agent construction, per-execution `SkillRevocationChecker` checks, durable SQLite signer-revocation storage plus a Redis 6.2+ `RedisSkillRevocationStore` over a host-owned async client with bounded SSCAN listing and fail-closed backend errors, with 10 fake-client contract cases and live Redis command acceptance, active-run cancellation at configurable polling intervals, with sanitized in-flight SSE revocation errors, plus signed GitHub build provenance for release distributions are implemented. Docker and Podman CLI/API tests cover enforcement. Linux live acceptance verifies effective UID, CPU, memory, process, network, root filesystem, workspace and private read-only tool-input mounts, custom executable tool calls, and cleanup after success and cancellation. The hosted research service Compose deployment was locally verified running non-root with a read-only root, dropped capabilities, and bounded CPU, memory, and process use. Native Windows launches fail closed before startup unless the Docker server is at least 29.1.4; whole-number CPU and explicit process-limit opt-out tests exist. The Docker API adapter now supports Docker Desktop's local named pipe through the optional `windows-sandbox` extra, with mocked transport tests and opt-in live coverage for both adapters; Windows host validation remains. Redis persistence and read-after-write configuration, multi-instance trust-key distribution, macOS/Windows live isolation evidence, hardened workspace races, deployment-specific ingress and operations controls, and defense against engine, kernel, hypervisor, and malicious configured images remain. Poll-based revocation detection is delayed by the configured interval and checker latency; completed tool effects cannot be rolled back and uncooperative synchronous callbacks may continue. |
| API, CLI, and deployment | 10% | 95% | bounded stateless evaluation API and `gabby evaluate` JSONL CI workflow with output/tool-use expectations, machine-readable knowledge ingest/delete/search over bounded file ingestion, root-confined stale-source cleanup, and SQLite FTS5, `gabby run`/`serve` retriever injection for knowledge-enabled agents with actionable missing-store errors, FastAPI `/v1` run and SSE routes, the async-first/sync-wrapper `GabbyClient` for stateless Python consumers with bounded response parsing and URL transport validation, typed schemas, optional trace bodies that retain trace IDs, CLI-configurable request byte and total receive-time bounds, per-process execution admission before body buffering and authentication for ordinary requests, with separate bounded admission and run-slot lookup for keyed stream reattachment and `/health` excluded, bounded 408 responses for stalled uploads, pluggable bearer and optional issuer-bound JWT authenticators, bounded async OIDC issuer discovery with exact issuer validation, HTTPS JWKS URL checks, duplicate JSON member rejection, and verifier-option validation before discovery requests, configurable five-second default timeout for custom authentication calls with sanitized 503 and capacity-release acceptance, exact JWT scope mapping, host-injected bounded JWT revocation checks, CLI-configured bearer capabilities and route requirements, authenticated principal forwarding into host approval callbacks, shared per-process run capacity with overload responses, ASGI disconnect/send-failure/deadline cancellation and capacity release, fresh stateless retry acceptance, opt-in process-local SSE replay bound to principal and request with sequential IDs and GabbyClient reconnection support, plus a host-owned async `StreamJournal` protocol with a bounded SQLite implementation for same-host cross-worker live replay and completed replay across process restarts, embedded execution, an Nginx ingress reference that enforces TLS 1.2/1.3, suppresses version disclosure, and applies HSTS and browser security headers, with repeatable real-Nginx acceptance for headers and health forwarding, exact request-body rejection, and edge 429 burst limiting against the hosted agent, a Kubernetes hosted-research reference with a digest-pinned image placeholder, single replica, ClusterIP service, TLS ingress, NetworkPolicy, pod security context, bounded resources, and manifest contract tests; and a multi-stage lockfile-based research-agent container whose exact Compose deployment passed local build, hardening, health, and API-authentication checks and accepts environment-configured SHA-256-pinned base images exist. The `gabby knowledge evaluate` CLI exposes those metrics over bounded JSONL datasets and the SQLite store. The gabby embeddings evaluate CLI runs labeled provider evaluations with strict versioned profiles for OpenAI-compatible, Gemini, and Hugging Face providers. The `gabby skill catalog build` command emits validated static registry catalogs and signed exact-version artifacts. `gabby skill inspect` emits machine-readable pre-install package metadata with optional trusted signature enforcement. `gabby skill fetch --with-dependencies` provides exact-version remote skill closure installation through the CLI. The static catalog builder can seed a new output tree from a prior registry after validating every cataloged signed artifact. First hosted CI run of Compose, and ingress smoke gates, live Kubernetes/CNI acceptance, deployment-specific TLS and trusted-proxy configuration, custom shared-journal backend acceptance, and deployment runbooks remain. |
| OSS quality and CI | 15% | 80% | `uv` lock, Python version metadata, Python/platform CI, Windows jobs that install the optional Docker Desktop named-pipe dependency, quality gates that audit that optional dependency, OSS policies, explicit repository governance and API compatibility guidance, package build/install validation, CI-checked reports, and unique ADR numbering and index checks are in place. A previous four-version full-suite run passed on Python 3.11–3.14, but predates the current tree. Current Linux Docker/Podman sandbox acceptance passed 14 engine-backed cases across both engines and adapters; sandbox-live workflow gates on pull requests and tagged releases, and a reusable hosted-agent Compose build and runtime smoke workflow called by CI and tagged releases, are configured. The release distribution build waits for the container gate. The tag-gated PyPI Trusted Publishing workflow uses isolated build and publish jobs, signed provenance attestations, and a CycloneDX SBOM attested against wheel and source distributions. Current-tree full-suite acceptance across Python versions, first hosted live-sandbox/Compose/attested-release executions, GitHub environment and PyPI Trusted Publisher setup, the final named v1.0 compatibility set, and macOS/Windows live platform evidence remain. |
| Docs and examples | 5% | 88% | Historical evidence for the 2026-10-03 tree: architecture, ADRs, threat model, extension guidance, security, operations, skills, API and deployment examples, ingestion guidance, public API docstrings, evaluation guides, and registry documentation. Deployment validation, provider/platform evidence, and confirmation of the contract set in v1.0 release notes remained at that snapshot. |

**Weighted progress: 90%.** Exact weighted score: 90.05%. Calculation: (15×95 + 20×99 + 15×98 + 20×77 + 10×95 + 15×80 + 5×88) / 100 = 90.05%. This is the historical score for the dated snapshot above, not a current readiness rating.

The bounded JSON Feed 1.0/1.1 and OPML 1.0/1.1/2.0 parsers were added after this weighted
assessment. They extend the existing knowledge-ingestion evidence without changing the category weights or scores; the next
score revision should follow a deliberate review of the rubric rather than treating one feature as
a whole-category percentage change.

## Verification snapshot

The run totals below are historical evidence for the tree at the time each run was performed; they
do not verify the current ingestion-scope change. See ADR 0125 for the current supported formats.

Gabby specializes agent behavior through runtime configuration, policies, and governed execution.
It does not train models, modify model weights, or load model adapters.

The latest Linux/Python 3.12.14 coverage-enabled run completed **1,765 passed, 37 skipped** in
70.87 seconds. All executed tests passed, but branch-aware coverage measured **88.43%**, below the
configured 90% gate, so the CI-equivalent command exits unsuccessfully. The added evaluation and
retrieval-evaluation edge cases raised coverage from 87.94% to 88.38%; their focused suite passed
79 tests. New cross-process SQLite journal tests verify 80 appends from four concurrent processes
and recovery of an abandoned run after a worker exits. JSON Feed and streaming OPML parsing are
included; Jina live hosted-provider acceptance skips unless the host sets its opt-in flag and API key.
The live Linux sandbox matrix passed all **14** Docker/Podman CLI/API cases: 8 Docker and 6 Podman,
including both workspace modes and per-run cleanup. The Docker Compose plugin is unavailable in
this environment, so Compose and Nginx deployment gates were not rerun. macOS/Windows sandbox
acceptance and hosted providers remain unverified here.
Two earlier ordinary full-suite runs intermittently timed out in
`test_cli_process_runner_captures_input_and_bounds_output`; it passes alone, with its full test
module, and in the latest full-suite runs. The current source archive and wheel also build and pass the package-integrity checker, with the current package contents. All
11 Parquet and both Kubernetes deployment contract cases passed. The Redis revocation adapter passed 10 fake-client
contract cases and a live local Redis command acceptance cycle for shared checks, listing, reinstate,
and fresh reads.
The Anthropic provider's completion, streaming, and end-to-end tool cycle are covered by mock
contract tests; its live acceptance is opt-in. The reusable approval-audit module has 93.30%. The CLI subprocess test passed alone, with its
complete module (80 tests), and in the latest full-suite run. The
revocation/API/runtime suite passed 44
tests. The latest ingestion and public API suites passed 208 tests, including TOML indexing into
SQLite.
The static skill registry builder passed a client round-trip against its generated catalog and
package artifacts. The vector-only PDF path was also verified by a real PDFium render and
`FileIngestor` to SQLite integration. The previous four-version full-suite run passed 1,162 tests on
Python 3.11, 3.12, 3.13, and 3.14 with 25 opt-in skips per version;
its branch-aware coverage was 91.23% on Python 3.11 and 3.14, and 91.25% on Python 3.12 and 3.13.
The suite covers
bounded transient model retries,
no replay after partial stream output, stable tool failure categories, handler-detail redaction, and propagation to model observations, traces, and SSE events alongside
the named-pipe transport contract, Cohere reranking provider contracts,
route-scoped authorization, versioned skill resolution, Hugging Face embeddings, cooperative tool
cancellation, active skill-signer revocation cancellation through embedded and HTTP streaming calls, crash recovery, native Windows engine preflight, CSV/JSON/PDF ingestion and vector retrieval, and Windows
live acceptance cases:

- The latest coverage-enabled run recorded **1,765 passed and 37 skipped** on Linux/Python 3.12.14.
  It failed the configured branch coverage gate at **88.43%** (minimum 90%). A Python 3.11.14 run
  passed the same test count at 88.42%. The current host
  passed all 14 Linux Docker/Podman live sandbox cases; the Docker Compose plugin is unavailable,
  so Compose and ingress gates were not run.
  Earlier four-version runs passed 1,162 tests per Python 3.11–3.14 environment and met the 90%
  branch-aware coverage gate; these preceded the PDFium OCR addition.
  Current full-suite coverage is 86% for the model providers, 89% for runtime, 83% for ingestion,
  79% for the skill registry, and 76–77% for the two evaluation modules. Focused Anthropic provider
  tests cover request conversion, completion and streaming tool calls, and a complete agent tool
  cycle; real hosted acceptance is opt-in. Focused provider contract tests also cover SSE framing,
  bounded UTF-8 responses, malformed data, and provider lifecycle behavior. Hybrid retrieval has
  94% full-suite coverage, including shared active-generation filtering and fail-fast validation of
  custom store generation-filter signatures. Regressions cover expiration before
  execution and stable sandbox timeout, engine-unavailable, and output-limit codes in SSE and
  traces; broader deadline and sandbox failure-path coverage remains a targeted follow-up.
  The local embedding provider has 100% module coverage across 42 contract cases. The CLI suite has
  25 passing cases and 99% module coverage, including run/serve contract checks and trusted-key
  path replacement, truncation, and FIFO substitution regressions.
  The API tests verify capacity admission
  before request-body reads and hold the slot through response transmission.
- The latest full suite had 37 opt-in skips, including live Linux Docker/Podman acceptance, Cohere
  and Jina reranking, Ollama and Hugging Face endpoints, native
  Windows Docker acceptance. A separate current-tree live run passed 8 Docker and 6 Podman cases
  across CLI/API adapters and workspace modes. Native Windows integration did not run on this Linux
  host.
- Ruff check/format, source-package mypy, lockfile, workflow, scorecard, and documentation checks
  pass on this worktree. The package source distribution and wheel build, and the wheel imports from an isolated
  target install.
- `pip-audit --skip-editable` reported no known vulnerabilities in the locked dependencies.
- `uv lock --check` passed.
- The runnable offline domain example completed customer-support, research, and data-analysis
  executions.
- The exact container Compose deployment passed local validation with checksum-verified Docker
  Compose v5.5.1: it built and started healthy, ran as UID 10001 with a read-only root, dropped
  capabilities, one CPU, 1 GiB memory, and 128 processes, returned HTTP 200 for health and 401 for
  an unauthenticated run, and was then fully removed. The hosted CI gate is configured but has not
  run remotely.
- Current-worktree opt-in live sandbox acceptance passed on Linux with Docker and Podman: **14
  passed** total, 8 Docker and 6 Podman cases across CLI/API adapters and workspace modes. The live
  cases verify effective UID 65532 and cleanup after active-run cancellation. This verifies the
  current worktree on Linux only.
- The provider response-bound tests guard against multibyte UTF-8 overflows; Hugging Face embedding tests
  cover bounded feature extraction, sanitized errors, and end-to-end coordinated SQLite retrieval.
- Detached skill signature sidecars are opened and checked as bounded regular files before parsing;
  regression coverage rejects oversized files and an atomic path replacement between metadata check
  and open.
- The detached skill-signing module has 92% combined coverage on the current suite, with
  regressions for invalid and duplicate signature fields, package-content mismatch, unavailable
  optional crypto support, and atomic signature-output failures.
- The versioned-skill full-suite evidence includes exact pinning, dependency resolution, filesystem
  selection of exact or unique versions, fail-closed ambiguity handling, and in-memory registry
  selection of multiple versions across all supported Python versions.
- Live completion/stream acceptance checks are available for Ollama and Hugging Face but were not
  run; the local Ollama server was unavailable and Hugging Face was not opted in.
- Cross-platform runs on macOS and Windows remain unverified in this environment.
- CI and tagged-release workflows are configured for the full Python 3.11–3.14 cross-product on
  Linux/macOS/Windows, and the workflow checker enforces that matrix. Configuration is not evidence
  that the current worktree has passed those remote jobs.

Keep this verification snapshot separate from the weighted product score. A green suite is evidence
for covered criteria, not proof that the complete product objective is finished.
