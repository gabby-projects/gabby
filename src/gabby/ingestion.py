# Copyright 2026-present Gabby Contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Bounded plain-text and Markdown ingestion with replaceable parser interfaces."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path, PureWindowsPath
from typing import Any, Protocol

from ._sync import run_sync_callback
from .knowledge import Document, SourceKnowledgeWriter


class TextChunker(Protocol):
    """Synchronous, replaceable text-to-chunks strategy."""

    def chunk(self, text: str) -> Sequence[str]:
        """Return deterministic, non-empty chunks in source order."""
        ...


@dataclass(frozen=True)
class ParsedPage:
    """Text extracted from one logical page of a source document."""

    text: str
    page_number: int | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


class FileParser(Protocol):
    """Replaceable synchronous parser for a bounded source file."""

    extensions: frozenset[str]

    def parse(self, content: bytes) -> Sequence[ParsedPage]:
        """Extract source-ordered pages from the provided bytes."""
        ...


class _Utf8Parser:
    def __init__(
        self,
        extensions: frozenset[str],
        *,
        max_input_bytes: int = 10 * 1024 * 1024,
        max_extracted_chars: int = 10_000_000,
    ) -> None:
        for name, value in (
            ("max_input_bytes", max_input_bytes),
            ("max_extracted_chars", max_extracted_chars),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        self.extensions = extensions
        self.max_input_bytes = max_input_bytes
        self.max_extracted_chars = max_extracted_chars

    def parse(self, content: bytes) -> tuple[ParsedPage, ...]:
        if not isinstance(content, bytes):
            raise TypeError("content must be bytes")
        if len(content) > self.max_input_bytes:
            raise ValueError(f"input exceeds max_input_bytes={self.max_input_bytes}")
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError:
            raise ValueError("input must be valid UTF-8") from None
        if "\x00" in text:
            raise ValueError("input must not contain NUL characters")
        if len(text) > self.max_extracted_chars:
            raise ValueError(f"text exceeds max_extracted_chars={self.max_extracted_chars}")
        return (ParsedPage(text),)


class Utf8TextParser(_Utf8Parser):
    """Read plain UTF-8 text and log files without format-specific interpretation."""

    extensions = frozenset({".txt", ".log"})

    def __init__(
        self, *, max_input_bytes: int = 10 * 1024 * 1024, max_extracted_chars: int = 10_000_000
    ) -> None:
        super().__init__(
            self.extensions,
            max_input_bytes=max_input_bytes,
            max_extracted_chars=max_extracted_chars,
        )


class MarkupTextParser(_Utf8Parser):
    """Read Markdown source as bounded UTF-8 text, preserving its markup for retrieval."""

    extensions = frozenset({".md", ".markdown"})

    def __init__(
        self, *, max_input_bytes: int = 10 * 1024 * 1024, max_extracted_chars: int = 10_000_000
    ) -> None:
        super().__init__(
            self.extensions,
            max_input_bytes=max_input_bytes,
            max_extracted_chars=max_extracted_chars,
        )


class ParagraphChunker:
    """Group paragraphs into bounded chunks and repeat a small tail across boundaries."""

    def __init__(self, *, max_chars: int = 2000, overlap_chars: int = 160) -> None:
        if isinstance(max_chars, bool) or not isinstance(max_chars, int) or max_chars < 1:
            raise ValueError("max_chars must be a positive integer")
        if (
            isinstance(overlap_chars, bool)
            or not isinstance(overlap_chars, int)
            or overlap_chars < 0
            or overlap_chars >= max_chars
        ):
            raise ValueError("overlap_chars must be a non-negative integer smaller than max_chars")
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars

    def chunk(self, text: str) -> list[str]:
        """Split text into bounded, source-ordered chunks with configured overlap."""
        if not isinstance(text, str):
            raise TypeError("text must be a string")
        paragraphs = [
            part.strip()
            for part in re.split(r"\n\s*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
            if part.strip()
        ]
        chunks: list[str] = []
        pending = ""

        def flush() -> None:
            nonlocal pending
            if pending:
                chunks.append(pending)
                pending = ""

        for paragraph in paragraphs:
            if len(paragraph) > self.max_chars:
                flush()
                chunks.extend(self._split_long_paragraph(paragraph))
                continue
            candidate = f"{pending}\n\n{paragraph}" if pending else paragraph
            if pending and len(candidate) > self.max_chars:
                flush()
                pending = paragraph
            else:
                pending = candidate
        flush()
        if self.overlap_chars == 0 or len(chunks) < 2:
            return chunks
        return [chunks[0], *(
            f"{previous[-self.overlap_chars:].lstrip()}\n{current}"
            if previous[-self.overlap_chars:].strip()
            else current
            for previous, current in zip(chunks, chunks[1:], strict=False)
        )]

    def _split_long_paragraph(self, paragraph: str) -> list[str]:
        pieces: list[str] = []
        start = 0
        while start < len(paragraph):
            end = min(start + self.max_chars, len(paragraph))
            if end < len(paragraph):
                whitespace = paragraph.rfind(" ", start, end)
                if whitespace > start + self.max_chars // 2:
                    end = whitespace
            piece = paragraph[start:end].strip()
            if piece:
                pieces.append(piece)
            start = end
            while start < len(paragraph) and paragraph[start].isspace():
                start += 1
        return pieces


@dataclass(frozen=True)
class IngestionReport:
    """Summary from one file or directory ingestion operation."""

    source_count: int
    document_count: int
    sources: tuple[str, ...]


class FileIngestor:
    """Ingest bounded UTF-8 text and Markdown files below one explicit root directory."""

    def __init__(
        self,
        store: SourceKnowledgeWriter,
        root: str | Path,
        *,
        chunker: TextChunker | None = None,
        parsers: Sequence[FileParser] | None = None,
        max_file_bytes: int = 10 * 1024 * 1024,
        max_files: int = 10_000,
        max_total_bytes: int = 1024 * 1024 * 1024,
        max_pages: int = 1000,
        max_extracted_chars: int = 10_000_000,
    ) -> None:
        for name, value in (
            ("max_file_bytes", max_file_bytes),
            ("max_files", max_files),
            ("max_total_bytes", max_total_bytes),
            ("max_pages", max_pages),
            ("max_extracted_chars", max_extracted_chars),
        ):
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{name} must be a positive integer")
            if value < 1:
                raise ValueError(f"{name} must be a positive integer")
        resolved_root = Path(root).expanduser().resolve(strict=True)
        if not resolved_root.is_dir():
            raise ValueError("root must be an existing directory")
        self.store = store
        self.root = resolved_root
        self.chunker = chunker or ParagraphChunker()
        configured_parsers = tuple(parsers) if parsers is not None else (
            Utf8TextParser(
                max_input_bytes=max_file_bytes, max_extracted_chars=max_extracted_chars
            ),
            MarkupTextParser(
                max_input_bytes=max_file_bytes, max_extracted_chars=max_extracted_chars
            ),
        )
        self.parsers: dict[str, FileParser] = {}
        for parser in configured_parsers:
            extensions = getattr(parser, "extensions", None)
            if (
                not isinstance(extensions, frozenset)
                or not extensions
                or not callable(getattr(parser, "parse", None))
                or any(
                    not isinstance(extension, str)
                    or not extension.startswith(".")
                    or extension != extension.casefold()
                    for extension in extensions
                )
            ):
                raise TypeError("parsers must expose lowercase dotted extensions and parse(bytes)")
            for extension in extensions:
                if extension in self.parsers:
                    raise ValueError(f"multiple parsers claim extension {extension!r}")
                self.parsers[extension] = parser
        self.supported_extensions = frozenset(self.parsers)
        self.max_file_bytes = max_file_bytes
        self.max_files = max_files
        self.max_total_bytes = max_total_bytes
        self.max_pages = max_pages
        self.max_extracted_chars = max_extracted_chars

    async def ingest_file(
        self, relative_path: str | Path, *, metadata: Mapping[str, Any] | None = None
    ) -> int:
        """Ingest one supported file below the configured root and return its document count."""
        count, _ = await self._ingest_file(
            relative_path,
            metadata=metadata,
            byte_limit=min(self.max_file_bytes, self.max_total_bytes),
            byte_limit_error="file exceeds configured ingestion byte limit",
        )
        return count

    async def _ingest_file(
        self,
        relative_path: str | Path,
        *,
        metadata: Mapping[str, Any] | None,
        byte_limit: int,
        byte_limit_error: str,
    ) -> tuple[int, int]:
        def resolve_supported_file() -> tuple[str, Path]:
            _, candidate = self._resolve_file(relative_path, must_exist=False)
            if candidate.suffix.casefold() not in self.parsers:
                raise ValueError(f"unsupported file extension: {candidate.suffix or '<none>'}")
            if not candidate.exists():
                raise ValueError("file path must name an existing regular file")
            return self._resolve_file(relative_path)

        source, path = await run_sync_callback(resolve_supported_file)
        file_metadata = self._validate_metadata(metadata)

        def load_documents() -> tuple[list[Document], int]:
            with path.open("rb") as stream:
                content = stream.read(byte_limit + 1)
            if len(content) > byte_limit:
                raise ValueError(byte_limit_error)
            pages = self.parsers[path.suffix.casefold()].parse(content)
            if len(pages) > self.max_pages:
                raise ValueError(f"parser returned too many pages (maximum {self.max_pages})")
            indexed: list[tuple[str, int | None, dict[str, Any]]] = []
            extracted_chars = 0
            for page in pages:
                if not isinstance(page, ParsedPage) or not isinstance(page.text, str):
                    raise ValueError("parser must return ParsedPage values with string text")
                extracted_chars += len(page.text)
                if extracted_chars > self.max_extracted_chars:
                    raise ValueError(
                        f"parser output exceeds max_extracted_chars={self.max_extracted_chars}"
                    )
                if page.page_number is not None and (
                    isinstance(page.page_number, bool)
                    or not isinstance(page.page_number, int)
                    or page.page_number < 1
                ):
                    raise ValueError("parser page numbers must be positive integers")
                page_metadata = self._validate_metadata(page.metadata)
                chunks = self.chunker.chunk(page.text)
                if any(not isinstance(chunk, str) or not chunk.strip() for chunk in chunks):
                    raise ValueError("chunker must return only non-empty strings")
                indexed.extend((chunk, page.page_number, page_metadata) for chunk in chunks)
            documents = []
            for index, (chunk, page_number, page_metadata) in enumerate(indexed):
                document_metadata = dict(page_metadata)
                document_metadata.update(file_metadata)
                document_metadata.update(chunk_index=index, chunk_count=len(indexed))
                if page_number is not None:
                    document_metadata["page_number"] = page_number
                document_id = hashlib.sha256(f"{source}\0{index}\0{chunk}".encode()).hexdigest()
                documents.append(
                    Document(text=chunk, source=source, metadata=document_metadata, id=document_id)
                )
            return documents, len(content)

        documents, byte_count = await run_sync_callback(load_documents)
        count = await self.store.replace_source(source, documents)
        return count, byte_count

    async def ingest_directory(
        self, *, metadata: Mapping[str, Any] | None = None
    ) -> IngestionReport:
        """Ingest supported files below the root and report processed sources and documents."""
        self._validate_metadata(metadata)

        def discover_files() -> list[Path]:
            files = sorted(
                (
                    path
                    for path in self.root.rglob("*")
                    if path.is_file()
                    and not path.is_symlink()
                    and path.suffix.casefold() in self.parsers
                ),
                key=lambda path: path.relative_to(self.root).as_posix(),
            )
            if len(files) > self.max_files:
                raise ValueError(f"directory exceeds max_files={self.max_files}")
            total = 0
            for path in files:
                size = path.stat().st_size
                source = path.relative_to(self.root).as_posix()
                if size > self.max_file_bytes:
                    raise ValueError(
                        f"file {source!r} exceeds max_file_bytes={self.max_file_bytes}"
                    )
                total += size
                if total > self.max_total_bytes:
                    raise ValueError(f"directory exceeds max_total_bytes={self.max_total_bytes}")
            return files

        files = await run_sync_callback(discover_files)
        sources: list[str] = []
        document_count = 0
        consumed = 0
        for path in files:
            source = path.relative_to(self.root).as_posix()
            remaining = self.max_total_bytes - consumed
            count, byte_count = await self._ingest_file(
                source,
                metadata=metadata,
                byte_limit=min(self.max_file_bytes, remaining),
                byte_limit_error=(
                    f"directory ingestion exceeds max_total_bytes={self.max_total_bytes}"
                ),
            )
            consumed += byte_count
            sources.append(source)
            document_count += count
        return IngestionReport(len(sources), document_count, tuple(sources))

    async def delete_file(self, relative_path: str | Path) -> int:
        """Delete indexed documents for a safe root-relative source path."""
        source, _ = await run_sync_callback(self._resolve_file, relative_path, must_exist=False)
        return await self.store.delete_source(source)

    def _resolve_file(
        self, relative_path: str | Path, *, must_exist: bool = True
    ) -> tuple[str, Path]:
        raw = str(relative_path)
        path = Path(relative_path)
        windows_path = PureWindowsPath(raw)
        if (
            not raw
            or "\\" in raw
            or path.is_absolute()
            or windows_path.is_absolute()
            or windows_path.drive
            or any(part in ("", ".", "..") for part in path.parts)
            or not path.parts
        ):
            raise ValueError("file path must be a safe relative path under the configured root")
        candidate = self.root.joinpath(path)
        current = self.root
        for part in path.parts:
            current = current / part
            if current.is_symlink():
                raise ValueError("file path must not traverse symbolic links")
        if not must_exist and not candidate.exists():
            return path.as_posix(), candidate
        try:
            resolved = candidate.resolve(strict=must_exist)
        except FileNotFoundError as exc:
            raise ValueError("file path must name an existing regular file") from exc
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("file path resolves outside the configured root") from exc
        if must_exist and not resolved.is_file():
            raise ValueError("file path must name a regular file")
        return path.as_posix(), resolved

    @staticmethod
    def _validate_metadata(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
        if metadata is None:
            return {}
        if not isinstance(metadata, Mapping):
            raise TypeError("metadata must be a mapping")
        if any(not isinstance(key, str) for key in metadata):
            raise TypeError("metadata keys must be strings")
        if {"chunk_index", "chunk_count", "page_number"}.intersection(metadata):
            raise ValueError("chunk_index, chunk_count, and page_number are reserved metadata keys")
        return dict(metadata)


TextFileIngestor = FileIngestor
