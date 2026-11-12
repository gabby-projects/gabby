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

# OpenSSF Best Practices audit

**Assessment date:** 2026-11-12  
**Scope:** repository evidence and checks run on the current Linux worktree. This is a maintainer
checklist, not a claim that the OpenSSF Best Practices badge is at 100%. GitHub settings, hosted CI
results, release publication, and maintainer response history are marked unverified unless their
evidence is included below.

Statuses mean:

- **PASS** — repository evidence supports the criterion at the stated scope.
- **PARTIAL** — some controls exist, but a known requirement or verification step remains.
- **FAIL** — a required control is absent or the latest check fails.
- **UNVERIFIED** — the available checkout and tools cannot establish the result.
- **N/A** — the criterion does not apply to this Python-only project or to a release that has not
  occurred.

## Criteria

| # | Criterion | Status | Evidence and remaining work |
|---:|---|---|---|
| 1 | Software description (`description_good`) | PASS | [README.md](../README.md) describes the problem, runtime boundary, and intended users. |
| 2 | User feedback and contribution info (`interact`) | PASS | README links to GitHub contributions; issue templates and [CONTRIBUTING.md](../CONTRIBUTING.md) provide feedback paths. |
| 3 | Contribution process (`contribution`) | PASS | CONTRIBUTING explains pull requests, review, validation, and release ownership. |
| 4 | Contribution requirements (`contribution_requirements`) | PASS | CONTRIBUTING lists supported Python, style/type/test/build/security commands, regression expectations, and ADR guidance. |
| 5 | FLOSS license (`floss_license`) | PASS | The project is licensed under Apache-2.0 in [LICENSE](../LICENSE). |
| 6 | OSI-approved license (`floss_license_osi`) | PASS | Apache-2.0 is an OSI-approved license; the project declares it consistently in package metadata. |
| 7 | License location (`license_location`) | PASS | The standard root [LICENSE](../LICENSE) file contains the license text. |
| 8 | Basic documentation (`documentation_basics`) | PASS | README and the [documentation index](index.md) link to usage, architecture, deployment, operations, and security guidance. |
| 9 | Interface documentation (`documentation_interface`) | PASS | [README_GUIDE.md](README_GUIDE.md), [CLIENT.md](CLIENT.md), and the FastAPI OpenAPI schema document request and response contracts. |
| 10 | HTTPS support (`sites_https`) | PASS | Repository, clone, release, and download links use HTTPS; there is no separately operated project website. |
| 11 | Searchable discussion (`discussion`) | PASS | GitHub issues and pull requests are public, searchable, URL-addressable discussion channels. |
| 12 | English language (`english`) | PASS | Project documentation, issue templates, and contribution guidance are in English. |
| 13 | Maintained project (`maintained`) | PASS | The repository has recent changes and active CI/security workflows. This does not establish future response times. |
| 14 | Public repository | PASS | `undreamt-oss/gabby` is the public source repository. |
| 15 | Version control | PASS | Source modifications are tracked in Git. |
| 16 | Interim changes | PASS | Development and release changes are represented in Git history and working-tree changes; release artifacts are built from version-controlled sources. |
| 17 | Distributed version control | PASS | The project uses Git. |
| 18 | Changelog | PASS | [CHANGELOG.md](../CHANGELOG.md) has an Unreleased section and dated version entries. |
| 19 | Release notes | PARTIAL | Changelog entries and [RELEASING.md](RELEASING.md) define the release process. No major stable release has been published yet. |
| 20 | Version naming | PASS | `pyproject.toml` uses a consistent PEP 440 alpha version; release validation checks tags against package metadata. |
| 21 | Version tags | UNVERIFIED | The release workflow is tag-triggered, but no remote tag/release inventory was available in this audit session. Verify GitHub releases before the first publication. |
| 22 | Signed releases or tags | UNVERIFIED | Release distributions have an attestation workflow, but signed Git tags and published attestations were not verified. Require and verify signed tags before release. |
| 23 | Bug reporting process | PASS | GitHub bug, feature, documentation, and question forms are present under `.github/ISSUE_TEMPLATE/`. |
| 24 | Public issue tracker | PASS | The repository uses the public GitHub issue tracker. |
| 25 | Timely issue responses | UNVERIFIED | This audit did not measure issue response intervals or establish a maintainer response target. |
| 26 | Searchable tracker | PASS | GitHub issues are searchable and individually URL-addressable. |
| 27 | Vulnerability reporting policy | PASS | [SECURITY.md](../SECURITY.md) describes confidential reporting and the information to include. |
| 28 | Private vulnerability channel | PARTIAL | Repository settings showed private vulnerability reporting enabled in the maintainer-provided screenshot. A non-maintainer could not use the direct advisory link earlier; verify the current reporter flow with a contributor account and document a working fallback contact. |
| 29 | Vulnerability response time | FAIL | SECURITY.md says “as soon as practical” but sets no initial-response deadline. Maintainers need to choose and publish a realistic target. |
| 30 | Public security policy | PASS | SECURITY.md is published at the repository root and linked from the README. |
| 31 | Automated build | PASS | GitHub Actions validates Python environments, builds distributions, checks package contents, and gates release publication. |
| 32 | Common build tools | PASS | The project uses standard Python packaging and the `uv` lock/sync/build workflow. |
| 33 | FLOSS build tools | PASS | The documented build, test, lint, type-check, and audit tools are open-source tools from the Python ecosystem. |
| 34 | Automated test suite | PASS | The repository maintains pytest unit, contract, and opt-in integration tests. See `tests/`. |
| 35 | Standard test invocation | PASS | CONTRIBUTING documents `uv run --no-sync pytest --cov=gabby`. |
| 36 | Code coverage | PASS | The current full Linux/Python 3.14.8 suite passed 1,624 tests and reached 90.06% branch-aware coverage, meeting the configured 90% gate. |
| 37 | Continuous integration | PASS | Pull-request workflows run test, platform, package, dependency, and documentation gates. Hosted results for this worktree are not available here. |
| 38 | Compiler or linter warnings | PASS | Ruff and strict mypy checks are configured as required quality commands and CI gates. |
| 39 | Strict warning policy | PARTIAL | Lint/type commands are gating, but the repository does not state a general warning-waiver and warning-expiration policy. |
| 40 | Address warnings | UNVERIFIED | Findings discovered during this audit are being fixed; no repository-wide warning-resolution history or response-time target is available. |
| 41 | Quality monitoring | PASS | CI runs coverage, lint, typing, documentation, workflow, package, dependency, and scorecard checks; scheduled CodeQL and OpenSSF Scorecard workflows are configured. |
| 42 | Style standards | PASS | Ruff format/check, `.editorconfig`, pre-commit guidance, and documented code conventions are provided. |
| 43 | Assurance rationale | PASS | Architecture docs, a threat model, contributing rules, and numbered ADRs explain design and assurance decisions. |
| 44 | Secure design knowledge | UNVERIFIED | The threat model records design controls and limits, but repository files cannot verify maintainers' individual security knowledge. |
| 45 | Implementation security knowledge | PARTIAL | Threat modeling and security tests cover common classes, but contributor guidance does not explicitly map review to OWASP Top 10 or CWE guidance. |
| 46 | Security standards awareness | PARTIAL | OpenSSF practices and deployment controls are documented; there is no maintained standards-mapping or maintainer training record. |
| 47 | Standard cryptography | PASS | Skill signatures and audit evidence use Ed25519; content integrity uses SHA-256. |
| 48 | FLOSS cryptography | PASS | Cryptographic operations use the open-source `cryptography` package rather than a project-written cipher/signature implementation. |
| 49 | Sufficient key lengths | PASS | Ed25519 raw private and public keys are validated at 32 bytes. |
| 50 | Correct crypto implementation | PASS | Gabby delegates Ed25519 operations to `cryptography`; SHA-256 uses Python's standard `hashlib`. |
| 51 | Perfect Forward Secrecy | PARTIAL | Remote model/client transports require HTTPS and the Nginx reference allows TLS 1.2/1.3, but Gabby cannot enforce the deployment's cipher suite or prove PFS for every host/provider. |
| 52 | Secure password storage | N/A | Gabby does not store user passwords; authentication and identity storage belong to the host application. |
| 53 | Secure randomness | PASS | Runtime identifiers use Python `uuid4`, which obtains randomness from the operating system; signing keys are supplied by the host and handled by the vetted crypto library. |
| 54 | Verified deliverables | PARTIAL | Skill packages support detached Ed25519 verification and release workflows configure provenance attestations. No release artifact or published attestation was verified in this audit. |
| 55 | MITM protection | PASS | Repository distribution and built-in remote model endpoints use HTTPS/TLS; deployment TLS remains host-owned. |
| 56 | No unpatched vulnerabilities | UNVERIFIED | A dependency audit can cover the lockfile, not every source or external GitHub alert. No release or complete code-scanning alert inventory was verified here. |
| 57 | Timely fixes | UNVERIFIED | The repository does not publish an evidenced 60-day vulnerability-fix record or response SLA. |
| 58 | Critical vulnerabilities | UNVERIFIED | Prioritization is described generally, but live security alerts and incident response history were not available. |
| 59 | No stored credentials | PARTIAL | Configuration rejects inline model credentials and docs prohibit committing secrets; repository-wide secret scanning and GitHub protection settings were not verified. |
| 60 | Static code analysis | PASS | GitHub CodeQL analyzes Python in pull requests, default-branch updates, and scheduled runs. |
| 61 | Common vulnerability checks | PASS | CodeQL's Python analysis applies standard security queries; no custom query pack is claimed. |
| 62 | Address SAST findings | UNVERIFIED | GitHub code-scanning alert state and resolution history were not available to this audit. |
| 63 | Regular SAST execution | PASS | CodeQL is configured for pull requests, pushes to `main`, and a weekly schedule. |
| 64 | Dynamic analysis | FAIL | No DAST scanner or regular fuzzing job is configured. API and sandbox integration tests are not a substitute for DAST. |
| 65 | Memory safety checks | N/A | The maintained implementation and Go/Rust client SDKs contain no project-owned C/C++ components. Third-party native dependencies are outside this source-level criterion. |
| 66 | Address DAST findings | UNVERIFIED | There is no DAST result set to review or close. |
| 67 | Regular DAST execution | FAIL | No recurring DAST or fuzzing workflow is configured. |

## Pull-request review follow-up

Greptile review timelines were checked for every PR number supplied in the task. Findings fixed in
this worktree are below; the current full local suite, static gates, package checks, and targeted
regression tests provide the verification evidence. A merged PR review is historical input, not
evidence that its finding remains unfixed in the current tree.

| PR | Greptile finding(s) | Current disposition |
|---:|---|---|
| [#48](https://github.com/undreamt-oss/gabby/pull/48) | MCP client API mismatch; model-overridable MCP target; missing resolved MCP config; CrewAI class closure; false-positive audit permission; event-loop-blocking writes; leaked CrewAI clients; concurrent audit chain writers; unbounded LF TRACE pending entries. | Fixed in runtime and tests. The audit exporter now has explicit close/lifetime ownership, and the docs describe exclusive path ownership. |
| [#47](https://github.com/undreamt-oss/gabby/pull/47) | Caller scope blocked all tools; permission-only scope error; incomplete/mixed token usage bypassed budgets; credential lookup exceeded tool timeout. | Fixed with regression coverage for scope filtering, normalized per-call usage, and shared tool deadlines. |
| [#46](https://github.com/undreamt-oss/gabby/pull/46) | CLI could not trust signed installed skills; JSON redaction broke structure; custom filter subclass skipped checks; buffered chunks inflated limits; stream usage was dropped; worker import polluted stdout. | Fixed with CLI trusted-key options, structured redaction, exact built-in fast-path selection, bounded payload accounting, usage merging, and worker stdout isolation. |
| [#44](https://github.com/undreamt-oss/gabby/pull/44) | Missing host-context/persona imports and forwarding; persona style limit; missing invalid-result trace; streaming rejection test only covered non-streaming. | Runtime contracts and streaming regression test are present in the current tree. |
| [#42](https://github.com/undreamt-oss/gabby/pull/42) | Public API test import; missing license header; unbounded ingestion discovery before caps; lost safety regressions; stale Ruff imports. | The discovery loop now checks caps as it finds files; tests cover bounded discovery, byte/count limits, symlinks, deterministic chunks, and SQLite source replacement. The license checker also covers supported dotfiles. |
| [#41](https://github.com/undreamt-oss/gabby/pull/41) | Context/memory was ambiguously described as an alternative to a caller-scoped retriever. | Guide now separates personalization context from access-controlled document retrieval. |
| [#39](https://github.com/undreamt-oss/gabby/pull/39) | Removed model adapter fields could be silently ignored; docs overclaimed an AI enforcer and removed model capabilities; package checker required removed training code. | Legacy `adapter_id` and `adapter_revision` now fail validation; docs distinguish model guidance from runtime-enforced controls. Package/lint checks are included in the local gates. |
| [#37](https://github.com/undreamt-oss/gabby/pull/37) | Contributor guide claimed a removed `.python-version` default. | CONTRIBUTING now says contributors select a supported Python version. |
| [#36](https://github.com/undreamt-oss/gabby/pull/36) | Branch-label mapping discussed a `bug/` prefix. | The maintainer explicitly chose `fix/` and removed `bug/`; the labeler follows that instruction. |
| [#34](https://github.com/undreamt-oss/gabby/pull/34) | `pdf-ocr` omitted a Pillow minimum. | PDF/OCR ingestion was subsequently removed from the supported product scope; no PDF extra remains. |
| [#31](https://github.com/undreamt-oss/gabby/pull/31) | Handoff and governance docs assumed CODEOWNERS used a team. | Instructions now allow either a user or team and require checking the configured owner's access. |
| [#28](https://github.com/undreamt-oss/gabby/pull/28) | PostgreSQL vector migration could persist an incorrect first-worker dimension. | PostgreSQL stores and migrations were removed from the supported product scope. |
| [#19](https://github.com/undreamt-oss/gabby/pull/19) | OpenSSF badge image lacked alt text. | README uses a named Markdown image link. |

No substantive Greptile finding was present in the fetched discussion timeline for PRs #45, #43,
#40, #38, #35, #33, #32, #30, #29, #27, #26, #25, #24, #23, #22, #21, #20, #17, #15, #14,
#13, #12, #11, #10, #9, #8, #7, #6, #5, #4, #3, #2, and #1.

## Cross-platform verification

The CI workflow defines unit/contract test jobs for Ubuntu, macOS, and Windows on Python 3.11–3.14.
This audit executed the local Linux/Python 3.14.8 suite only. Live Docker/Podman and hosted-provider
tests are opt-in and were skipped in that run; Windows live Docker acceptance is opt-in, and hosted
macOS live-engine acceptance is not configured. GitHub checks for this worktree were unavailable.
Therefore this audit does not claim that the current tree passed on macOS or Windows, or that live
container acceptance passed on any OS. Before claiming cross-OS verification, run and record the
documented Linux, Windows, and macOS container tests on their respective runners.

## Outstanding maintainer actions

- Choose and publish a private vulnerability report initial-response target; test the advisory flow
  from a contributor account and provide a usable fallback contact.
- Verify live GitHub settings and histories: issue response times, private reporting access, code
  scanning alerts, secret scanning, release tags, signed tags, branch protection, and hosted CI.
- Re-run `pip-audit` in a networked environment; the local run could not resolve PyPI.
- Add contract tests for the generated Go SDK; `go test ./...` currently reports no Go test files.
- Install/use a Rust toolchain and run `cargo check --locked`; this host has no Rust toolchain.
- Re-run Rust dependency and API checks after the toolchain is available; the lockfile alone does
  not establish that the SDK builds or passes tests.
- Add a reviewed DAST or fuzzing plan and recurring CI execution, or document a risk-based reason
  for deferring it; review and close findings from that work.
- Run and record live Docker/Podman sandbox acceptance on Linux, Windows, and macOS.
- Recalculate the weighted readiness score only after current evidence is reviewed; the linked
  historical scorecard is not a current OpenSSF percentage.
