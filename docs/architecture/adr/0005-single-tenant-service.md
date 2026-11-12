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

# ADR 0005: One tenant per Gabby service instance

**Status:** Accepted by the project architect.  
**Date:** 2026-09-29.

## Context

Gabby serves agent execution through an ASGI app. Authentication identifies the caller, but the
current runtime does not scope model clients, retrievers, traces, secrets, policies, or sandboxes by
tenant. Adding a shared-process tenant registry before those resources have an isolation contract
could let one tenant's data or credentials cross into another tenant's run.

## Decision

- A Gabby service instance serves one tenant and one configured agent.
- Deployments isolate tenants by running separate Gabby service instances and supplying separate
  credentials, resource handles, configuration, and storage for each instance.
- `Principal.subject` identifies a caller inside that service. It does not select a tenant or grant
  per-agent/tool authorization by itself.
- The shared-process, multi-tenant agent registry is out of scope until providers, retrieval,
  secrets, traces, policies, budgets, and sandbox lifecycle all carry and enforce tenant scope.

## Consequences

The existing `create_app(agent, ...)` shape matches the initial tenant model. Deployments needing
multiple tenants must route requests to separately configured service instances. Authentication
alone does not provide tenant authorization or isolation; hosted deployments remain responsible for
service routing and instance separation.
