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

# Contributing to Gabby

Gabby is an agent construction and runtime framework. Contributions should preserve the boundary
between reusable agent definitions and transient executions, and must not imply that prompting or
retrieval modifies model weights.

Contributors may use AI tools as assistants, but remain responsible for reviewing and validating
their changes. Follow the [AI usage guide](docs/AI_USAGE.md) when using AI during development.

## Before changing code

Read the [architecture draft](docs/ARCHITECTURE.md), the relevant user guide, and any accepted
[architecture decision record](docs/architecture/adr/README.md). Identify which component owns the
behavior: definition resolution, model provider, environment, skill, tool, knowledge, policy,
runtime, verification, tracing, or transport. Changes to public contracts, concurrency/lifecycle
behavior, security assumptions, dependency direction, or deployment boundaries need an ADR and a
clear migration path where callers can observe the change.

Provider SDKs, credentials, and network clients belong in provider adapters. The runtime owns
orchestration; consuming applications own durable conversation state. Tool permissions must be
enforced at runtime and must not depend on prompt instructions.

## Development environment

Gabby supports Python 3.11 through 3.14. Use the committed lockfile for development:

```bash
python -m pip install uv==0.13.5
uv sync --frozen --group dev --extra server --extra auth --extra skill-signing
uv lock --check
```

Choose a Python version from the supported 3.11–3.14 range; the repository does not pin a local
interpreter version. On Windows, add `--extra windows-sandbox` to install the optional Docker
transport dependency. To work on an optional integration, install its matching `mcp`,
`opentelemetry`, `trace`, or `crewai` extra. CI installs only the common test and runtime extras.
To install the shared local hooks, install `pre-commit` in your
developer environment and run `pre-commit install`; run `pre-commit run --all-files` before opening
a pull request.

Run the repository quality gates before submitting changes:

```bash
uv run --no-sync ruff check src tests scripts examples
uv run --no-sync ruff format --check src tests scripts examples
uv run --no-sync mypy src/gabby tests scripts examples
uv run --no-sync pytest --cov=gabby
uv build --out-dir dist
uv run --no-sync python scripts/check_package.py dist
uv run --no-sync pip-audit --skip-editable --progress-spinner off
uv run --no-sync python scripts/check_license_headers.py
uv run --no-sync python scripts/check_workflows.py
uv run --no-sync python scripts/check_scorecard.py
uv run --no-sync python scripts/check_documentation.py
```

Every behavior change should include focused regression coverage. Changes to cancellation, timeout,
cleanup, concurrency, redaction, policy enforcement, or HTTP framing need tests for both the normal
path and the failure boundary. Do not use live model APIs in the default test suite; use deterministic
provider fakes and local ASGI clients.

## Change requirements

Use the commit message format `<type>: <imperative summary>` for every commit. Keep the type
lowercase, use a concise imperative summary, and omit the final period. Common types include
`docs`, `feat`, `fix`, `refactor`, `test`, `build`, `ci`, and `chore`.

Examples:

```text
docs: clarify Gabby's project positioning
feat: add bounded tool result handling
fix: preserve cancellation during stream cleanup
refactor: isolate provider response parsing
test: cover concurrent tool cancellation
build: pin the container base image
ci: validate supported Python versions
chore: refresh maintainer references
```

Use a matching lowercase prefix for branch names: `ci/`, `docs/`, `feat/`, `fix/`, `roadmap/`, or `chore/`.
The pull request labeler uses these prefixes to apply labels; the corresponding label must exist in the repository.

Public classes and functions exported from `gabby` need precise annotations and concise docstrings.
Module docstrings state the module boundary. The documentation checker also verifies Markdown
headings, code fences, local links, and stale-work markers in comments. Comments explain ownership,
ordering, cancellation, security, or compatibility invariants. Avoid logging prompts, credentials,
provider bodies, tool arguments, or user context.

Update the closest guide and `CHANGELOG.md` when callers or operators can observe a change. Every
pull request should describe the owning boundary, behavior, validation commands, and any unverified
security or deployment assumptions. Keep generated environments, lock caches, credentials, and
unrelated formatting churn out of commits.

The maintainer release procedure is documented in [RELEASING.md](docs/RELEASING.md). Releases are
version-tagged and gated by the release verification workflow before the protected PyPI publish job.
Repository branch-protection expectations are in [repository governance](docs/REPOSITORY_GOVERNANCE.md),
and public compatibility and deprecation rules are in the [API stability policy](docs/API_STABILITY.md).
