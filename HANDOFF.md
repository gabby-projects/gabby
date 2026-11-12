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

# Gabby maintainer handoff

## Current state

Gabby is a pre-1.0, async-first Python framework in the `undreamt-oss` organization. Gabby's agent
runtime, provider, and sandbox gates are project-specific. The development environment is
Python 3.11–3.14, managed with `uv` and the committed `uv.lock`. Readiness evidence and known gaps live in the
[project scorecard](docs/PROJECT_SCORECARD.md); this file tracks maintainer-owned setup outside the
source tree.

## External setup to verify

These controls live in GitHub or PyPI settings and cannot be guaranteed by repository files alone:

- Confirm the user or team configured in `.github/CODEOWNERS` exists and has the required access.
- Protect the default branch with pull-request review, code-owner review, and the exact stable CI
  status checks reported by GitHub. Keep force-push and deletion restrictions enabled.
- Confirm CodeQL and OpenSSF Scorecard publish reliable pull-request and default-branch results;
  require them only after those checks are stable.
- Configure the protected `pypi` environment, tag restrictions, and PyPI Trusted Publisher described
  in [RELEASING.md](docs/RELEASING.md). Do not store a long-lived PyPI token in repository secrets.
- Confirm the security advisory reporting route and Dependabot alerts are enabled for the repository.

Record verification dates and any deviations here after checking the live settings. Do not treat a
workflow definition as proof that its hosted job, branch rule, team permission, or publishing trust
has been configured or has passed.

## Local release gate

Before a release, follow [CONTRIBUTING.md](CONTRIBUTING.md) and
[RELEASING.md](docs/RELEASING.md), then update the
[project scorecard](docs/PROJECT_SCORECARD.md) with current evidence. Hosted checks, provider
acceptance, and platform validation remain separate evidence from local results.
