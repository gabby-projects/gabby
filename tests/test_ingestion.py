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
#
# Copyright 2026-present Gabby Contributors.

from __future__ import annotations

from collections.abc import Iterator, Sequence
from pathlib import Path

import pytest

from gabby import (
    Document,
    FileIngestor,
    MarkupTextParser,
    ParagraphChunker,
    ParsedPage,
    SQLiteFTS5Store,
    TextFileIngestor,
    Utf8TextParser,
)


class MemoryStore:
    def __init__(self) -> None:
        self.sources: dict[str, list[Document]] = {}

    async def replace_source(self, source: str, documents: Sequence[Document]) -> int:
        self.sources[source] = list(documents)
        return len(self.sources[source])

    async def delete_source(self, source: str) -> int:
        return len(self.sources.pop(source, []))


def test_utf8_text_parser_is_bounded_and_rejects_invalid_text() -> None:
    parser = Utf8TextParser(max_input_bytes=32, max_extracted_chars=8)
    assert parser.parse(b"\xef\xbb\xbfhello")[0].text == "hello"
    with pytest.raises(ValueError, match="valid UTF-8"):
        parser.parse(b"\xff")
    with pytest.raises(ValueError, match="NUL"):
        parser.parse(b"a\x00b")
    with pytest.raises(ValueError, match="max_extracted_chars"):
        parser.parse(b"0123456789")
    with pytest.raises(ValueError, match="max_input_bytes"):
        Utf8TextParser(max_input_bytes=2).parse(b"long")


def test_markdown_parser_preserves_source_as_text() -> None:
    assert MarkupTextParser().parse(b"# Heading\n\n**body**")[0] == ParsedPage(
        "# Heading\n\n**body**"
    )


def test_paragraph_chunking_is_deterministic_and_bounded() -> None:
    chunker = ParagraphChunker(max_chars=10, overlap_chars=0)
    text = "alpha\n\nbeta gamma\n\n" + "x" * 25

    first = chunker.chunk(text)

    assert first == chunker.chunk(text)
    assert first
    assert all(0 < len(chunk) <= 10 for chunk in first)


def test_only_plain_text_and_markdown_are_default_ingestion_formats(tmp_path: Path) -> None:
    ingestor = FileIngestor(MemoryStore(), tmp_path)
    assert ingestor.supported_extensions == {".txt", ".log", ".md", ".markdown"}
    assert TextFileIngestor is FileIngestor


@pytest.mark.asyncio
async def test_ingest_directory_indexes_text_and_markdown_with_source_metadata(
    tmp_path: Path,
) -> None:
    (tmp_path / "guide.md").write_text("# Guide\n\nUse bounded policies.", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("Plain text notes.", encoding="utf-8")
    (tmp_path / "ignored.pdf").write_bytes(b"not parsed")
    store = MemoryStore()
    ingestor = FileIngestor(store, tmp_path)
    report = await ingestor.ingest_directory(metadata={"tenant": "demo"})
    assert report.source_count == 2
    assert report.sources == ("guide.md", "notes.txt")
    assert store.sources["guide.md"][0].text == "# Guide\n\nUse bounded policies."
    assert store.sources["guide.md"][0].metadata["tenant"] == "demo"


@pytest.mark.asyncio
async def test_ingest_directory_enforces_file_count_during_discovery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")
    store = MemoryStore()
    ingestor = FileIngestor(store, tmp_path, max_files=1)
    original_rglob = Path.rglob

    def limited_rglob(root: Path, pattern: str) -> Iterator[Path]:
        if root != ingestor.root:
            yield from original_rglob(root, pattern)
            return
        yield first
        yield second
        raise AssertionError("discovery should stop as soon as the file limit is exceeded")

    monkeypatch.setattr(Path, "rglob", limited_rglob)

    with pytest.raises(ValueError, match="max_files=1"):
        await ingestor.ingest_directory()
    assert store.sources == {}


@pytest.mark.asyncio
async def test_ingest_directory_checks_total_size_before_indexing_any_source(
    tmp_path: Path,
) -> None:
    (tmp_path / "one.txt").write_text("one", encoding="utf-8")
    (tmp_path / "two.txt").write_text("two", encoding="utf-8")
    store = MemoryStore()
    ingestor = FileIngestor(
        store,
        tmp_path,
        max_file_bytes=8,
        max_total_bytes=5,
    )

    with pytest.raises(ValueError, match="max_total_bytes=5"):
        await ingestor.ingest_directory()
    assert store.sources == {}


@pytest.mark.asyncio
async def test_ingest_file_rejects_oversized_text_before_store_write(tmp_path: Path) -> None:
    (tmp_path / "large.txt").write_text("larger than limit", encoding="utf-8")
    store = MemoryStore()
    ingestor = FileIngestor(store, tmp_path, max_file_bytes=4)

    with pytest.raises(ValueError, match="max_input_bytes=4|configured ingestion byte limit"):
        await ingestor.ingest_file("large.txt")
    assert store.sources == {}


@pytest.mark.asyncio
async def test_ingestion_skips_symlinked_sources_and_rejects_direct_symlink_access(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("private outside text", encoding="utf-8")
    link = root / "linked.txt"
    try:
        link.symlink_to(outside)
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    store = MemoryStore()
    ingestor = FileIngestor(store, root)
    report = await ingestor.ingest_directory()

    assert report.sources == ()
    with pytest.raises(ValueError, match="symbolic links"):
        await ingestor.ingest_file("linked.txt")
    assert store.sources == {}


@pytest.mark.asyncio
async def test_ingest_replaces_source_documents_in_sqlite(tmp_path: Path) -> None:
    source = tmp_path / "guide.txt"
    database = tmp_path / "knowledge.db"
    source.write_text("legacy authentication guidance", encoding="utf-8")
    store = SQLiteFTS5Store(database)
    ingestor = FileIngestor(store, tmp_path)

    assert await ingestor.ingest_file("guide.txt") == 1
    assert await store.retrieve("legacy authentication")

    source.write_text("current authorization guidance", encoding="utf-8")
    assert await ingestor.ingest_file("guide.txt") == 1

    assert await store.retrieve("legacy authentication") == []
    assert [document.text for document in await store.retrieve("current authorization")] == [
        "current authorization guidance"
    ]


@pytest.mark.asyncio
async def test_ingest_rejects_unsupported_format_and_unsafe_paths(tmp_path: Path) -> None:
    (tmp_path / "data.json").write_text('{"a": 1}', encoding="utf-8")
    ingestor = FileIngestor(MemoryStore(), tmp_path)
    with pytest.raises(ValueError, match="unsupported file extension"):
        await ingestor.ingest_file("data.json")
    with pytest.raises(ValueError, match="safe relative path"):
        await ingestor.ingest_file("../outside.txt")


@pytest.mark.asyncio
async def test_custom_host_parser_remains_replaceable(tmp_path: Path) -> None:
    class HostParser:
        extensions = frozenset({".custom"})

        def parse(self, content: bytes) -> tuple[ParsedPage, ...]:
            return (ParsedPage(content.decode("utf-8").upper()),)

    (tmp_path / "input.custom").write_text("host-owned extraction", encoding="utf-8")
    store = MemoryStore()
    ingestor = FileIngestor(store, tmp_path, parsers=(HostParser(),))
    await ingestor.ingest_file("input.custom")
    assert store.sources["input.custom"][0].text == "HOST-OWNED EXTRACTION"
