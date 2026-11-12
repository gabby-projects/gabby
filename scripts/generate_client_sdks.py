#!/usr/bin/env python3
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

"""Generate the checked-in lightweight SDK packages from their repository templates."""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "sdks" / "templates"


def main() -> None:
    for language in ("typescript", "go", "rust"):
        source = TEMPLATES / language
        destination = ROOT / "sdks" / language
        if not source.is_dir():
            raise SystemExit(f"Missing SDK template directory: {source}")
        if destination.exists():
            shutil.rmtree(destination)
        shutil.copytree(source, destination)
    print("Generated TypeScript, Go, and Rust clients from sdks/templates.")


if __name__ == "__main__":
    main()
