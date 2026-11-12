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

# ADR 0129: Template-generated language SDKs

- Status: accepted
- Date: 2026-11-12

## Context

The Python client does not serve teams that consume Gabby from TypeScript/Node.js, Go, or Rust.
These clients should remain small and match the public HTTP and SSE contracts without adding
language runtimes or code-generation dependencies to the Python package.

## Decision

Maintain the three client implementations as language-specific source templates under
`sdks/templates/` and regenerate checked-in packages with `scripts/generate_client_sdks.py`. Each
client implements stateless run and SSE calls, bearer-token configuration, and the API's resume
headers. Release workflows attach versioned source archives; the clients are not advertised as
separately published registry packages.

## Consequences

Template changes are reviewed and validated with their generated output. The SDKs must stay aligned
with `/v1`, and server contract changes need corresponding updates and tests in each language. They
do not own conversation history, authentication policy, retries for non-idempotent runs, or
deployment configuration. Consumers should use HTTPS and retrieve tokens from their own secret
stores.
