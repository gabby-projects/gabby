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

# ADR 0085: Per-run skill integrity enforcement

- Status: Accepted
- Date: 2026-10-03

## Context

`SkillTrustPolicy` verified installed package signatures while constructing an agent. The agent
then held an immutable in-memory definition, but an operator could still mutate the installed
skill directory while the agent remained alive. The earlier trust decision did not detect that
change before a later run.

## Decision

- Before every async run and stream, revalidate the installed files for every resolved skill when
  the host supplied a `SkillTrustPolicy`.
- Require the package to remain valid under the same signer captured at construction. Fail closed
  with `SkillIntegrityError` before sandbox creation, model calls, or tools if verification fails.
- Count the check against the run deadline and record successful checks in the execution trace.
- Map integrity failures to a sanitized HTTP 403 for `/run` and sanitized SSE error events.
- Keep behavior unchanged when no host trust policy is configured.

## Consequences

Long-lived agents now detect installed package tampering before each new execution. Verification
uses the existing bounded package file, byte, and entry limits. It runs synchronously on the event
loop because cancelling a worker-thread future cannot stop its filesystem scan; hosts with large
trusted skill sets should account for the verification cost in run deadlines. This check does not
create an atomic filesystem snapshot against a concurrent hostile writer, and it does not interrupt
an already-running execution if files change after its admission check.

## Alternatives considered

- Reconstruct the agent after every audit: requires host lifecycle coordination and leaves a window
  between audit and reconstruction.
- Revalidate on a background thread: cancelling an await does not stop the worker's filesystem
  traversal, which can continue after the run has failed.
- Continuously revalidate during an active run: adds repeated I/O and cannot roll back completed
  tool side effects. Per-run admission gives a bounded, clear enforcement point.
