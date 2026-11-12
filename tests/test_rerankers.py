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

"""Configuration and bounded HTTP contracts for reranking providers."""

from __future__ import annotations

import json
import traceback
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from gabby import (
    CohereReranker,
    Document,
    JinaReranker,
    NvidiaReranker,
    RerankingError,
    RerankingResponseSizeError,
    RerankingRetriever,
    VoyageReranker,
)

_ASYNC_CLIENT = httpx.AsyncClient


class _Chunks(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self) -> AsyncIterator[bytes]:
        for chunk in self.chunks:
            yield chunk

    async def aclose(self) -> None:
        return None


def _reranker(handler: Any, monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> CohereReranker:
    transport = httpx.MockTransport(handler)

    def make_client(**client_kwargs: Any) -> httpx.AsyncClient:
        return _ASYNC_CLIENT(transport=transport, **client_kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", make_client)
    return CohereReranker(**kwargs)


def _jina_reranker(handler: Any, monkeypatch: pytest.MonkeyPatch, **kwargs: Any) -> JinaReranker:
    transport = httpx.MockTransport(handler)

    def make_client(**client_kwargs: Any) -> httpx.AsyncClient:
        return _ASYNC_CLIENT(transport=transport, **client_kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", make_client)
    return JinaReranker(**kwargs)


def _voyage_reranker(
    handler: Any, monkeypatch: pytest.MonkeyPatch, **kwargs: Any
) -> VoyageReranker:
    transport = httpx.MockTransport(handler)

    def make_client(**client_kwargs: Any) -> httpx.AsyncClient:
        return _ASYNC_CLIENT(transport=transport, **client_kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", make_client)
    return VoyageReranker(**kwargs)


def _nvidia_reranker(
    handler: Any, monkeypatch: pytest.MonkeyPatch, **kwargs: Any
) -> NvidiaReranker:
    transport = httpx.MockTransport(handler)

    def make_client(**client_kwargs: Any) -> httpx.AsyncClient:
        return _ASYNC_CLIENT(transport=transport, **client_kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", make_client)
    return NvidiaReranker(**kwargs)


async def test_cohere_reranker_sends_bounded_text_and_maps_ordered_indexes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 1, "relevance_score": 0.97},
                    {"index": 0, "relevance_score": 0.42},
                ]
            },
        )

    docs = [
        Document("Account recovery instructions", source="support.md", id="account"),
        Document(
            "Password reset steps", source="private.md", metadata={"secret": "local"}, id="reset"
        ),
    ]
    monkeypatch.setenv("COHERE_API_KEY", "cohere-test-token")
    reranker = _reranker(respond, monkeypatch)
    try:
        result = await reranker.rerank("reset my password", docs, limit=10)
    finally:
        await reranker.aclose()

    assert [document.id for document in result] == ["reset", "account"]
    assert result[0] is docs[1]
    assert requests[0].url == "https://api.cohere.com/v2/rerank"
    assert requests[0].headers["authorization"] == "Bearer cohere-test-token"
    payload = json.loads(requests[0].content)
    assert payload == {
        "model": "rerank-v4.0-fast",
        "query": "reset my password",
        "documents": ["Account recovery instructions", "Password reset steps"],
        "top_n": 2,
        "max_tokens_per_doc": 4096,
    }
    assert "private.md" not in requests[0].content.decode()
    assert docs[1].metadata == {"secret": "local"}


@pytest.mark.asyncio
async def test_jina_reranker_sends_bounded_text_and_maps_ordered_indexes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 1, "relevance_score": 0.97},
                    {"index": 0, "relevance_score": 0.42},
                ]
            },
        )

    docs = [
        Document("Account recovery instructions", source="support.md", id="account"),
        Document("Password reset steps", source="private.md", id="reset"),
    ]
    monkeypatch.setenv("JINA_API_KEY", "jina-test-token")
    reranker = _jina_reranker(respond, monkeypatch)
    try:
        result = await reranker.rerank("reset my password", docs, limit=10)
    finally:
        await reranker.aclose()

    assert [document.id for document in result] == ["reset", "account"]
    assert result[0] is docs[1]
    assert requests[0].url == "https://api.jina.ai/v1/rerank"
    assert requests[0].headers["authorization"] == "Bearer jina-test-token"
    payload = json.loads(requests[0].content)
    assert payload == {
        "model": "jina-reranker-v3.5",
        "query": "reset my password",
        "documents": ["Account recovery instructions", "Password reset steps"],
        "top_n": 2,
        "return_documents": False,
    }
    assert "private.md" not in requests[0].content.decode()


@pytest.mark.asyncio
async def test_voyage_reranker_sends_bounded_text_and_maps_ordered_indexes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {"index": 1, "relevance_score": 0.97},
                    {"index": 0, "relevance_score": 0.42},
                ]
            },
        )

    docs = [
        Document("Account recovery instructions", source="support.md", id="account"),
        Document("Password reset steps", source="private.md", id="reset"),
    ]
    monkeypatch.setenv("VOYAGE_API_KEY", "voyage-test-token")
    reranker = _voyage_reranker(respond, monkeypatch)
    try:
        result = await reranker.rerank("reset my password", docs, limit=10)
    finally:
        await reranker.aclose()

    assert [document.id for document in result] == ["reset", "account"]
    assert result[0] is docs[1]
    assert requests[0].url == "https://api.voyageai.com/v1/rerank"
    assert requests[0].headers["authorization"] == "Bearer voyage-test-token"
    assert json.loads(requests[0].content) == {
        "model": "rerank-2.5-lite",
        "query": "reset my password",
        "documents": ["Account recovery instructions", "Password reset steps"],
        "top_k": 2,
        "return_documents": False,
        "truncation": False,
    }
    assert "private.md" not in requests[0].content.decode()


def test_voyage_reranker_configuration_and_inline_credentials() -> None:
    with pytest.raises(ValueError, match="requires HTTPS"):
        VoyageReranker(base_url="http://remote.example/v1")
    with pytest.raises(ValueError, match="model.api_key"):
        VoyageReranker.from_config({"api_key": "secret"})
    with pytest.raises(ValueError, match="truncation must be a boolean"):
        VoyageReranker(truncation="yes")  # type: ignore[arg-type]

    reranker = VoyageReranker.from_config({"model": "rerank-2.5"})
    assert reranker.model == "rerank-2.5"
    assert reranker.api_key_env == "VOYAGE_API_KEY"
    assert reranker.truncation is False


@pytest.mark.asyncio
async def test_voyage_reranker_bounds_requests_responses_and_sanitizes_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VOYAGE_API_KEY", "token")
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, stream=_Chunks([b'{"results":', b"[]}"]))

    reranker = _voyage_reranker(respond, monkeypatch, max_request_bytes=200, max_response_bytes=12)
    try:
        with pytest.raises(RerankingError, match="max_request_bytes=200"):
            await reranker.rerank("query", [Document("x" * 200)], limit=1)
        with pytest.raises(RerankingResponseSizeError, match="max_response_bytes=12"):
            await reranker.rerank("query", [Document("short")], limit=1)
        assert len(requests) == 1
    finally:
        await reranker.aclose()

    reranker = _voyage_reranker(
        lambda _: httpx.Response(503, text="private upstream body"), monkeypatch
    )
    try:
        with pytest.raises(RerankingError, match="HTTP 503") as error:
            await reranker.rerank("query", [Document("text")], limit=1)
        assert "private upstream body" not in str(error.value)
    finally:
        await reranker.aclose()


def test_voyage_reranker_rejects_duplicate_indexes_and_nonfinite_scores() -> None:
    docs = [Document("one"), Document("two")]
    with pytest.raises(RerankingError, match="invalid document index"):
        VoyageReranker._parse_response(
            {
                "results": [
                    {"index": 0, "relevance_score": 0.9},
                    {"index": 0, "relevance_score": 0.8},
                ]
            },
            docs,
            limit=2,
        )
    with pytest.raises(RerankingError, match="invalid relevance score"):
        VoyageReranker._parse_response(
            {"results": [{"index": 0, "relevance_score": float("nan")}]}, docs, limit=1
        )


def test_nvidia_reranker_configuration_and_inline_credentials() -> None:
    with pytest.raises(ValueError, match="requires HTTPS"):
        NvidiaReranker(base_url="http://remote.example")
    with pytest.raises(ValueError, match="model.api_key"):
        NvidiaReranker.from_config({"api_key": "secret"})
    with pytest.raises(ValueError, match="128 characters"):
        NvidiaReranker(model="x" * 129)

    reranker = NvidiaReranker.from_config({"model": "nvidia/test-reranker"})
    assert reranker.model == "nvidia/test-reranker"
    assert reranker.api_key_env == "NVIDIA_API_KEY"
    assert reranker.base_url == "https://ai.api.nvidia.com"


@pytest.mark.asyncio
async def test_nvidia_reranker_sends_bounded_text_and_maps_ranked_passages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"rankings": [{"index": 1, "logit": 2.5}, {"index": 0, "logit": -0.25}]},
        )

    docs = [
        Document("Account recovery instructions", source="support.md", id="account"),
        Document("Password reset steps", source="private.md", id="reset"),
    ]
    monkeypatch.setenv("NVIDIA_API_KEY", "nvidia-test-token")
    reranker = _nvidia_reranker(respond, monkeypatch)
    try:
        result = await reranker.rerank("reset my password", docs, limit=1)
    finally:
        await reranker.aclose()

    assert result == [docs[1]]
    assert result[0] is docs[1]
    assert requests[0].url == "https://ai.api.nvidia.com/v1/retrieval/nvidia/reranking"
    assert requests[0].headers["authorization"] == "Bearer nvidia-test-token"
    assert json.loads(requests[0].content) == {
        "model": "nvidia/rerank-qa-mistral-4b",
        "query": {"text": "reset my password"},
        "passages": [
            {"text": "Account recovery instructions"},
            {"text": "Password reset steps"},
        ],
        "truncate": "NONE",
    }
    assert "private.md" not in requests[0].content.decode()


@pytest.mark.asyncio
async def test_nvidia_reranker_bounds_requests_responses_and_sanitizes_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "token")
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, stream=_Chunks([b'{"rankings":', b"[]}"]))

    reranker = _nvidia_reranker(respond, monkeypatch, max_request_bytes=200, max_response_bytes=14)
    try:
        with pytest.raises(RerankingError, match="max_request_bytes=200"):
            await reranker.rerank("query", [Document("x" * 200)], limit=1)
        with pytest.raises(RerankingResponseSizeError, match="max_response_bytes=14"):
            await reranker.rerank("query", [Document("short")], limit=1)
        assert len(requests) == 1
    finally:
        await reranker.aclose()

    reranker = _nvidia_reranker(
        lambda _: httpx.Response(503, text="private upstream body"), monkeypatch
    )
    try:
        with pytest.raises(RerankingError, match="HTTP 503") as error:
            await reranker.rerank("query", [Document("text")], limit=1)
        assert "private upstream body" not in str(error.value)
    finally:
        await reranker.aclose()


def test_nvidia_reranker_rejects_duplicate_indexes_and_nonfinite_logits() -> None:
    docs = [Document("one"), Document("two")]
    with pytest.raises(RerankingError, match="invalid passage index"):
        NvidiaReranker._parse_response(
            {"rankings": [{"index": 0, "logit": 0.9}, {"index": 0, "logit": 0.8}]},
            docs,
            limit=2,
        )
    with pytest.raises(RerankingError, match="invalid logit"):
        NvidiaReranker._parse_response(
            {"rankings": [{"index": 0, "logit": float("nan")}]}, docs, limit=1
        )


def test_jina_reranker_configuration_and_inline_credentials() -> None:
    with pytest.raises(ValueError, match="requires HTTPS"):
        JinaReranker(base_url="http://remote.example/v1")
    with pytest.raises(ValueError, match="model.api_key"):
        JinaReranker.from_config({"api_key": "secret"})

    reranker = JinaReranker.from_config({"model": "jina-reranker-v2-base-multilingual"})
    assert reranker.model == "jina-reranker-v2-base-multilingual"
    assert reranker.api_key_env == "JINA_API_KEY"


@pytest.mark.asyncio
async def test_jina_reranker_bounds_requests_responses_and_sanitizes_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("JINA_API_KEY", "token")
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, stream=_Chunks([b'{"results":', b"[]}"]))

    reranker = _jina_reranker(respond, monkeypatch, max_request_bytes=200, max_response_bytes=12)
    try:
        with pytest.raises(RerankingError, match="max_request_bytes=200"):
            await reranker.rerank("query", [Document("x" * 200)], limit=1)
        with pytest.raises(RerankingResponseSizeError, match="max_response_bytes=12"):
            await reranker.rerank("query", [Document("short")], limit=1)
        assert len(requests) == 1
    finally:
        await reranker.aclose()

    reranker = _jina_reranker(
        lambda _: httpx.Response(503, text="private upstream body"), monkeypatch
    )
    try:
        with pytest.raises(RerankingError, match="HTTP 503") as error:
            await reranker.rerank("query", [Document("text")], limit=1)
        assert "private upstream body" not in str(error.value)
    finally:
        await reranker.aclose()


@pytest.mark.asyncio
async def test_cohere_reranker_reads_host_credentials_and_closes_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"results": [{"index": 0, "relevance_score": 0.5}]})

    monkeypatch.setenv("RERANK_TOKEN", "host-owned")
    reranker = _reranker(
        respond,
        monkeypatch,
        api_key_env="RERANK_TOKEN",
        base_url="https://rerank.example/v2/",
        model="test-reranker",
        max_tokens_per_doc=1234,
    )
    try:
        assert await reranker.rerank("query", [Document("text", id="doc")], limit=1)
    finally:
        await reranker.aclose()

    assert requests[0].url == "https://rerank.example/v2/rerank"
    assert requests[0].headers["authorization"] == "Bearer host-owned"
    assert reranker._client is None


@pytest.mark.asyncio
async def test_cohere_reranker_composes_with_reranking_retriever(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class CandidateRetriever:
        async def retrieve(
            self, query: str, *, limit: int = 5, filters: dict[str, Any] | None = None
        ) -> list[Document]:
            return [
                Document("irrelevant information", id="other"),
                Document("reset guidance", id="reset"),
            ]

    monkeypatch.setenv("COHERE_API_KEY", "token")
    reranker = _reranker(
        lambda _: httpx.Response(
            200,
            json={"results": [{"index": 1, "relevance_score": 0.99}]},
        ),
        monkeypatch,
    )
    retriever = RerankingRetriever(CandidateRetriever(), reranker, candidate_limit=2)
    try:
        result = await retriever.retrieve("password reset", limit=1)
    finally:
        await reranker.aclose()

    assert [document.id for document in result] == ["reset"]


@pytest.mark.asyncio
async def test_cohere_reranker_skips_empty_requests_without_credentials_or_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(_: httpx.Request) -> httpx.Response:
        raise AssertionError("empty reranking requests must not use the network")

    reranker = _reranker(fail, monkeypatch, api_key_env="MISSING_RERANK_TOKEN")
    assert await reranker.rerank(" ", [Document("text")], limit=1) == []
    assert await reranker.rerank("query", [], limit=1) == []
    assert await reranker.rerank("query", [Document("text")], limit=0) == []
    await reranker.aclose()


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"model": ""}, "model"),
        ({"api_key_env": "bad-name"}, "api_key_env"),
        ({"api_key": ""}, "api_key"),
        ({"max_tokens_per_doc": True}, "max_tokens_per_doc"),
        ({"max_tokens_per_doc": 32_769}, "max_tokens_per_doc"),
        ({"max_request_bytes": False}, "max_request_bytes"),
        ({"max_response_bytes": 0}, "max_response_bytes"),
        ({"timeout_seconds": float("inf")}, "timeout_seconds"),
        ({"base_url": "http://remote.example/v2"}, "requires HTTPS"),
        ({"base_url": "https://user:secret@example.test/v2"}, "Credential-bearing"),
        ({"base_url": "https://example.test/v2?api_key=secret"}, "Credential-bearing"),
    ],
)
def test_cohere_reranker_validates_configuration(kwargs: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        CohereReranker(**kwargs)


def test_cohere_reranker_from_config_rejects_inline_credentials() -> None:
    with pytest.raises(ValueError, match="model.api_key"):
        CohereReranker.from_config({"api_key": "secret"})
    with pytest.raises(ValueError, match="base_url"):
        CohereReranker.from_config({"base_url": 17})

    reranker = CohereReranker.from_config({"model": "rerank-test", "api_key_env": "RERANK_KEY"})
    assert reranker.model == "rerank-test"
    assert reranker.api_key_env == "RERANK_KEY"


@pytest.mark.asyncio
async def test_cohere_reranker_requires_a_host_credential(monkeypatch: pytest.MonkeyPatch) -> None:
    reranker = _reranker(lambda _: httpx.Response(200), monkeypatch, api_key_env="MISSING_KEY")
    with pytest.raises(RerankingError, match="credential is missing"):
        await reranker.rerank("query", [Document("text")], limit=1)
    await reranker.aclose()


@pytest.mark.asyncio
async def test_cohere_reranker_bounds_request_and_streamed_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requests: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, stream=_Chunks([b'{"results":', b"[]}"]))

    monkeypatch.setenv("COHERE_API_KEY", "token")
    reranker = _reranker(
        respond,
        monkeypatch,
        max_request_bytes=200,
        max_response_bytes=12,
    )
    try:
        with pytest.raises(RerankingError, match="max_request_bytes=200"):
            await reranker.rerank("query", [Document("x" * 200)], limit=1)
        with pytest.raises(RerankingResponseSizeError, match="max_response_bytes=12"):
            await reranker.rerank("query", [Document("short")], limit=1)
        assert len(requests) == 1
    finally:
        await reranker.aclose()


@pytest.mark.asyncio
async def test_cohere_reranker_sanitizes_http_and_transport_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("COHERE_API_KEY", "token")
    reranker = _reranker(
        lambda _: httpx.Response(503, text="provider returned private content"), monkeypatch
    )
    try:
        with pytest.raises(RerankingError, match="HTTP 503") as error:
            await reranker.rerank("query", [Document("text")], limit=1)
        assert "private content" not in str(error.value)
    finally:
        await reranker.aclose()

    reranker = _reranker(
        lambda _: (_ for _ in ()).throw(httpx.ConnectError("private endpoint")), monkeypatch
    )
    try:
        with pytest.raises(RerankingError, match="request failed") as error:
            await reranker.rerank("query", [Document("text")], limit=1)
        assert "private endpoint" not in str(error.value)
        assert error.value.__cause__ is None
        assert error.value.__suppress_context__
        assert "private endpoint" not in "".join(traceback.format_exception(error.value))
    finally:
        await reranker.aclose()

    reranker = _reranker(
        lambda _: httpx.Response(200, content=b'{"private response excerpt": invalid}'), monkeypatch
    )
    try:
        with pytest.raises(RerankingError, match="request failed") as error:
            await reranker.rerank("query", [Document("text")], limit=1)
        assert error.value.__cause__ is None
        assert error.value.__suppress_context__
        assert "private response excerpt" not in "".join(traceback.format_exception(error.value))
    finally:
        await reranker.aclose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("results", "message"),
    [
        (None, "invalid response object"),
        ([None], "invalid result entry"),
        ([{"index": True, "relevance_score": 0.5}], "invalid document index"),
        ([{"index": 4, "relevance_score": 0.5}], "invalid document index"),
        ([{"index": 0}], "invalid relevance score"),
        (
            [
                {"index": 0, "relevance_score": 0.9},
                {"index": 1, "relevance_score": 0.8},
            ],
            "more documents than requested",
        ),
    ],
)
async def test_cohere_reranker_rejects_invalid_responses(
    monkeypatch: pytest.MonkeyPatch, results: Any, message: str
) -> None:
    monkeypatch.setenv("COHERE_API_KEY", "token")
    reranker = _reranker(lambda _: httpx.Response(200, json={"results": results}), monkeypatch)
    try:
        with pytest.raises(RerankingError, match=message):
            await reranker.rerank("query", [Document("one")], limit=1)
    finally:
        await reranker.aclose()


def test_cohere_reranker_rejects_duplicate_indexes_and_nonfinite_scores() -> None:
    documents = [Document("one"), Document("two")]
    with pytest.raises(RerankingError, match="invalid document index"):
        CohereReranker._parse_response(
            {
                "results": [
                    {"index": 0, "relevance_score": 0.5},
                    {"index": 0, "relevance_score": 0.4},
                ]
            },
            documents,
            limit=2,
        )
    with pytest.raises(RerankingError, match="invalid relevance score"):
        CohereReranker._parse_response(
            {"results": [{"index": 0, "relevance_score": float("nan")}]},
            documents,
            limit=1,
        )


@pytest.mark.asyncio
async def test_cohere_reranker_rejects_too_many_documents_before_network(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    reranker = _reranker(
        lambda _: (_ for _ in ()).throw(AssertionError("must not call provider")), monkeypatch
    )
    with pytest.raises(ValueError, match="at most 100"):
        await reranker.rerank("query", [Document(str(index)) for index in range(101)], limit=1)
    await reranker.aclose()


@pytest.mark.parametrize("provider_type", [JinaReranker, VoyageReranker])
@pytest.mark.parametrize(
    ("settings", "message"),
    [
        ({"model": ""}, "model"),
        ({"api_key_env": "bad-name"}, "api_key_env"),
        ({"api_key": ""}, "api_key"),
        ({"max_request_bytes": True}, "max_request_bytes"),
        ({"max_response_bytes": 0}, "max_response_bytes"),
        ({"timeout_seconds": float("inf")}, "timeout_seconds"),
        ({"base_url": "http://remote.example/v1"}, "requires HTTPS"),
        ({"base_url": "https://user:secret@example.test/v1"}, "Credential-bearing"),
        ({"base_url": "https://example.test/v1?token=secret"}, "Credential-bearing"),
    ],
)
def test_hosted_rerankers_reject_invalid_configuration(
    provider_type: type[JinaReranker] | type[VoyageReranker],
    settings: dict[str, Any],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        provider_type(**settings)


@pytest.mark.parametrize("provider_type", [JinaReranker, VoyageReranker])
def test_hosted_rerankers_from_config_keep_credentials_host_owned(
    provider_type: type[JinaReranker] | type[VoyageReranker],
) -> None:
    with pytest.raises(ValueError, match="model.api_key"):
        provider_type.from_config({"model": "reranker", "api_key": "secret"})
    with pytest.raises(ValueError, match="base_url"):
        provider_type.from_config({"base_url": 17})

    provider = provider_type.from_config({"model": "reranker", "api_key_env": "RERANK_KEY"})
    assert provider.model == "reranker"
    assert provider.api_key is None
    assert provider.api_key_env == "RERANK_KEY"


@pytest.mark.parametrize("provider_type", [CohereReranker, JinaReranker, VoyageReranker])
@pytest.mark.asyncio
async def test_hosted_rerankers_validate_inputs_before_provider_calls(
    provider_type: type[CohereReranker] | type[JinaReranker] | type[VoyageReranker],
) -> None:
    provider = provider_type(api_key="test-token")
    documents = [Document("candidate")]
    try:
        with pytest.raises(TypeError, match="query"):
            await provider.rerank(3, documents, limit=1)  # type: ignore[arg-type]
        with pytest.raises(TypeError, match="sequence"):
            await provider.rerank("query", "candidate", limit=1)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="limit"):
            await provider.rerank("query", documents, limit=True)
        with pytest.raises(TypeError, match="Document"):
            await provider.rerank("query", ["candidate"], limit=1)  # type: ignore[list-item]
        with pytest.raises(ValueError, match="at most 100"):
            await provider.rerank("query", [Document(str(i)) for i in range(101)], limit=1)
        assert await provider.rerank(" ", documents, limit=1) == []
    finally:
        await provider.aclose()


@pytest.mark.parametrize("provider_type", [JinaReranker, VoyageReranker])
@pytest.mark.parametrize(
    "data",
    [
        None,
        {},
        {"results": [None]},
        {"results": [{"index": True, "relevance_score": 0.5}]},
        {"results": [{"index": -1, "relevance_score": 0.5}]},
        {"results": [{"index": 3, "relevance_score": 0.5}]},
        {"results": [{"index": 0, "relevance_score": True}]},
        {"results": [{"index": 0, "relevance_score": "0.5"}]},
        {"results": [{"index": 0, "relevance_score": float("inf")}]},
    ],
)
def test_hosted_rerankers_reject_malformed_rankings(
    provider_type: type[JinaReranker] | type[VoyageReranker], data: Any
) -> None:
    with pytest.raises(RerankingError):
        provider_type._parse_response(data, [Document("one"), Document("two")], limit=2)


@pytest.mark.parametrize("provider_type", [JinaReranker, VoyageReranker])
def test_hosted_rerankers_reject_excess_and_duplicate_results(
    provider_type: type[JinaReranker] | type[VoyageReranker],
) -> None:
    documents = [Document("one"), Document("two")]
    with pytest.raises(RerankingError, match="more documents than requested"):
        provider_type._parse_response(
            {"results": [{"index": 0, "relevance_score": 1}, {"index": 1, "relevance_score": 0}]},
            documents,
            limit=1,
        )
    with pytest.raises(RerankingError, match="invalid document index"):
        provider_type._parse_response(
            {
                "results": [
                    {"index": 0, "relevance_score": 1},
                    {"index": 0, "relevance_score": 0},
                ]
            },
            documents,
            limit=2,
        )
