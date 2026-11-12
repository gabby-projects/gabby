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

# ADR 0019: Require HTTPS for remote built-in model providers

- Status: Accepted
- Date: 2026-09-29

## Context

Model requests can contain prompts, retrieved documents, tool results, and bearer credentials.
Allowing a built-in provider to send these over remote HTTP exposes them to network observers and
intermediaries.

## Decision

Built-in OpenAI-compatible, Ollama, and Hugging Face providers require HTTPS for non-loopback
`base_url` values. Plain HTTP is accepted only for loopback endpoints such as local Ollama. Gabby
validates agent configuration and also validates direct construction of the built-in adapters.
Applications that need another transport can inject their own `ModelProvider` implementation.

## Consequences

- Remote prompts and provider credentials use TLS by default and cannot be downgraded through a
  built-in provider's URL setting.
- Local inference on loopback can use HTTP without extra TLS setup.
- This check validates transport scheme and endpoint locality; it does not establish endpoint
  identity beyond the guarantees of the configured HTTPS trust store.
- Custom providers own their transport security and must protect prompts and credentials.

## Alternatives considered

- Permit arbitrary HTTP URLs: rejected because built-in adapters may send sensitive prompts and
  bearer tokens over cleartext remote connections.
- Require HTTPS even for local inference: rejected because local inference services commonly use
  loopback HTTP and do not need network encryption across a host boundary.
