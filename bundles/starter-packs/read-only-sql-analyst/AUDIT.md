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

- Scope: explains results from one host-registered `sql_read_only_query` tool.
- Capability boundary: agent policy allowlists only that tool and limits calls to three per run.
- Required host control: the tool must use a read-only database principal, enforce query and row
  limits, reject multi-statement or mutating operations, and authorize tenant scope independently.
- Review status: source reviewed for the declared scope; prompts alone do not enforce SQL safety.
- Required deployment checks: test the actual tool handler against DDL, DML, excessive scans,
  cross-tenant queries, secrets, and malformed model-generated input before use.
