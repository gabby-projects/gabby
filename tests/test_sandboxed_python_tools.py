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

"""Importable Python handlers execute through the existing run sandbox."""

import pytest

from gabby.python_tools import sandboxed_python_tool


def test_sandboxed_python_tool_uses_fixed_image_handler_reference() -> None:
    tool = sandboxed_python_tool(
        name="tax_calculator",
        handler="billing.tools:calculate_tax",
        parameters={
            "type": "object",
            "properties": {"amount": {"type": "number"}},
            "required": ["amount"],
            "additionalProperties": False,
        },
        output_schema={"type": "object"},
        description="Calculate tax using the configured billing rules.",
    )

    assert tool.execution == "sandboxed"
    assert tool.sandbox_action == "tool.execute"
    assert tool.sandbox_command == (
        "python3",
        "-I",
        "-m",
        "gabby.tool_worker",
        "billing.tools:calculate_tax",
    )
    assert tool.handler is None


def test_sandboxed_python_tool_rejects_local_functions() -> None:
    def local_handler(value: str) -> dict[str, str]:
        return {"value": value}

    with pytest.raises(ValueError, match="top-level importable"):
        sandboxed_python_tool(
            name="local",
            handler=local_handler,
            parameters={"type": "object"},
            output_schema={"type": "object"},
            description="Local handler",
        )
