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

from __future__ import annotations

from pathlib import Path

import pytest

from gabby import (
    Document,
    FileIngestor,
    MarkupTextParser,
    ParsedPage,
    TextFileIngestor,
    Utf8TextParser,
)


class MemoryStore:
    def __init__(self) -> None:
        self.sources: dict[str, list[Document]] = {}

    async def replace_source(self, source: str, documents: list[Document]) -> int:
        self.sources[source] = documents
        return len(documents)

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


def test_only_plain_text_and_markdown_are_default_ingestion_formats(tmp_path: Path) -> None:
    ingestor = FileIngestor(MemoryStore(), tmp_path)  # type: ignore[arg-type]
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
    ingestor = FileIngestor(store, tmp_path)  # type: ignore[arg-type]
    report = await ingestor.ingest_directory(metadata={"tenant": "demo"})
    assert report.source_count == 2
    assert report.sources == ("guide.md", "notes.txt")
    assert store.sources["guide.md"][0].text == "# Guide\n\nUse bounded policies."
    assert store.sources["guide.md"][0].metadata["tenant"] == "demo"


@pytest.mark.asyncio
async def test_ingest_rejects_unsupported_format_and_unsafe_paths(tmp_path: Path) -> None:
    (tmp_path / "data.json").write_text('{"a": 1}', encoding="utf-8")
    ingestor = FileIngestor(MemoryStore(), tmp_path)  # type: ignore[arg-type]
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
    ingestor = FileIngestor(store, tmp_path, parsers=(HostParser(),))  # type: ignore[arg-type]
    await ingestor.ingest_file("input.custom")
    assert store.sources["input.custom"][0].text == "HOST-OWNED EXTRACTION"
