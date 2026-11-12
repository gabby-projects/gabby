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

# ADR 0121: Runtime specialization boundary

- Status: accepted
- Date: 2026-11-10

## Decision

Gabby gives an agent its requested character through user-defined instructions, enforced by the AI
enforcer within policies, tools, knowledge, approvals, verification, and execution pipelines. It does
not train models, modify model weights, or load model adapters.

## Rationale

Agent character and behavior belong in explicit, inspectable runtime configuration and governance
rules. This keeps Gabby's responsibility focused on enforcing those choices while executing the
configured agent request.
