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

# ADR 0099: Bounded TOML knowledge ingestion

## Status

Superseded by ADR 0125.

## Context

TOML is widely used for project metadata and application configuration, including Python project
metadata. Treating it as plain text loses the association between nested values and their keys.
Gabby's knowledge ingestion already provides bounded parsers for YAML and JSON, with replaceable
parser contracts and source-scoped indexing.

## Decision

Add `TOMLTextParser` for `.toml` files, using Python's standard-library `tomllib` parser. Decode
UTF-8 input with an optional byte-order mark, reject malformed input, and apply input, structural,
and rendered-output limits. Normalize TOML date and time values to ISO-8601 strings, then render
nested tables as dotted key paths and arrays with indexed positions. Register it in `FileIngestor`
and expose it from the package root.

## Consequences

- TOML configuration is searchable without adding a runtime dependency.
- Strict TOML parsing rejects duplicate keys and malformed documents.
- One source maps to one searchable page; its text retains key paths and array indexes.
- Parser input, structure, and output are bounded, while `FileIngestor` retains responsibility for
  filesystem confinement and source replacement.

## References

- [`TOMLTextParser` extension guide](../../EXTENSIONS.md)
- [Python `tomllib` documentation](https://docs.python.org/3/library/tomllib.html)
