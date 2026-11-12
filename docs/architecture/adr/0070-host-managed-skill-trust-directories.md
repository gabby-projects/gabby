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

# ADR 0070: Host-managed skill trust directories

- Status: Accepted
- Date: 2026-10-02

## Context

`SkillTrustPolicy` snapshots an application-supplied key mapping, while the CLI accepts public keys
one at a time. Applications and operators need one explicit host-owned source they can version,
rotate, and reuse across agent startup and skill package commands without moving trust into agent
configuration.

## Decision

- Add `load_skill_trust_keys(directory)` and `SkillTrustPolicy.from_directory(directory)` for
  directories containing raw Ed25519 public keys named `KEY_ID.pub`.
- Require a non-symlink directory with one to 256 regular key files. Reject subdirectories,
  unexpected entries, malformed key IDs, files not exactly 32 bytes, and files changed while they
  are opened.
- Add `--trusted-key-dir` to CLI verification, installation, remote fetch, and installed-skill audit
  commands. It may be combined with individual `--trusted-key` arguments only when key IDs do not
  collide.
- Continue to snapshot keys when constructing `SkillTrustPolicy`. Operators load the new key set
  and reconstruct agents to apply routine trust rotations. Active revocation remains the separate
  responsibility of `SkillRevocationChecker`.
- Keep directory files outside agent YAML and package files. Private signing keys remain with the
  publisher and are never accepted by the trust-directory loader.

## Consequences

An operator can maintain one bounded host trust directory and reuse it for local and remote package
verification and application startup. Rotation is explicit and auditable through ordinary
deployment configuration changes. Each running agent retains its construction-time trust snapshot;
multi-instance distribution, revocation propagation, and key-store backups remain deployment or
host responsibilities.

## Alternatives considered

- Store trusted keys in agent YAML: rejected because agent authors must not control the trust policy
  of the consuming application.
- Add a Gabby-owned key-generation and private-key management CLI: rejected because private signing
  key provisioning and custody belong to publisher secret-management systems.
- Add a mutable process-wide trust registry: rejected because it would break immutable agent plans
  and make concurrent runs observe different signer policies.
