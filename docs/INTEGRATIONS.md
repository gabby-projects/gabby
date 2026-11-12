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

# Runtime integrations

Gabby can sit behind an orchestration framework through its stateless HTTP and SSE API. The
orchestrator selects and schedules work; Gabby applies the selected agent's tool policy, approvals,
sandbox rules, payload filters, and configured output/persona checks.

## MCP

Install `gabby-agent-runtime[mcp]`. Agent YAML can configure Streamable HTTP MCP servers. Use HTTPS
outside loopback, and explicitly allowlist every remote tool:

```yaml
mcp:
  servers:
    tickets:
      url: https://tools.example.com/mcp
      allow_tools: [get_ticket, search_tickets]
  expose: true
tools: [tickets_get_ticket, tickets_search_tickets]
policies:
  allowed_tools: [tickets_get_ticket, tickets_search_tickets]
```

Load MCP-enabled definitions through the asynchronous constructor so Gabby can discover each
allowlisted tool before freezing the agent's tool registry:

```python
agent = await Agent.from_file_mcp("agent.yaml")
```

MCP tool names are prefixed by the configured server name. Remote tools remain subject to the
agent's declared `tools`, `policies.allowed_tools`, schema checks, result bounds, approval settings,
and runtime deadlines. MCP transport errors fail the tool call. Server-provided descriptions and
schemas are untrusted input and should be reviewed before an agent is deployed.

When `mcp.expose` is true, `create_mcp_server(agent)` returns an MCP Python SDK server exposing one
`run_agent(task)` tool. Run it with the SDK's Streamable HTTP or stdio transport. The operation calls
`Agent.arun()` and does not expose host Python handlers directly. The host owns starting and closing
the MCP server and the agent.

## OpenTelemetry and signed audit evidence

Install `gabby-agent-runtime[opentelemetry]` and configure an OTLP endpoint:

```python
tracer, provider = create_otlp_tracer(endpoint="https://otel.example.com/v1/traces")
agent = Agent.from_file("agent.yaml", tracer=tracer)
try:
    result = await agent.arun("Review this request")
finally:
    await agent.aclose()
    provider.shutdown()
```

Spans contain event kind, trace ID, agent name, and duration. They intentionally omit event details,
prompts, tool arguments, and model output. The host owns exporter/provider shutdown and credentials.

`SignedAuditExporter` writes JSONL records linked by SHA-256 hashes and signed with Ed25519. It
records successful tool-policy decisions, explicit policy denials, and persona-verifier outcomes,
without recording prompts, tool arguments, verifier details, or model output. Install
`gabby-agent-runtime[skill-signing]`; provide a protected 32-byte private key. It verifies a
pre-existing chain before appending. Anchor exported chain heads outside the process if you need to
detect full-file replacement. Call `exporter.close()` during host shutdown to release its
writer ownership. A single exporter must own a given audit path; a second active writer for the
same resolved path is rejected so concurrent processes cannot fork the hash chain.

For LF TRACE v0.2 Trust Records, install `gabby-agent-runtime[trace]` and configure
`LFTraceExporter(directory, claims=..., private_key=..., audit_exporter=...)`. Supply the signed
deployment claims (`subject`, `model`, `runtime`, `policy`, `data_class`, `build_provenance`, and
`appraisal`) from trusted deployment evidence. The exporter derives the tool-transcript hash from
observed policy outcomes and delegates signing/schema validation to `agentrust-trace`. Compose it
with OTel using `CompositeTracer(otel_tracer, trace_exporter)`.

TRACE v0.2 is a draft and its standard record has no persona-compliance claim. The companion Gabby
signed audit chain records persona-verifier outcomes and uses the trace ID to correlate with the
TRACE filename. A signed record proves who made a claim and that it has not changed; it does not
independently prove the model followed a persona, nor that the runtime is hardware-attested. Never
invent deployment claims to make schema validation pass.

## Orchestrator helpers

Install `gabby-agent-runtime[crewai]` for CrewAI. LangGraph needs no additional Gabby dependency:

```python
node = langgraph_node(gabby_client, input_key="task", output_key="review")
crew_tool = crewai_tool(gabby_client)
```

`langgraph_node` consumes a string state field and returns the result plus `gabby_trace_id` as a
state update. `crewai_tool` creates a CrewAI tool using the same remote client. Import
[`examples/n8n/gabby-http-node.json`](../examples/n8n/gabby-http-node.json) into n8n for a prefilled
HTTP Request node; it calls `POST /v1/agents/{agent_name}/run`. For SSE, set the node's URL to
`POST /v1/agents/{agent_name}/stream` and response format to text/event stream. Keep the service URL
and bearer token in n8n credentials/environment, not the workflow export. `GabbyClient.astream()`
provides typed SSE events for Python orchestrator nodes.

All adapters are thin HTTP clients: they do not pass orchestration state unless the caller maps it
into the request's explicit context or memory fields. The host remains responsible for
authentication, tenant selection, caller identity, and deciding which work is delegated to Gabby.
