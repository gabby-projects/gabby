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

# Bundle review

- Scope: read-only inspection of a caller-provided repository checkout.
- Capability boundary: agent policy allowlists only `shell_run`; container networking is disabled by
  the default sandbox contract and CPU, memory, process count, and run duration are bounded.
- Required host controls: register `sandbox_tools()`, place a disposable checkout under `workspace/`,
  keep credentials and engine sockets out of the sandbox, and use a pinned image digest in production.
- Review status: source reviewed for the declared scope; the skill prompt cannot prevent arbitrary
  shell arguments by itself.
- Required deployment checks: verify that the selected image contains only required binaries and
  test the actual sandbox configuration on the deployment's container engine.
