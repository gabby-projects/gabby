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

# ADR 0130: Host-Orchestrated Multi-Agent Pipelines

- **Status:** Accepted
- **Date:** 2026-11-12
- **Decision owners:** Gabby maintainers

## Context

Applications may need to route one user request through a classifier, tenant-scoped retrieval,
specialist agents, and a response synthesizer. Gabby provides a stateless HTTP/SSE API, typed
request context, route authentication, scope-aware policies, per-run limits, and a Python client.
Its product boundary leaves workflow choice, durable application state, and tenant routing to the
host. `create_app()` serves one configured agent per service instance. `AgentTool` composition
already supports a parent model invoking a child agent, but that is model-selected delegation rather
than deterministic host-owned fan-out/fan-in.

The reference architecture must not imply capabilities Gabby does not provide. In particular,
request context is not authentication; a local retrieval store does not enforce cross-service tenant
isolation; route scopes and agent tool scopes are separate controls; approvals are per-call callbacks
rather than a durable pause/resume workflow; and token/USD limits apply to each run, not an entire
host workflow.

## Decision

Document and provide a reference example for host-owned multi-agent orchestration. The host will:

1. authenticate the caller and resolve subject, tenant, and scopes;
2. claim and persist a workflow execution using a host-owned durable store;
3. call separately configured Gabby services through fixed deployment endpoints;
4. validate bounded structured routing output and independently authorize each stage;
5. perform tenant-filtered retrieval in the host or a trusted host service and pass relevant text
   through `HostContext`;
6. carry the host-verified tenant ID in short-lived signed worker tokens, bound retrieval latency,
   and run independent authorized work concurrently;
7. checkpoint bounded results and traces, recover only from matching workflow/request/agent
   revisions, and synthesize completed or partial results through a separate Gabby service.

The reference does not add a general workflow engine or durable state to Gabby's runtime. It uses
the existing versioned HTTP/SSE and Python client contracts. Each Gabby service remains configured
for one agent. The host is responsible for distributed admission and leases, secret/key management,
workflow-wide budgets, retrieval authorization, side-effect idempotency, and final state retention.

## Security constraints

- Resolve caller identity and tenant only from trusted host authentication. Never trust body fields,
  prompts, RAG text, or model-generated routing plans for identity or authorization.
- Use short-lived JWTs with a fixed audience and least-privilege scopes for each service. Include the
  host-verified tenant as a signed `tenant_id` claim. Configure route-level `run_scopes` and
  `stream_scopes`; configure `policies.scope_rules` to further narrow the analyst's fixed tool and
  permission allowlists.
- Keep endpoint URLs, agent names, JWT audiences, and deployment revisions in trusted deployment
  configuration. Do not allow model-directed endpoint selection.
- Register only bounded, parameterized, read-only data tools for the analyst example. Derive tenant
  predicates from the verified `Principal.tenant_id` available to the host tool handler, and fail
  closed when it is absent or cannot be resolved.
- Apply tenant filtering before retrieved content enters `HostContext`; bound and mark all retrieved
  and worker content as untrusted evidence. Bound retrieval latency so an unavailable retriever
  cannot prevent independent authorized analysis.
- Protect checkpoint content with tenant partitioning, encryption, access controls, conditional
  writes, and retention/deletion policy. Do not persist credentials or raw prompts in ordinary
  traces or metadata.
- Enforce one active workflow owner per execution ID in the host. Gabby's process-local capacity
  gate is not a distributed workflow lock or tenant quota.
- Configure per-run token/USD limits on each agent. A host-wide hard spend cap requires a separate
  atomic reservation and usage-reconciliation ledger; per-run limits do not add up to a workflow
  cap.

## Consequences

The host can deterministically skip unauthorized workers, parallelize independent read-only stages,
store durable checkpoints, and recover without making Gabby stateful. One worker failure can yield a
partial result without misrepresenting that worker as successful. Fixed single-agent services also
make each worker's tools, model, policy, and credentials independently deployable.

The host owns more code and operational responsibility: identity, orchestration, persistence,
execution leases, quotas, durable retries, tenant-safe retrieval, and side-effect idempotency. The
reference code is deliberately an example with protocols rather than a bundled database, identity
provider, or finance tool. Stage result data is sensitive and requires host-defined retention and
access policies.

`AgentTool` remains the supported option for model-selected, bounded child-agent delegation. This
decision does not merge that mechanism with host orchestration or make Gabby a general agent
orchestrator. See [the host pipeline guide](../../HOST_ORCHESTRATED_PIPELINES.md).
