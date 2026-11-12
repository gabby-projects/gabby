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

# ADR 0017: Keep provider credentials outside agent configuration

- Status: Accepted
- Date: 2026-09-29

## Context

Agent definitions are persistent, portable configuration and may be committed, shared, or included
in traces and support bundles. A provider API key or bearer credential embedded in that config can
be copied or exposed with the agent. The public guidance already directs hosts to use environment
lookups or inject their secret-aware provider.

## Decision

Agent configuration cannot contain `model.api_key`, credential-bearing model headers, URL
userinfo, or provider URL query parameters with credential-like names. Gabby enforces this for
YAML-loaded and in-memory `AgentDefinition` objects, and built-in provider `from_config` factories
reject the same fields. Providers resolve credentials through the
configured `model.api_key_env` variable or through a provider injected by the consuming host.
The environment reference must be a valid environment variable name. Provider constructors may
accept a key directly for host code that has already retrieved it from a secret manager; that
value must not be copied into agent configuration.

## Consequences

- Agent definitions stay portable without carrying provider secrets.
- Existing pre-1.0 callers that pass `api_key` through a model config mapping must switch to
  `api_key_env` or construct and inject a provider.
- Custom providers remain responsible for their own credential sources and safe error handling.
- The restriction catches common credential markers in header and query parameter names; it does
  not make arbitrary user-provided configuration or provider code secret-safe by itself.

## Alternatives considered

- Permit inline keys and rely on `.gitignore` or operator discipline: rejected because agent files
  are reusable portable artifacts and cannot safely police every host's handling practices.
- Allow only custom headers and rely on deployment tooling to scrub them: rejected for built-in
  providers because common authorization headers are direct credential storage paths.
