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
"""Thin HTTP client adapters for orchestration frameworks."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .client import GabbyClient


def langgraph_node(
    client: GabbyClient,
    *,
    input_key: str = "input",
    output_key: str = "gabby_output",
    context_key: str | None = None,
) -> Any:
    """Create an async LangGraph node that adds Gabby's result to graph state."""

    async def node(state: Mapping[str, Any]) -> dict[str, Any]:
        task = state.get(input_key)
        if not isinstance(task, str) or not task.strip():
            raise ValueError(f"LangGraph state[{input_key!r}] must be non-empty text")
        context = state.get(context_key) if context_key else None
        if context is not None and not isinstance(context, Mapping):
            raise ValueError(f"LangGraph state[{context_key!r}] must be a mapping")
        result = await client.arun(task, context=context)
        return {output_key: result.output, "gabby_trace_id": result.trace_id}

    return node


def crewai_tool(
    client: GabbyClient,
    *,
    name: str = "gabby_governed_task",
    description: str = "Run a task through Gabby's governed agent runtime",
) -> Any:
    """Build an optional CrewAI ``BaseTool`` around the Gabby HTTP client."""
    try:
        from crewai.tools import BaseTool
        from pydantic import BaseModel, Field
    except ImportError as exc:
        raise RuntimeError("CrewAI adapter requires the optional 'crewai' package") from exc

    class TaskInput(BaseModel):
        task: str = Field(description="Task to execute through Gabby")

    sync_client = client.clone()
    async_client = client.clone()

    class GabbyCrewTool(BaseTool):  # type: ignore[misc]
        name: str = name
        description: str = description
        args_schema: type[BaseModel] = TaskInput

        def _run(self, task: str) -> str:
            return sync_client.run(task).output

        async def _arun(self, task: str) -> str:
            return (await async_client.arun(task)).output

    return GabbyCrewTool()


def n8n_request(
    client: GabbyClient,
    task: str,
    *,
    stream: bool = False,
) -> Any:
    """Invoke Gabby from an n8n Python Code node or workflow integration.

    For JavaScript n8n workflows, use an HTTP Request node targeting the same ``/run`` or
    ``/stream`` endpoint. The helper is intended for Python-based n8n task runners.
    """
    if stream:
        return client.stream(task)
    return client.run(task)
