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

"""Check ordered Apache license headers on files that support comments."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {
    ".git",
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "build",
    "dist",
    "target",
    "__pycache__",
}
HASH_SUFFIXES = {
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".toml",
    ".yaml",
    ".yml",
    ".lock",
    ".conf",
    ".ini",
    ".cfg",
    ".gitignore",
    ".dockerignore",
    ".editorconfig",
    ".txt",
}
SLASH_SUFFIXES = {
    ".go",
    ".mod",
    ".rs",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".java",
    ".c",
    ".h",
}
SUPPORTED_NAMES = {"Dockerfile", "CODEOWNERS"}
HASH_NAMES = {".gitignore", ".dockerignore", ".editorconfig"}
COPYRIGHT = "Copyright 2026-present Gabby Contributors."
LICENSE_TEXT = (
    'Licensed under the Apache License, Version 2.0 (the "License");',
    "you may not use this file except in compliance with the License.",
    "You may obtain a copy of the License at",
    "",
    "     https://www.apache.org/licenses/LICENSE-2.0",
    "",
    "Unless required by applicable law or agreed to in writing, software",
    'distributed under the License is distributed on an "AS IS" BASIS,',
    "WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.",
    "See the License for the specific language governing permissions and",
    "limitations under the License.",
)
NON_COMMENTABLE_EXCEPTIONS = (
    "LICENSE contains the license text and does not receive a recursive header",
    "JSON and tsconfig files do not support comments",
    "src/gabby/py.typed must remain empty for PEP 561",
    ".python-version accepts a version value, not a comment header",
    "Task.txt is an external audit checklist and is deliberately excluded",
)


def header_for(path: Path) -> tuple[list[str], str] | None:
    """Return the exact comment block and syntax marker for one supported file."""
    if path.suffix == ".md":
        return ["<!--", *LICENSE_TEXT, "", COPYRIGHT, "-->"], "html"
    if path.name in SUPPORTED_NAMES | HASH_NAMES or path.suffix in HASH_SUFFIXES:
        marker = "#"
    elif path.suffix in SLASH_SUFFIXES:
        marker = "//"
    elif path.suffix == ".sql":
        marker = "--"
    else:
        return None
    return [
        *(f"{marker} {line}" if line else marker for line in LICENSE_TEXT),
        marker,
        f"{marker} {COPYRIGHT}",
    ], marker


def eligible_paths() -> list[Path]:
    """Find maintainable source, documentation, and configuration files."""
    result: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED_DIRS or part.endswith(".egg-info") for part in relative.parts):
            continue
        if relative.as_posix() in {
            "LICENSE",
            "Task.txt",
            ".python-version",
            "src/gabby/py.typed",
        }:
            continue
        if header_for(path) is not None:
            result.append(path)
    return sorted(result)


def content_start(lines: list[str], path: Path) -> int:
    """Skip interpreter and encoding directives that must precede a Python header."""
    if path.suffix != ".py":
        return 0
    start = 1 if lines and lines[0].startswith("#!") else 0
    for index, line in enumerate(lines[:2]):
        if re.match(r"#.*coding[:=]\s*[-\w.]+", line):
            start = max(start, index + 1)
    return start


def validate(path: Path) -> str | None:
    expected = header_for(path)
    assert expected is not None
    expected_lines, style = expected
    lines = path.read_text(encoding="utf-8").splitlines()
    start = content_start(lines, path)
    actual = lines[start : start + len(expected_lines)]
    if actual != expected_lines:
        return "header missing, malformed, or not in the requested Apache-then-copyright order"
    separator = start + len(expected_lines)
    if separator >= len(lines) or lines[separator] != "":
        return "header must be followed by one blank line"
    if style != "html" and expected_lines[-2].strip() != style:
        return "header must include an empty comment line between license and copyright"
    return None


def main() -> int:
    failures: list[tuple[Path, str]] = []
    for path in eligible_paths():
        error = validate(path)
        if error is not None:
            failures.append((path, error))
    if failures:
        for path, error in failures:
            print(f"{path.relative_to(ROOT)}: {error}")
        return 1
    print(f"All {len(eligible_paths())} commentable project files have ordered Apache-2.0 headers.")
    for exception in NON_COMMENTABLE_EXCEPTIONS:
        print(f"Excluded by file-format contract: {exception}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
