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

# ADR 0111: Bounded AsciiDoc and reStructuredText ingestion

## Status

Superseded by ADR 0125.

## Context

Developers often keep framework documentation and runbooks in AsciiDoc or reStructuredText. Gabby's
default `FileIngestor` accepted Markdown and plain text, but rejected these common UTF-8 source
formats despite using a replaceable parser contract.

## Decision

- Add `MarkupTextParser` for `.adoc`, `.asciidoc`, and `.rst` files in the default parser set.
- Preserve the original markup source and line order as searchable text rather than attempting a
  partial format renderer.
- Bound parser input and output, require strict UTF-8, strip an optional UTF-8 BOM, and reject NULs.
- Never evaluate directives, resolve include paths, fetch remote resources, or execute embedded code.

## Consequences

Documentation prose and labels remain searchable without an external parser dependency. Markup
syntax is retained in indexed content. Hosts that need rendered output can provide a custom
`FileParser` with a separately reviewed directive and resource policy.

## Verification

Parser tests cover source preservation, BOM decoding, invalid UTF-8, NUL rejection, byte and output
limits, and default directory ingestion of both formats into SQLite FTS5.
