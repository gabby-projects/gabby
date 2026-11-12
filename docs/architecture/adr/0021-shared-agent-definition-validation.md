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

# ADR 0021: Validate YAML and programmatic agent definitions consistently

- Status: Accepted
- Date: 2026-09-29

## Context

Gabby accepts agent definitions from both YAML files and Python `AgentDefinition` objects. YAML
loading checked required fields, mapping shapes, policy values, and provider credential boundaries,
while direct construction could reach runtime with malformed configuration and fail later or
differently.

## Decision

Use one `validate_agent_definition` function for YAML-loaded and in-memory `AgentDefinition`
objects. The YAML loader validates the decoded definition, and `Agent` validates programmatic
definitions before resolving skills, constructing built-in providers, or creating runtime state.
Both paths enforce required identity/model fields, text and mapping types, list values, execution
policy constraints, and model credential/endpoint rules.

## Consequences

- Programmatic and YAML definitions fail at the same construction boundary for the same invalid
  fields.
- Applications can call the exported `validate_agent_definition` helper before constructing an
  agent.
- Pre-1.0 callers that relied on late validation or invalid values must correct their definitions.
- Runtime services injected by the host, such as models, retrievers, and handler callables, remain
  service references and are not validated as serialized configuration.

## Alternatives considered

- Validate only YAML and allow arbitrary programmatic definitions: rejected because `Agent` is also
  a public construction path and would permit policy/configuration bypasses.
- Maintain separate validation implementations: rejected because they can drift and produce
  different acceptance behavior for the same agent.
