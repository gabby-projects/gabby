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

# Starter bundles

This directory contains three reviewed source bundles: customer-support triage, a read-only SQL
analyst, and a sandboxed Git assistant. Each includes an `agent.yaml`, a Gabby `skill.yaml`, and an
`AUDIT.md` that states the granted capability and required deployment checks.

The source tree is not itself a publisher-signed release. Signed `.gabskill` artifacts are generated
for tagged releases by `scripts/build_starter_bundles.py` only when the protected
`starter-bundle-signing` GitHub environment is configured with `GABBY_STARTER_SIGNING_KEY` and
`GABBY_STARTER_SIGNING_KEY_ID`. The workflow attaches the signed packages and public key to the
GitHub release. Until the maintainer provisions that key and enables the release job, no one should
describe these source templates as pre-signed official packages. Never put the private key in this
repository. Consumers should verify package signatures against the published public key and confirm
the release source before trusting that key.

After downloading a release bundle, install the signed package and place its public key in the
trusted-key directory:

```sh
mkdir -p ./skills ./trusted-publishers
gabby skill install ./customer-support-triage-1.0.0.gabskill \
  --registry ./skills --trusted-key-dir ./trusted-publishers
```

Keep the matching `agent.yaml` next to `skills/`, replace the model placeholder, and provide the
host-side dependencies described in the audit file. The SQL bundle additionally requires a
host-registered read-only `sql_read_only_query` tool. The Git bundle requires `sandbox_tools()` and
a disposable repository workspace. Copy the checkout to `workspace/` and replace the placeholder
image with a reviewed image that contains Git; its `shell_run` prompt is not a command authorization
boundary. Configure an immutable image digest before deploying the Git bundle.

Build and sign locally with a publisher-managed key:

```sh
GABBY_STARTER_SIGNING_KEY_ID=undreamt-starter-v1 \
GABBY_STARTER_SIGNING_KEY="$GABBY_SKILL_SIGNING_KEY" \
python scripts/build_starter_bundles.py --output dist/starter-bundles
```

The build fails closed unless the Ed25519 key is present, validates all three source skills,
creates detached signatures, verifies each signature against the derived public key, and writes the
public key into the output. Review and test bundle changes before signing a release.
