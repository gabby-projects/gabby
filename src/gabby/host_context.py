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
"""Typed, bounded per-request personalization context supplied by the host."""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StrictBool, StrictInt, StrictStr

_Scalar = StrictStr | StrictInt | StrictBool | FiniteFloat | None


class _HostContextModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class HostUserPreferences(_HostContextModel):
    """Caller preferences that the host has authenticated and selected."""

    display_name: Annotated[str, Field(max_length=128)] | None = None
    locale: Annotated[str, Field(max_length=64)] | None = None
    timezone: Annotated[str, Field(max_length=128)] | None = None
    response_style: Annotated[str, Field(max_length=2048)] | None = None
    accessibility_needs: list[Annotated[str, Field(max_length=512)]] = Field(
        default_factory=list, max_length=20
    )
    custom: dict[str, _Scalar] = Field(default_factory=dict, max_length=32)


class HostSessionSummary(_HostContextModel):
    """Host-owned summary of prior turns, scoped to the current request."""

    summary: Annotated[str, Field(min_length=1, max_length=8192)]
    updated_at: Annotated[str, Field(max_length=64)] | None = None
    recent_topics: list[Annotated[str, Field(max_length=256)]] = Field(
        default_factory=list, max_length=32
    )


class HostRAGSnippet(_HostContextModel):
    """One bounded, untrusted text snippet retrieved for the current caller."""

    text: Annotated[str, Field(min_length=1, max_length=32768)]
    source: Annotated[str, Field(min_length=1, max_length=1024)]
    title: Annotated[str, Field(max_length=256)] | None = None
    score: FiniteFloat | None = None
    metadata: dict[str, _Scalar] = Field(default_factory=dict, max_length=32)


class HostContext(_HostContextModel):
    """Typed, request-local personalization and retrieval context."""

    user_preferences: HostUserPreferences | None = None
    session_summary: HostSessionSummary | None = None
    rag_snippets: list[HostRAGSnippet] = Field(default_factory=list, max_length=64)
