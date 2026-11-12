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

- Scope: classifies and drafts from the current request only; no tools or knowledge sources.
- Capability boundary: the agent definition grants no tools and caps the run at four steps.
- Sensitive data: instructions prohibit asking for credentials and require supplied support policy
  to determine entitlement or escalation.
- Review status: source reviewed for the declared scope; this is not a security certification or a
  guarantee that model output will always comply.
- Required deployment checks: configure an approved model, run organization-specific support
  policy tests, and review the final skill package signature against the publisher trust key.
