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

# Examples

These examples demonstrate Gabby's scope: configuring an agent runtime, enforcing tool and
request boundaries, executing bounded work, and returning results or traces. They are learning
materials, not production deployments. Host applications still own identity, durable state,
tenant-aware data access, and deployment security.

## Core runtime examples

Run the deterministic examples from the repository root:

```sh
uv run --frozen python examples/domain_agents.py
uv run --frozen python examples/agent_composition.py
uv run --frozen python examples/planning_revisions.py
```

These scripts use small local test doubles that implement Gabby's model-provider interface. They
return scripted responses; they do not call an AI model, download weights, train or fine-tune a
model, or demonstrate model manipulation. Their purpose is to make the runtime behavior repeatable
without credentials or network access.

- [`domain_agents.py`](domain_agents.py) demonstrates agent definitions, skill activation,
  schema-validated application tools, and per-run bounds across support, research, and data tasks.
  Its records and tool handlers are synthetic examples; Python handlers are trusted host code unless
  the application explicitly runs them through a supported sandbox.
- [`agent_composition.py`](agent_composition.py) demonstrates explicit parent-to-specialist
  delegation and trace correlation. It is a small in-process composition example, not a workflow
  engine or durable multi-agent orchestrator.
- [`planning_revisions.py`](planning_revisions.py) demonstrates an optional planner revising a
  plan after a bounded tool observation.
- [`approval_audit.py`](approval_audit.py) demonstrates a host-provided approval callback and the
  content-minimizing SQLite audit helper. The printed callback is only a stand-in for an authenticated
  reviewer interface.

For a real local database tool boundary, run:

```sh
uv run --frozen python examples/sqlite_data_agent.py
```

[`sqlite_data_agent.py`](sqlite_data_agent.py) creates synthetic records in a temporary SQLite
database, exposes a parameterized read-only query tool, and removes the data when it exits. SQLite
is only the sample application's data source here; Gabby does not require applications to use
SQLite. Read the [SQLite data tool guide](../docs/SQLITE_DATA.md) before adapting it.

For isolated Python tool execution, run:

```sh
uv run --frozen python examples/python_sandboxed_agent.py
```

[`python_sandboxed_agent.py`](python_sandboxed_agent.py) requires a local Docker daemon and runs a
bounded calculation in a per-run container. This demonstrates Gabby's configured sandbox boundary;
it does not mean every registered Python handler is sandboxed automatically. See the
[Python tool guide](../docs/PYTHON_TOOL.md).

## Host integration examples

[`host_orchestrated_pipeline/`](host_orchestrated_pipeline/) demonstrates a host coordinating four
separate Gabby service calls: triage, a knowledge worker, a read-only analyst, and synthesis. The
host owns routing, identity, tenant-scoped retrieval, durable checkpoints, and workflow-wide budget
accounting. Its interfaces and YAML files are a reference template, not a standalone deployable
system. The YAML model entries use the generic `openai_compatible` adapter with placeholder model
IDs; configure each service for a supported provider and deployment-owned endpoint and credentials.
Read its README and the [host orchestration guide](../docs/HOST_ORCHESTRATED_PIPELINES.md) before
adapting it.

[`hosted_service.py`](hosted_service.py) and [`hosted-agent.yaml`](hosted-agent.yaml) show an
optional live-model setup using Gabby's generic OpenAI-compatible adapter. The YAML contains
placeholder endpoint and model values: replace them with the endpoint and model ID for your chosen
compatible service. Set the configured `MODEL_API_KEY` and a deployment-owned API token, then start
the service:

```sh
GABBY_AGENT_CONFIG=examples/hosted-agent.yaml \
GABBY_API_TOKEN=replace-with-a-secret \
MODEL_API_KEY=replace-with-a-provider-api-key \
uv run --frozen --extra server uvicorn examples.hosted_service:create_app \
  --factory --host 127.0.0.1 --port 8787
```

Check health and make an authenticated run request:

```sh
curl http://127.0.0.1:8787/health
curl http://127.0.0.1:8787/v1/agents/research-synthesizer/run \
  -H 'Authorization: Bearer replace-with-a-secret' \
  -H 'Content-Type: application/json' \
  -d '{"input":"What does the research say about tree cover?","context":{"sources":[{"label":"sample-report.md","text":"Tree canopy increased by 8% between 2018 and 2024."}]}}'
```

The service sample uses one static bearer token for local demonstration. For deployment, use an
appropriate authenticator, terminate TLS at a trusted ingress, provide credentials through a secret
manager, and configure rate limits and process supervision. A successful health check does not test
the inference provider; the run route does. See the [operations guide](../docs/OPERATIONS.md).

[`stateless_sse_client.py`](stateless_sse_client.py) shows a Python host client sending input,
context, and memory on each request and consuming Gabby's typed SSE events. Conversation history
and durable user state remain with the host. With the service above running, try:

```sh
GABBY_API_TOKEN=replace-with-a-secret \
uv run --frozen python examples/stateless_sse_client.py \
  --agent research-synthesizer \
  --context-json '{"sources":[{"label":"sample-report.md","text":"Tree canopy increased by 8% between 2018 and 2024."}]}' \
  --memory-json '{"preferred_format":"brief"}' \
  'What does the research say about tree cover?'
```

Set `GABBY_URL` when the service is not at `http://127.0.0.1:8787`. The client allows HTTP only
for loopback development and requires HTTPS for remote service URLs.

## Optional integrations

- [`redis_skill_revocation.py`](redis_skill_revocation.py) demonstrates using a host-owned Redis
  client for shared publisher revocation across Gabby processes. Install `redis>=5`, set
  `GABBY_REDIS_URL`, and use a Redis 6.2+ service. Redis is optional and is not Gabby's conversation
  store. See the [operations guide](../docs/OPERATIONS.md#enforce-skill-publisher-revocations).
- [`n8n/gabby-http-node.json`](n8n/gabby-http-node.json) is an importable HTTP Request node template
  for an external n8n workflow. It is an adapter example, not an orchestration feature built into
  Gabby. Configure the endpoint and authentication in n8n before use.

## Model and provider references

Gabby executes model calls through its `ModelProvider` interface, so examples that exercise the
agent loop need either a deterministic test double or a configured inference provider. The offline
examples contain mock provider classes solely to script reproducible behavior. The hosted service
and host-pipeline templates use the generic OpenAI-compatible adapter with placeholders; adapt the
configuration or inject a custom `ModelProvider` for other APIs. No example trains models, changes
weights, loads model adapters, or requires a particular provider for Gabby's governance and
tool-execution features.
