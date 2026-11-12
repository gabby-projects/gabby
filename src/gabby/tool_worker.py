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

"""Sandbox image entry point for importable Python tool handlers."""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast


def _load_handler(reference: str) -> Callable[..., Any]:
    module_name, separator, attribute = reference.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError("handler reference must use module:function syntax")
    handler = getattr(importlib.import_module(module_name), attribute)
    if not callable(handler):
        raise TypeError("configured handler is not callable")
    return cast(Callable[..., Any], handler)


async def _invoke(handler: Callable[..., Any], arguments: dict[str, Any]) -> Any:
    result = handler(**arguments)
    if hasattr(result, "__await__"):
        return await result
    return result


def main(argv: list[str] | None = None) -> int:
    """Read one Gabby tool payload and return exactly one JSON result."""
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 2:
        return 2
    reference, request_path = args
    try:
        request = json.loads(Path(request_path).read_text(encoding="utf-8"))
        if not isinstance(request, dict):
            raise ValueError("tool arguments must be an object")
        # Imports can execute module-level code that writes to stdout. Keep both import and
        # handler diagnostics away from the one-line JSON worker protocol.
        with contextlib.redirect_stdout(sys.stderr):
            handler = _load_handler(reference)
            result = asyncio.run(_invoke(handler, request))
        response = json.dumps(result, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    except Exception:
        print("Sandboxed Python tool failed", file=sys.stderr)
        return 1
    print(response)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
