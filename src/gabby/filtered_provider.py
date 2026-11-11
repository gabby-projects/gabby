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
"""Model-provider decorator that filters complete and streaming payloads."""

from __future__ import annotations

import inspect
import json
from collections.abc import AsyncIterator, Sequence
from typing import Any

from .config import DEFAULT_MAX_MODEL_REQUEST_BYTES, DEFAULT_MAX_MODEL_RESPONSE_BYTES
from .models import (
    ModelRequestSizeError,
    ModelResponse,
    ModelResponseSizeError,
    ModelStreamDelta,
    ensure_model_request_size,
)
from .payload_filters import DefaultPayloadFilter, PayloadFilter


async def _apply_filters_request(
    filters: Sequence[PayloadFilter],
    *,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
    model: str,
    purpose: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    for payload_filter in filters:
        result = payload_filter.filter_request(
            messages=messages, tools=tools, model=model, purpose=purpose
        )
        if inspect.isawaitable(result):
            result = await result
        if (
            not isinstance(result, tuple)
            or len(result) != 2
            or not isinstance(result[0], list)
            or not isinstance(result[1], list)
        ):
            raise TypeError("PayloadFilter.filter_request() must return (messages, tools) lists")
        messages, tools = result
    return messages, tools


async def _apply_filters_response(
    filters: Sequence[PayloadFilter], *, response: ModelResponse, purpose: str
) -> ModelResponse:
    for payload_filter in filters:
        result = payload_filter.filter_response(response=response, purpose=purpose)
        if inspect.isawaitable(result):
            result = await result
        if not isinstance(result, ModelResponse):
            raise TypeError("PayloadFilter.filter_response() must return ModelResponse")
        response = result
    return response


class FilteredModelProvider:
    """Transparent provider wrapper that filters every request and response payload.

    Streaming calls are buffered while filters run so no text or partial tool arguments escape
    before response filters approve the complete model response.
    """

    def __init__(
        self,
        provider: Any,
        filters: Sequence[PayloadFilter],
        *,
        purpose: str,
        max_request_bytes: int = DEFAULT_MAX_MODEL_REQUEST_BYTES,
    ) -> None:
        self._provider = provider
        self._filters = tuple(filters)
        self._purpose = purpose
        self._max_request_bytes = max_request_bytes

    def __getattr__(self, name: str) -> Any:
        return getattr(self._provider, name)

    async def complete(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float | None = None,
        timeout_seconds: float = 120,
        max_response_bytes: int | None = None,
    ) -> ModelResponse:
        filtered_messages, filtered_tools = await _apply_filters_request(
            self._filters,
            messages=messages,
            tools=tools,
            model=model,
            purpose=self._purpose,
        )
        self._check_request_size(
            messages=filtered_messages,
            tools=filtered_tools,
            model=model,
            temperature=temperature,
            streaming=False,
        )
        method = self._provider.complete
        kwargs: dict[str, Any] = {
            "messages": filtered_messages,
            "tools": filtered_tools,
            "model": model,
            "temperature": temperature,
            "timeout_seconds": timeout_seconds,
        }
        if max_response_bytes is not None and _accepts_keyword(method, "max_response_bytes"):
            kwargs["max_response_bytes"] = max_response_bytes
        response = await method(**kwargs)
        if not isinstance(response, ModelResponse):
            raise TypeError("model provider returned an invalid response object")
        return await _apply_filters_response(
            self._filters, response=response, purpose=self._purpose
        )

    async def stream(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float | None = None,
        timeout_seconds: float = 120,
        max_response_bytes: int | None = None,
    ) -> AsyncIterator[ModelStreamDelta]:
        if not callable(getattr(self._provider, "stream", None)):
            response = await self.complete(
                messages=messages,
                tools=tools,
                model=model,
                temperature=temperature,
                timeout_seconds=timeout_seconds,
                max_response_bytes=max_response_bytes,
            )
            if response.content:
                yield ModelStreamDelta(content_delta=response.content)
            for index, tool_call in enumerate(response.tool_calls):
                function = tool_call.get("function", {})
                yield ModelStreamDelta(
                    tool_call_index=index,
                    tool_call_id=tool_call.get("id"),
                    tool_name_delta=function.get("name"),
                    tool_arguments_delta=function.get("arguments"),
                    provider_metadata=tool_call.get("provider_metadata"),
                )
            yield ModelStreamDelta(finish_reason="stop", usage=response.usage)
            return
        filtered_messages, filtered_tools = await _apply_filters_request(
            self._filters,
            messages=messages,
            tools=tools,
            model=model,
            purpose=self._purpose,
        )
        self._check_request_size(
            messages=filtered_messages,
            tools=filtered_tools,
            model=model,
            temperature=temperature,
            streaming=True,
        )
        method = self._provider.stream
        kwargs: dict[str, Any] = {
            "messages": filtered_messages,
            "tools": filtered_tools,
            "model": model,
            "temperature": temperature,
            "timeout_seconds": timeout_seconds,
        }
        if max_response_bytes is not None and _accepts_keyword(method, "max_response_bytes"):
            kwargs["max_response_bytes"] = max_response_bytes
        if all(
            isinstance(payload_filter, DefaultPayloadFilter) for payload_filter in self._filters
        ):
            # The default heuristic filter is safe to apply to each delta and preserves live SSE.
            # Host filters can inspect the complete response and therefore use the buffered path.
            async for delta in method(**kwargs):
                if not isinstance(delta, ModelStreamDelta):
                    raise TypeError("model provider returned a malformed stream delta")
                if delta.content_delta is not None:
                    filtered = await _apply_filters_response(
                        self._filters,
                        response=ModelResponse(content=delta.content_delta),
                        purpose=self._purpose,
                    )
                    delta = ModelStreamDelta(
                        content_delta=filtered.content or "",
                        tool_call_index=delta.tool_call_index,
                        tool_call_id=delta.tool_call_id,
                        tool_name_delta=delta.tool_name_delta,
                        tool_arguments_delta=delta.tool_arguments_delta,
                        finish_reason=delta.finish_reason,
                        usage=delta.usage,
                        provider_metadata=delta.provider_metadata,
                    )
                yield delta
            return

        deltas: list[ModelStreamDelta] = []
        response_limit = max_response_bytes or DEFAULT_MAX_MODEL_RESPONSE_BYTES
        used_bytes = 0
        async for delta in method(**kwargs):
            if not isinstance(delta, ModelStreamDelta):
                raise TypeError("model provider returned a malformed stream delta")
            delta_payload = {
                "content_delta": delta.content_delta,
                "tool_call_index": delta.tool_call_index,
                "tool_call_id": delta.tool_call_id,
                "tool_name_delta": delta.tool_name_delta,
                "tool_arguments_delta": delta.tool_arguments_delta,
                "finish_reason": delta.finish_reason,
                "usage": delta.usage,
                "provider_metadata": delta.provider_metadata,
            }
            try:
                used_bytes += len(
                    json.dumps(
                        delta_payload,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                    ).encode("utf-8")
                )
            except (TypeError, ValueError, UnicodeError):
                raise TypeError("model provider returned malformed stream metadata") from None
            if used_bytes > response_limit:
                raise ModelResponseSizeError(
                    f"Model response exceeded max_model_response_bytes={response_limit}"
                )
            deltas.append(delta)
        response = await _apply_filters_response(
            self._filters, response=_response_from_deltas(deltas), purpose=self._purpose
        )
        if response.content:
            yield ModelStreamDelta(content_delta=response.content)
        for index, tool_call in enumerate(response.tool_calls):
            function = tool_call.get("function", {})
            yield ModelStreamDelta(
                tool_call_index=index,
                tool_call_id=tool_call.get("id"),
                tool_name_delta=function.get("name"),
                tool_arguments_delta=function.get("arguments"),
                provider_metadata=tool_call.get("provider_metadata"),
            )
        last = deltas[-1] if deltas else None
        yield ModelStreamDelta(
            finish_reason=(last.finish_reason if last is not None else "stop"),
            usage=(last.usage if last is not None else None),
            provider_metadata=(last.provider_metadata if last is not None else None),
        )

    async def aclose(self) -> None:
        close = getattr(self._provider, "aclose", None)
        if callable(close):
            result = close()
            if inspect.isawaitable(result):
                await result

    def close(self) -> None:
        close = getattr(self._provider, "close", None)
        if callable(close):
            close()

    def _check_request_size(
        self,
        *,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        model: str,
        temperature: float | None,
        streaming: bool,
    ) -> None:
        try:
            ensure_model_request_size(
                messages=messages,
                tools=tools,
                model=model,
                temperature=temperature,
                max_bytes=self._max_request_bytes,
                streaming=streaming,
                supports_tool_choice=bool(getattr(self._provider, "supports_tool_choice", True)),
            )
        except ModelRequestSizeError as exc:
            raise ValueError(
                f"Filtered model request exceeds configured size limit: {exc}"
            ) from exc


def _accepts_keyword(method: Any, name: str) -> bool:
    try:
        parameters = inspect.signature(method).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(parameter.name == name for parameter in parameters)


def _response_from_deltas(deltas: list[ModelStreamDelta]) -> ModelResponse:
    content: list[str] = []
    calls: dict[int, dict[str, Any]] = {}
    finish_reason: str | None = None
    usage: dict[str, Any] = {}
    for delta in deltas:
        if delta.content_delta:
            content.append(delta.content_delta)
        if delta.tool_call_index is not None:
            call = calls.setdefault(
                delta.tool_call_index,
                {"id": None, "type": "function", "function": {"name": "", "arguments": ""}},
            )
            if delta.tool_call_id:
                call["id"] = delta.tool_call_id
            if delta.tool_name_delta:
                call["function"]["name"] += delta.tool_name_delta
            if delta.tool_arguments_delta:
                call["function"]["arguments"] += delta.tool_arguments_delta
            if delta.provider_metadata:
                call.setdefault("provider_metadata", {}).update(delta.provider_metadata)
        if delta.finish_reason is not None:
            finish_reason = delta.finish_reason
        if delta.usage is not None:
            usage = delta.usage
    return ModelResponse(
        content="".join(content) or None,
        tool_calls=[calls[index] for index in sorted(calls)],
        usage=usage,
        raw={"finish_reason": finish_reason} if finish_reason is not None else {},
    )
