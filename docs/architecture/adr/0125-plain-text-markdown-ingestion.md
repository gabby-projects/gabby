# ADR 0125: Plain-text and Markdown ingestion scope

- Status: Accepted
- Date: 2026-11-11

## Context

Gabby had accumulated built-in parsers for many specialized formats, including PDF/OCR, office
documents, email, archives, feeds, and structured data. These parsers expanded dependencies,
maintenance, and security review beyond the core Agent Runtime and Governance Framework. The
runtime needs a direct path for indexing text knowledge, while applications can own specialized
document extraction.

## Decision

- Keep built-in ingestion for bounded UTF-8 `.txt`, `.log`, `.md`, and `.markdown` files.
- Preserve the source text and Markdown markup; do not interpret format-specific directives or
  execute file contents.
- Keep `FileParser`, `ParsedPage`, `TextChunker`, and `FileIngestor(parsers=...)` as extension
  contracts so a host can provide additional trusted parsers.
- Keep root-confined path checks, input and extracted-text bounds, deterministic chunking, metadata,
  and atomic per-source replacement in the runtime ingestion pipeline.
- Remove bundled parsers and optional dependencies for PDF/OCR, office files, email, archives,
  feeds, and structured-data formats.

## Consequences

The built-in RAG path stays small and predictable. Hosts that ingest specialized formats must own
their parser dependencies and extraction lifecycle, then provide the resulting text through a
custom parser or the retrieval interfaces. Custom parsers run as trusted host code and should use
process or service isolation when parsing complex untrusted files.

## Alternatives considered

- Keep every parser optional: rejected because the large parser surface still makes Gabby responsible
  for maintaining and securing format-specific extraction behavior.
- Remove ingestion entirely: rejected because bounded text and Markdown ingestion is a useful direct
  path into Gabby's knowledge stores.

## Compatibility and evidence

This is a pre-1.0 breaking change. Built-in file extensions and parser exports are reduced; hosts
that depended on removed parsers should provide a `FileParser` implementation. Contract tests cover
the remaining text formats, input bounds, and parser injection.
