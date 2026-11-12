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

"""Sandboxed Python execution tool for data-oriented agents."""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from typing import Any

from .tools import Tool

_MAX_CODE_BYTES = 1024 * 1024
_HANDLER_REFERENCE = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*:[A-Za-z_][A-Za-z0-9_]*\Z")


def sandboxed_python_tool(
    *,
    name: str,
    handler: str | Callable[..., Any],
    parameters: dict[str, Any],
    output_schema: dict[str, Any],
    description: str,
    executable: str = "python3",
    max_input_bytes: int = 256 * 1024,
    max_result_bytes: int = 1024 * 1024,
    timeout_seconds: float = 30,
) -> Tool:
    """Register an importable Python handler that executes inside the per-run sandbox.

    The handler must be importable from the configured sandbox image. Pass a ``module:function``
    reference or a top-level Python function; closures and local functions are rejected. The host
    never executes the handler in its own process. The image must include both Gabby and the
    handler's package.
    """
    if isinstance(handler, str):
        reference = handler
    elif callable(handler):
        module = getattr(handler, "__module__", "")
        qualified_name = getattr(handler, "__qualname__", "")
        if "." in qualified_name or "<locals>" in qualified_name:
            raise ValueError("handler must be a top-level importable Python function")
        reference = f"{module}:{qualified_name}"
    else:
        raise TypeError("handler must be a module:function reference or importable function")
    if _HANDLER_REFERENCE.fullmatch(reference) is None:
        raise ValueError("handler must use module:function syntax")
    if not isinstance(executable, str) or not executable or "\x00" in executable:
        raise ValueError("executable must be a non-empty interpreter command")
    for key, value, maximum in (
        ("max_input_bytes", max_input_bytes, 1024 * 1024),
        ("max_result_bytes", max_result_bytes, 1024 * 1024),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
            raise ValueError(f"{key} must be from 1 through {maximum}")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or not 0.01 <= timeout_seconds <= 3600
    ):
        raise ValueError("timeout_seconds must be finite and between 0.01 and 3600 seconds")
    return Tool(
        name=name,
        description=description,
        parameters=parameters,
        output_schema=output_schema,
        timeout_seconds=float(timeout_seconds),
        max_input_bytes=max_input_bytes,
        max_result_bytes=max_result_bytes,
        permissions=("sandbox:python-handler",),
        sandbox_action="tool.execute",
        execution="sandboxed",
        sandbox_command=(executable, "-I", "-m", "gabby.tool_worker", reference),
    )


def python_run_tool(
    *,
    executable: str = "python3",
    name: str = "python_run",
    description: str = "Run Python code in the configured per-run sandbox.",
    max_code_bytes: int = 256 * 1024,
    max_result_bytes: int = 1024 * 1024,
    timeout_seconds: float = 30,
) -> Tool:
    """Create a Python tool whose source and process execute inside the agent container.

    The selected sandbox image must contain the configured interpreter. Gabby stages each source
    file in the sandbox's private, read-only tool-input mount, runs it with Python isolated mode,
    and removes the staged source after execution. The container's workspace, network, deadline,
    CPU, memory, and process policies remain in force.
    """
    if not isinstance(executable, str) or not executable or "\x00" in executable:
        raise ValueError("executable must be a non-empty interpreter command")
    for key, value, maximum in (
        ("max_code_bytes", max_code_bytes, _MAX_CODE_BYTES),
        ("max_result_bytes", max_result_bytes, 1024 * 1024),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{key} must be a positive integer")
        if not 1 <= value <= maximum:
            raise ValueError(f"{key} must be from 1 through {maximum}")
    if (
        isinstance(timeout_seconds, bool)
        or not isinstance(timeout_seconds, (int, float))
        or not math.isfinite(timeout_seconds)
        or not 0.01 <= timeout_seconds <= 3600
    ):
        raise ValueError("timeout_seconds must be finite and between 0.01 and 3600 seconds")

    return Tool(
        name=name,
        description=description,
        parameters={
            "type": "object",
            "properties": {"code": {"type": "string", "minLength": 1}},
            "required": ["code"],
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {
                "exit_code": {"type": "integer"},
                "stdout": {"type": "string"},
                "stderr": {"type": "string"},
            },
            "required": ["exit_code", "stdout", "stderr"],
            "additionalProperties": False,
        },
        timeout_seconds=float(timeout_seconds),
        max_input_bytes=max_code_bytes,
        max_result_bytes=max_result_bytes,
        permissions=("sandbox:python",),
        sandbox_action="python.run",
        execution="sandboxed",
        sandbox_command=(executable,),
    )
