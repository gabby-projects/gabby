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
"""Validation and bounds for the host context API contract."""

import pytest
from pydantic import ValidationError

from gabby.host_context import HostContext


def test_host_context_accepts_documented_typed_values() -> None:
    value = HostContext.model_validate(
        {
            "user_preferences": {
                "locale": "en-AU",
                "custom": {"compact": True, "reading_level": 7, "cohort": None},
            },
            "session_summary": {
                "summary": "The user is setting up the service.",
                "recent_topics": ["timeouts"],
            },
            "rag_snippets": [
                {"text": "Timeouts limit request duration.", "source": "guide.md", "score": 0.9}
            ],
        }
    )

    assert value.user_preferences is not None
    assert value.user_preferences.locale == "en-AU"
    assert value.rag_snippets[0].source == "guide.md"


@pytest.mark.parametrize(
    "value",
    [
        {"unknown": "rejected"},
        {"user_preferences": {"custom": {"nested": {"unsafe": True}}}},
        {"rag_snippets": [{"text": "No source attribution"}]},
        {"rag_snippets": [{"text": "bad score", "source": "x", "score": float("nan")}]},
    ],
)
def test_host_context_rejects_unknown_or_invalid_values(value: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        HostContext.model_validate(value)


def test_host_context_enforces_collection_bounds() -> None:
    with pytest.raises(ValidationError):
        HostContext.model_validate(
            {"rag_snippets": [{"text": "snippet", "source": "guide.md"}] * 65}
        )
