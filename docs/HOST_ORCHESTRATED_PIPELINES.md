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

# Host-Orchestrated Multi-Agent Pipelines

This guide describes Approach A: a host application owns workflow decisions and durable state,
then calls several independently configured Gabby services for bounded agent work. Gabby remains
the governed execution runtime for each agent. It does not become the workflow engine, identity
provider, tenant router, or system of record. See [ADR 0130](architecture/adr/0130-host-orchestrated-multi-agent-pipelines.md)
and the [reference example](../examples/host_orchestrated_pipeline/README.md).

Use this pattern when the application needs deterministic routing, parallel specialist calls,
host-controlled authorization, or recovery across several agent runs. Use [AgentTool composition](ARCHITECTURE.md#agent-composition)
when a parent agent should choose and invoke one child as a tool within a single run. These are
different ownership models: the host decides each stage here; a parent model selects a child in
AgentTool composition.

## Deployment layout

`create_app()` serves one configured agent per service instance. Deploy one instance or service
configuration for each role; do not point every endpoint at one service and expect it to switch
YAML definitions based on caller input.

```text
my-ai-platform/
├── host-app/
│   ├── auth/                 # validates caller and resolves tenant/scopes
│   ├── orchestration/        # deterministic routing, fan-out, fan-in
│   ├── state/                # workflow checkpoints and conversation state
│   ├── retrieval/            # tenant-filtered search and source validation
│   └── gabby_clients/        # fixed service URLs, audiences, and revisions
└── gabby-deployments/
    ├── triage/agent.yaml
    ├── knowledge-worker/agent.yaml
    ├── finance-analyst/agent.yaml
    └── synthesis/agent.yaml
```

Use deployment-owned configuration to map each role to a fixed HTTPS URL, agent name, expected
JWT audience, and immutable configuration revision. Never let a model or request body choose a
service URL, agent name, token audience, or tool. Each deployment owns provider credentials and
the registered tools for its one agent.

## Request and state handoff

1. **Authenticate at the host.** Validate the user's session or token, resolve the subject, tenant,
   and effective scopes, and load only that user's permitted preferences and session summary. Build
   the `AuthenticatedCaller` from this trusted result; never construct it from JSON fields supplied
   by the caller.
2. **Claim an execution.** Generate an unpredictable execution ID. Atomically claim it in the host
   workflow store before calling the pipeline, so retries or multiple host replicas cannot execute
   the same workflow concurrently. Bind the claim to the tenant, subject, request fingerprint, and
   workflow version. Release or expire the lease on cancellation or process failure.
3. **Call triage.** Send the current task and bounded `HostContext` to the triage service. Its
   `output_schema` yields a validated plan with bounded `rag_query` and `analyst_task` fields. The
   plan is advisory input: it cannot grant capabilities, select an endpoint, or bypass host
   authorization.
4. **Authorize and retrieve.** The host checks `rag:read` before querying the retriever and applies
   the authenticated tenant filter inside the data access layer. The host validates and bounds the
   returned snippets, then passes them as `HostContext.rag_snippets`. Gabby's typed host context is
   request-scoped personalization and evidence; it is not an identity or tenant authorization
   mechanism. The host owns retrieval and its storage. Gabby does not automatically make a
   request's snippets tenant-safe, and its local SQLite stores are not a distributed tenant router.
5. **Run specialists.** Dispatch authorized RAG and analyst work concurrently. Each call gets a
   short-lived, audience-specific JWT containing only `pipeline:run` plus the worker scope it needs.
   The API authenticator verifies issuer, audience, signature, expiry, and subject; `run_scopes` and
   `stream_scopes` protect their respective routes. The analyst service also applies its
   `policies.scope_rules` to narrow its fixed tool and permission allowlists.
6. **Checkpoint outcomes.** Save the bounded result, safe status, trace ID, request fingerprint,
   and workflow version under a tenant-partitioned stage key. The host—not Gabby—owns this durable
   state. Keep raw prompts and tool data out of ordinary logs. Encrypt sensitive checkpoint content,
   limit access, and apply a retention/deletion policy.
7. **Synthesize and return.** Send only the bounded worker outcomes to the synthesis service and
   relay its SSE text deltas if desired. Treat deltas as provisional until the `completed` event
   arrives. A disconnected client or failed stream must not cause the host to record an incomplete
   synthesis as a completed workflow.

`HostContext` supports bounded user preferences, session summaries, and RAG snippets. Pass only
context needed by a given worker; the example sends retrieved snippets only to the RAG agent and
does not send profile/session data or retrieved evidence to the analyst. Caller identity and scopes
travel in the verified bearer token and authenticated `Principal`, not in model-visible context or
arbitrary metadata. Gabby is stateless between runs; the host decides what state to persist and send
on the next request.

## Authorization and data boundaries

- Require a host-authenticated `pipeline:run` capability before starting a workflow. Check each
  specialist capability before dispatch (`rag:read` and `sql:finance_readonly` in the example).
- Configure JWT validation independently for each service audience. Keep signing keys in the host's
  secret manager; use short-lived, narrowly scoped tokens and rotate keys under the identity
  provider's procedure.
- On the analyst service, make the tool an application-owned, read-only aggregate such as
  `finance_summary`; do not ask the model to generate arbitrary SQL. Use a dedicated read-only
  database principal, parameterized queries, query timeouts, row limits, and tenant predicates.
  Derive tenant identity from the authenticated `ToolContext.principal`, never from tool arguments,
  prompt text, or `HostContext`.
- Run host retrieval with the authenticated tenant filter. Check document visibility before
  returning each snippet; treat its text and metadata as untrusted, and preserve source identifiers
  for citations. A prompt telling the model to ignore injected instructions is defense in depth,
  not the tenant isolation control.
- For any side-effecting or elevated action, keep the approval decision in the host workflow and
  require an explicit approval record before dispatch. Gabby's approval hooks are per-call callbacks;
  they do not provide a durable pause/resume workflow. The reference analyst is read-only.
- Keep worker outputs bounded and mark them as untrusted evidence when synthesizing. A worker's
  output cannot grant another worker authority.
- Use HTTPS for remote service URLs, private service networking where available, and ingress
  limits. `create_app` concurrency limits and token/cost policies are per process or per agent run,
  not a workflow-wide distributed quota.

## Failure recovery

| Failure | Host behavior |
|---|---|
| Invalid or unavailable triage | Stop before dispatch; return a typed, safe failure and retain no fabricated plan. |
| Caller lacks a worker scope | Do not call that service; record `not_authorized`, and continue only with authorized work. |
| Tenant retriever is unavailable or returns no evidence | Mark retrieval unavailable/empty; skip the RAG worker. The analyst may still run if authorized. |
| One specialist times out or returns an API error | Record that stage as unavailable. Continue with other completed, authorized results and disclose the partial result during synthesis. |
| No worker provides usable evidence | Return a deterministic host-generated partial/failure response without asking synthesis to invent an answer. |
| Synthesis fails after specialists completed | Preserve successful stage checkpoints; retry synthesis under the host's retry policy without rerunning completed read-only workers. |
| Host process or caller stream is cancelled | Propagate cancellation, stop awaiting child work, keep completed checkpoints, and mark/release the host execution lease. |
| Same request is retried | Reuse only checkpoints whose tenant, subject/scopes, request/context fingerprint, workflow version, and agent revisions match. |

Retry only operations that are safe to repeat. Gabby does not implicitly retry tool calls. If a
worker performs side effects, add a host idempotency key and a durable operation ledger before
allowing retries; this reference pipeline's analyst is read-only.

The example checkpoint interface does not implement leases or a database. The host must provide an
atomic execution claim and a checkpoint store with tenant isolation, conditional writes, and durable
consistency appropriate to its deployment. Do not use process-local dictionaries as production
workflow state.

## Budgets, concurrency, and observability

Set token and estimated USD limits on every Gabby agent. These limit one agent run; the call that
crosses a limit has already completed, and a multi-stage workflow can otherwise spend the sum of
several per-run limits. For a hard workflow-wide cap, the host must maintain an atomic budget ledger,
reserve budget before dispatch (including parallel work), reconcile provider-reported usage, and
refuse later stages when the remaining budget is exhausted. Do not treat usage estimates as billing
guarantees.

Limit concurrent workflows and specialist fan-out at the host. Gabby's capacity gate is per process,
so horizontal replicas need a separate host-side quota or admission limit. Add backpressure for model
provider, retrieval, and database capacity; bound all request, context, result, and stream sizes.

Propagate a host correlation ID in allowlisted metadata such as `pipeline_execution_id`; do not put
tokens, caller PII, or confidential task text in metadata. Record each Gabby `trace_id` with the
stage result. Define trace access and retention with the same care as checkpoint data. If the host
exports usage, compute it from provider-reported result metadata and label estimates as estimates.

## Reference implementation and limits

[`examples/host_orchestrated_pipeline/`](../examples/host_orchestrated_pipeline/) contains four
agent configuration templates and a Python orchestration reference. The host must implement its
token issuer, tenant retriever, checkpoint store, atomic execution claim, and registered finance
tool. The reference code bounds handoffs, validates triage output again, uses fixed service
endpoints, skips unauthorized workers, runs authorized specialists concurrently, reuses compatible
successful checkpoints, and streams only the final synthesis stage.

It is an integration example rather than a complete production application: it does not provide a
database, identity provider, secret manager, deployment manifests, distributed lease, workflow-wide
cost ledger, or finance data tool. `AgentTool` composition remains available when the desired control
flow is model-selected rather than host-selected. See [ADR 0130](architecture/adr/0130-host-orchestrated-multi-agent-pipelines.md)
for the ownership decision and consequences.
