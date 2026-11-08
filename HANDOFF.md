# Gabby maintainer handoff

## Current state

Gabby is a pre-1.0, async-first Python framework in the `undreamt-oss` organization. Orbit is a
separate ecosystem and has no organization or governance relationship with this project. Gabby's
agent runtime, provider, and sandbox gates are project-specific. The development environment is
Python 3.11–3.14, managed with `uv` and the committed `uv.lock`. Readiness evidence and known gaps live in the
[project scorecard](docs/PROJECT_SCORECARD.md); this file tracks maintainer-owned setup outside the
source tree.

## External setup to verify

These controls live in GitHub or PyPI settings and cannot be guaranteed by repository files alone:

- Confirm the team configured in `.github/CODEOWNERS` exists and has the required access.
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
