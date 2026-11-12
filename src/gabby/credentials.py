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

"""Host-provided, run-scoped credentials for sandboxed tool processes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from .auth import Principal


class ScopedCredentialProvider(Protocol):
    """Resolve short-lived environment credentials for one authorized sandbox tool call."""

    async def resolve(
        self, *, tool_name: str, principal: Principal | None, run_id: str
    ) -> Mapping[str, str]:
        """Return credentials valid only for this tool invocation; never log the values."""
        ...
