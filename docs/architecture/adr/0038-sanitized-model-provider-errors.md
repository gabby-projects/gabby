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

# ADR 0038: Sanitize built-in model-provider errors

- Status: accepted
- Date: 2026-10-01

## Context

Built-in OpenAI-compatible completion and streaming adapters included provider HTTP response
bodies and transport exception text in raised `ModelError` messages. Providers can echo submitted
prompts or include endpoint details, so direct callers could expose sensitive information through
application errors and logs even though the FastAPI service sanitized execution errors.

## Decision

- Report the HTTP status code for unsuccessful provider responses, but do not read or include the
  upstream error body.
- Use stable generic messages for request and stream transport failures; suppress exception
  chaining in the displayed traceback so transport details do not appear through standard error
  formatting.
- Keep runtime traces and HTTP/SSE error payloads on their existing stable, sanitized contracts.
- Treat injected providers as trusted extensions responsible for sanitizing their own exceptions.

## Consequences

Direct callers retain useful HTTP status information without receiving provider-controlled text.
Transport failures are less descriptive; applications needing provider diagnostics should capture
safe structured telemetry in a custom provider rather than forwarding raw exception contents.

## Alternatives considered

- **Keep a bounded body excerpt:** a short excerpt can still contain a prompt echo, credential, or
  private endpoint detail.
- **Expose raw errors only to direct callers:** direct library callers commonly forward exception
  strings to logs or clients, so this would leave a second disclosure path.
- **Add a diagnostic callback to the core provider contract:** defer until there is a stable,
  structured observability contract for provider-specific diagnostics.

## Compatibility and evidence

This pre-1.0 change removes provider-controlled details from built-in `ModelError` messages.
Provider contract tests cover completion and streaming HTTP error bodies and transport exception
messages. The focused model test module passed after the change; the full test matrix has not yet
been rerun for this ADR.
