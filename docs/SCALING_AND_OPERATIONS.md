# Scaling and operational tradeoffs

This guide maps common production concerns to Gabby's current controls, limits, and deployment
choices. It distinguishes behavior implemented in Gabby from decisions and infrastructure owned by
the host. A passing local test is not evidence for a different provider, operating system, container
engine, or hosted deployment.

## Synchronous extension handlers

Synchronous callbacks run in Gabby's process through a dedicated bounded worker pool. The current
pool has eight daemon workers and a queue capped at 256 waiting callbacks. This prevents unbounded
thread creation and waiting work; when both workers and queue are occupied, new tool callbacks are
rejected with the stable `capacity_exhausted` tool error. It does not make a synchronous callback
interruptible. If a callback
hangs after starting, it continues occupying one worker even when the caller times out or cancels.

For callbacks that must be forcibly stopped, use a sandboxed/container-backed tool or a separate
process/service with an enforceable deadline. Keep synchronous host handlers short, make blocking
I/O use explicit timeouts, and cooperate with `ToolContext.cancellation` when possible. The callback
pool is process-global and its worker/queue sizing is not currently a public per-agent setting;
scale service processes only after accounting for per-process model and storage resources.

## Vector search and hybrid indexing

`SQLiteVectorStore` performs exact cosine ranking by scanning stored vectors. It is suitable for
local and modest corpora where predictable setup and exact results matter. There is no universal
chunk-count cutoff: measure latency and memory with representative vector dimensions, filters,
concurrency, and hardware before choosing a backend.

Hosts can implement the vector and manifest extension contracts when their corpus or deployment requires a different storage model. Gabby does not ship a shared or multi-host database backend.

## Container engine and platform support

Gabby deliberately fails closed for native Windows Docker containers unless the Docker Engine
server is at least 29.1.4. Earlier versions have a known failure when starting containers with
networking disabled. Gabby does not fall back to enabled networking. Upgrade the engine or choose a
supported deployment boundary; do not bypass the version check. The requirement is Windows-specific
and does not apply to Linux containers.

Container support varies by host, engine, API/CLI adapter, image, and OS. The [sandbox guide in the
user documentation](README_GUIDE.md#container-sandbox-tools) and opt-in live tests describe the
validated combinations. Require target-host acceptance checks for network isolation, mounts,
resource limits, Hyper-V isolation where applicable, and cleanup before relying on sandboxing.

## Tool schemas and prototyping

Tool input and output schemas are required runtime contracts. Gabby validates handler output before
adding it to model context, and applies the configured result-size limit. There is no warn-only mode:
letting invalid handler output pass can make model context and downstream behavior unpredictable.
For fast prototyping, begin with a broad JSON-only contract and narrow it as the handler stabilizes:

```python
from gabby import Tool

prototype_tool = Tool(
    name="lookup",
    description="Prototype lookup result shape.",
    parameters={"type": "object", "additionalProperties": True},
    output_schema={"type": ["object", "array", "string", "number", "boolean", "null"]},
    handler=lookup,
)
```

The broad output schema still rejects non-JSON values and does not disable byte limits. Before
shipping, replace it with the smallest useful schema, including required fields and property bounds
where the consuming application depends on the result shape. See the [tool contract](EXTENSIONS.md)
and [structured output guide](STRUCTURED_OUTPUT.md).

## Evidence checklist

Before scaling a Gabby deployment, record evidence for the actual configuration:

- Run the regular local suite and focused provider and container acceptance checks that
  match the target deployment.
- Measure end-to-end latency, throughput, worker saturation, request/response sizes, and resource
  use with representative workloads.
- Test cancellation and timeout behavior for each custom provider, tool, retriever, verifier, and
  tracer; synchronous callbacks may continue after cancellation.
- Confirm the selected vector and manifest backends share the intended database consistency domain.
- Verify TLS, authentication, authorization, process supervision, secrets, backups, and ingress
  controls in the host deployment.
- Treat untested provider/OS/engine combinations as unverified, not as supported by analogy.

## Concern-by-concern disposition

| Concern | Current disposition |
|---|---|
| Stuck synchronous callbacks | Worker threads and the waiting queue are bounded; new tool calls receive `capacity_exhausted` after saturation. A running Python callback still cannot be forcibly stopped. Use a container or separate process when hard termination is required. |
| Linear SQLite vector search | This remains an exact local backend with linear scan cost. Gabby makes no universal chunk threshold claim. hosts can provide a different vector backend through the extension contract. |
| Multi-host manifest setup | Not provided as a built-in backend. Hosts may implement the storage contracts and are responsible for consistency, migrations, and operational validation. |
| Mocked provider acceptance | Opt-in real completion/stream checks are documented for Ollama, Hugging Face, Anthropic, and Gemini. They require credentials or a local service and are not run in ordinary CI; they do not guarantee provider uptime or schema stability. |
| Docker version floor | The Windows Docker floor remains fail-closed because older daemons can fail when networking is disabled. There is no unsafe fallback that enables networking. Linux containers do not use this Windows-specific floor. |
| Strict tool schemas | Runtime validation remains mandatory. Developers can start with a broad JSON-only schema and refine it before release; Gabby does not silently pass invalid values through. |
