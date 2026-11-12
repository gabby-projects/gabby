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

# ADR 0127: Release-signed starter skill bundles

- Status: accepted
- Date: 2026-11-12

## Context

Users need examples they can inspect and adapt without trusting opaque, remotely hosted agent
definitions. A release bundle must make its capability grants, signer, and source review visible,
while keeping private signing material out of Git.

## Decision

Keep the customer-support triage, read-only SQL analyst, and sandboxed Git assistant as source
directories under `bundles/starter-packs/`. Each contains an agent definition, a skill package, a
human-readable audit note, and only the workspace fixtures needed by that example. Release tooling
builds deterministic skill archives, signs them with a host-provided Ed25519 key, verifies the
result against the derived public key, and emits the public key and audit material alongside the
artifact. The private key is supplied through the protected release environment and is never stored
in the repository.

## Consequences

Source bundles remain reviewable and can be changed through ordinary pull requests. A source bundle
is not itself a signed release artifact. A release signing job must be explicitly enabled and its
publisher key must be protected and rotated by maintainers. Signature verification establishes
artifact integrity and signer identity; it does not independently certify safe behavior. Bundles
must continue to use least-privilege tools and the normal Gabby runtime policies.
