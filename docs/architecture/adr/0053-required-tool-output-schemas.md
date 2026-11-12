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

# ADR 0053: Required tool output schemas

## Status

Accepted

## Context

The public tool contract calls for input and output schemas. Gabby already required input schemas,
but treated output schemas as optional. A tool without one could return any JSON value without
runtime validation, allowing malformed observations to reach a model or downstream consumer.

## Decision

- Require every `Tool` to declare an output JSON Schema at construction, alongside its input schema.
- Validate the schema at construction and validate each handler result before it becomes model
  context. Result serialization and the configured byte cap still apply.
- Keep output schemas out of the model's tool-call parameters; the schema is a runtime contract,
  not permission for the model to shape host output.
- Apply the requirement to host-trusted and sandboxed tools, including custom `tool.execute`
  handlers. Built-in shell and filesystem tools already have explicit result schemas.
- Treat this as a pre-1.0 API tightening. Missing schemas fail during construction; no permissive
  implicit schema is supplied.

## Consequences

Tool authors must describe the values their handlers return. Invalid results become typed tool
errors before model context construction, and tool registries hold only definitions with a checked
input/output contract. Broad schemas remain possible, but host applications should use specific
properties and required fields when the result shape affects application behavior.
