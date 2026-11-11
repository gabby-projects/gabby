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
"""Bounded, host-configured reranking provider adapters."""

from __future__ import annotations

import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import httpx

from .config import (
    DEFAULT_MAX_MODEL_REQUEST_BYTES,
    DEFAULT_MAX_MODEL_RESPONSE_BYTES,
    validate_model_credentials,
    validate_model_endpoint,
)
from .knowledge import MAX_RETRIEVAL_DOCUMENTS, Document


class RerankingError(RuntimeError):
    """A reranking provider failed or returned an invalid result."""


class RerankingResponseSizeError(RerankingError):
    """A reranking provider response exceeded the configured byte limit."""


@dataclass
class CohereReranker:
    """Rerank a bounded set of document texts with Cohere's v2 rerank endpoint.

    Only document text is sent to the provider. Gabby maps returned indexes back to the original
    ``Document`` objects, preserving local source metadata and identifiers. Credentials are read
    from the host environment unless an application injects ``api_key`` directly.
    """

    model: str = "rerank-v4.0-fast"
    api_key: str | None = field(default=None, repr=False)
    api_key_env: str = "COHERE_API_KEY"
    base_url: str = "https://api.cohere.com/v2"
    max_tokens_per_doc: int = 4096
    max_request_bytes: int = DEFAULT_MAX_MODEL_REQUEST_BYTES
    max_response_bytes: int = DEFAULT_MAX_MODEL_RESPONSE_BYTES
    timeout_seconds: float = 120.0
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty Cohere rerank model name")
        self.model = self.model.strip()
        if not isinstance(self.api_key_env, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env
        ):
            raise ValueError("api_key_env must be an environment variable name")
        if self.api_key is not None and (
            not isinstance(self.api_key, str) or not self.api_key.strip()
        ):
            raise ValueError("api_key must be a non-empty string when provided")
        if (
            isinstance(self.max_tokens_per_doc, bool)
            or not isinstance(self.max_tokens_per_doc, int)
            or not 1 <= self.max_tokens_per_doc <= 32_768
        ):
            raise ValueError("max_tokens_per_doc must be an integer from 1 through 32768")
        for name, limit in (
            ("max_request_bytes", self.max_request_bytes),
            ("max_response_bytes", self.max_response_bytes),
        ):
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")
        if not isinstance(self.base_url, str):
            raise ValueError("base_url must be an HTTPS URL or loopback HTTP URL")
        validate_model_credentials({"base_url": self.base_url}, provider="cohere")
        validate_model_endpoint(self.base_url, provider="Cohere reranking")
        self.base_url = self.base_url.rstrip("/")

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> CohereReranker:
        """Create an adapter from non-secret configuration and host environment credentials."""
        validate_model_credentials(config, provider="cohere")
        base_url = config.get("base_url", "https://api.cohere.com/v2")
        if not isinstance(base_url, str):
            raise ValueError("base_url must be an HTTPS URL or loopback HTTP URL")
        return cls(
            model=config.get("model", "rerank-v4.0-fast"),
            api_key_env=config.get("api_key_env", "COHERE_API_KEY"),
            base_url=base_url.rstrip("/"),
            max_tokens_per_doc=config.get("max_tokens_per_doc", 4096),
            max_request_bytes=config.get("max_request_bytes", DEFAULT_MAX_MODEL_REQUEST_BYTES),
            max_response_bytes=config.get("max_response_bytes", DEFAULT_MAX_MODEL_RESPONSE_BYTES),
            timeout_seconds=config.get("timeout_seconds", 120.0),
        )

    async def rerank(
        self, query: str, documents: Sequence[Document], *, limit: int
    ) -> list[Document]:
        """Return the provider-ranked subset, mapping only validated indexes to input documents."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if not isinstance(documents, Sequence) or isinstance(documents, (str, bytes)):
            raise TypeError("documents must be a sequence of Document values")
        if len(documents) > MAX_RETRIEVAL_DOCUMENTS:
            raise ValueError(f"documents must contain at most {MAX_RETRIEVAL_DOCUMENTS} values")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100:
            raise ValueError("limit must be an integer from 0 through 100")
        if limit == 0 or not query.strip() or not documents:
            return []
        for document in documents:
            if not isinstance(document, Document) or not isinstance(document.text, str):
                raise TypeError("documents must contain Document values with string text")

        payload = {
            "model": self.model,
            "query": query,
            "documents": [document.text for document in documents],
            "top_n": min(limit, len(documents)),
            "max_tokens_per_doc": self.max_tokens_per_doc,
        }
        self._ensure_request_size(payload)
        key = self.api_key or os.environ.get(self.api_key_env)
        if not key:
            raise RerankingError(f"Cohere API credential is missing from {self.api_key_env}")
        client = self._client
        if client is None or client.is_closed:
            client = self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )

        try:
            async with client.stream(
                "POST",
                "/rerank",
                json=payload,
                timeout=httpx.Timeout(self.timeout_seconds),
            ) as response:
                if response.status_code >= 400:
                    raise RerankingError(f"Cohere reranking returned HTTP {response.status_code}")
                body = await self._read_response_limited(response)
                data = json.loads(body)
        except RerankingError:
            raise
        except (httpx.HTTPError, ValueError):
            raise RerankingError("Cohere reranking request failed") from None

        return self._parse_response(data, documents, limit=min(limit, len(documents)))

    async def aclose(self) -> None:
        """Close the shared HTTP connection pool."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    def _ensure_request_size(self, payload: dict[str, Any]) -> None:
        encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        byte_count = 0
        try:
            for part in encoder.iterencode(payload):
                byte_count += len(part.encode("utf-8"))
                if byte_count > self.max_request_bytes:
                    raise RerankingError(
                        "Serialized Cohere reranking request exceeded max_request_bytes="
                        f"{self.max_request_bytes}"
                    )
        except (TypeError, ValueError, UnicodeEncodeError) as exc:
            if isinstance(exc, RerankingError):
                raise
            raise RerankingError("Cohere reranking request is not valid JSON") from None

    async def _read_response_limited(self, response: httpx.Response) -> bytearray:
        body = bytearray()
        async for chunk in response.aiter_bytes():
            if len(body) + len(chunk) > self.max_response_bytes:
                raise RerankingResponseSizeError(
                    "Cohere reranking response exceeded max_response_bytes="
                    f"{self.max_response_bytes}"
                )
            body.extend(chunk)
        return body

    @staticmethod
    def _parse_response(data: Any, documents: Sequence[Document], *, limit: int) -> list[Document]:
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise RerankingError("Cohere reranking returned an invalid response object")
        results = data["results"]
        if len(results) > limit:
            raise RerankingError("Cohere reranking returned more documents than requested")
        ranked: list[Document] = []
        seen: set[int] = set()
        for result in results:
            if not isinstance(result, dict):
                raise RerankingError("Cohere reranking returned an invalid result entry")
            index = result.get("index")
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(documents)
                or index in seen
            ):
                raise RerankingError("Cohere reranking returned an invalid document index")
            score = result.get("relevance_score")
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise RerankingError("Cohere reranking returned an invalid relevance score")
            try:
                finite_score = math.isfinite(float(score))
            except OverflowError:
                finite_score = False
            if not finite_score:
                raise RerankingError("Cohere reranking returned an invalid relevance score")
            seen.add(index)
            ranked.append(documents[index])
        return ranked


@dataclass
class JinaReranker:
    """Rerank a bounded set of document texts with Jina's hosted rerank API."""

    model: str = "jina-reranker-v3.5"
    api_key: str | None = field(default=None, repr=False)
    api_key_env: str = "JINA_API_KEY"
    base_url: str = "https://api.jina.ai/v1"
    max_request_bytes: int = DEFAULT_MAX_MODEL_REQUEST_BYTES
    max_response_bytes: int = DEFAULT_MAX_MODEL_RESPONSE_BYTES
    timeout_seconds: float = 120.0
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty Jina rerank model name")
        self.model = self.model.strip()
        if not isinstance(self.api_key_env, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env
        ):
            raise ValueError("api_key_env must be an environment variable name")
        if self.api_key is not None and (
            not isinstance(self.api_key, str) or not self.api_key.strip()
        ):
            raise ValueError("api_key must be a non-empty string when provided")
        for name, limit in (
            ("max_request_bytes", self.max_request_bytes),
            ("max_response_bytes", self.max_response_bytes),
        ):
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")
        if not isinstance(self.base_url, str):
            raise ValueError("base_url must be an HTTPS URL or loopback HTTP URL")
        validate_model_credentials({"base_url": self.base_url}, provider="jina")
        validate_model_endpoint(self.base_url, provider="Jina reranking")
        self.base_url = self.base_url.rstrip("/")

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> JinaReranker:
        """Create an adapter from non-secret configuration and host environment credentials."""
        validate_model_credentials(config, provider="jina")
        base_url = config.get("base_url", "https://api.jina.ai/v1")
        if not isinstance(base_url, str):
            raise ValueError("base_url must be an HTTPS URL or loopback HTTP URL")
        return cls(
            model=config.get("model", "jina-reranker-v3.5"),
            api_key_env=config.get("api_key_env", "JINA_API_KEY"),
            base_url=base_url.rstrip("/"),
            max_request_bytes=config.get("max_request_bytes", DEFAULT_MAX_MODEL_REQUEST_BYTES),
            max_response_bytes=config.get("max_response_bytes", DEFAULT_MAX_MODEL_RESPONSE_BYTES),
            timeout_seconds=config.get("timeout_seconds", 120.0),
        )

    async def rerank(
        self, query: str, documents: Sequence[Document], *, limit: int
    ) -> list[Document]:
        """Return the provider-ranked subset while preserving original document objects."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if not isinstance(documents, Sequence) or isinstance(documents, (str, bytes)):
            raise TypeError("documents must be a sequence of Document values")
        if len(documents) > MAX_RETRIEVAL_DOCUMENTS:
            raise ValueError(f"documents must contain at most {MAX_RETRIEVAL_DOCUMENTS} values")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100:
            raise ValueError("limit must be an integer from 0 through 100")
        if limit == 0 or not query.strip() or not documents:
            return []
        for document in documents:
            if not isinstance(document, Document) or not isinstance(document.text, str):
                raise TypeError("documents must contain Document values with string text")

        payload = {
            "model": self.model,
            "query": query,
            "documents": [document.text for document in documents],
            "top_n": min(limit, len(documents)),
            "return_documents": False,
        }
        self._ensure_request_size(payload)
        key = self.api_key or os.environ.get(self.api_key_env)
        if not key:
            raise RerankingError(f"Jina API credential is missing from {self.api_key_env}")
        client = self._client
        if client is None or client.is_closed:
            client = self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
        try:
            async with client.stream(
                "POST", "/rerank", json=payload, timeout=httpx.Timeout(self.timeout_seconds)
            ) as response:
                if response.status_code >= 400:
                    raise RerankingError(f"Jina reranking returned HTTP {response.status_code}")
                body = await self._read_response_limited(response)
                data = json.loads(body)
        except RerankingError:
            raise
        except (httpx.HTTPError, ValueError):
            raise RerankingError("Jina reranking request failed") from None
        return self._parse_response(data, documents, limit=min(limit, len(documents)))

    async def aclose(self) -> None:
        """Close the shared HTTP connection pool."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    def _ensure_request_size(self, payload: dict[str, Any]) -> None:
        encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        byte_count = 0
        try:
            for part in encoder.iterencode(payload):
                byte_count += len(part.encode("utf-8"))
                if byte_count > self.max_request_bytes:
                    raise RerankingError(
                        "Serialized Jina reranking request exceeded max_request_bytes="
                        f"{self.max_request_bytes}"
                    )
        except (TypeError, ValueError, UnicodeEncodeError):
            raise RerankingError("Jina reranking request is not valid JSON") from None

    async def _read_response_limited(self, response: httpx.Response) -> bytearray:
        body = bytearray()
        async for chunk in response.aiter_bytes():
            if len(body) + len(chunk) > self.max_response_bytes:
                raise RerankingResponseSizeError(
                    f"Jina reranking response exceeded max_response_bytes={self.max_response_bytes}"
                )
            body.extend(chunk)
        return body

    @staticmethod
    def _parse_response(data: Any, documents: Sequence[Document], *, limit: int) -> list[Document]:
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise RerankingError("Jina reranking returned an invalid response object")
        results = data["results"]
        if len(results) > limit:
            raise RerankingError("Jina reranking returned more documents than requested")
        ranked: list[Document] = []
        seen: set[int] = set()
        for result in results:
            if not isinstance(result, dict):
                raise RerankingError("Jina reranking returned an invalid result entry")
            index = result.get("index")
            score = result.get("relevance_score")
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(documents)
                or index in seen
            ):
                raise RerankingError("Jina reranking returned an invalid document index")
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise RerankingError("Jina reranking returned an invalid relevance score")
            try:
                finite_score = math.isfinite(float(score))
            except OverflowError:
                finite_score = False
            if not finite_score:
                raise RerankingError("Jina reranking returned an invalid relevance score")
            seen.add(index)
            ranked.append(documents[index])
        return ranked


@dataclass
class VoyageReranker:
    """Rerank a bounded set of document texts with Voyage AI's hosted rerank API."""

    model: str = "rerank-2.5-lite"
    api_key: str | None = field(default=None, repr=False)
    api_key_env: str = "VOYAGE_API_KEY"
    base_url: str = "https://api.voyageai.com/v1"
    truncation: bool = False
    max_request_bytes: int = DEFAULT_MAX_MODEL_REQUEST_BYTES
    max_response_bytes: int = DEFAULT_MAX_MODEL_RESPONSE_BYTES
    timeout_seconds: float = 120.0
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip():
            raise ValueError("model must be a non-empty Voyage rerank model name")
        self.model = self.model.strip()
        if not isinstance(self.api_key_env, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env
        ):
            raise ValueError("api_key_env must be an environment variable name")
        if self.api_key is not None and (
            not isinstance(self.api_key, str) or not self.api_key.strip()
        ):
            raise ValueError("api_key must be a non-empty string when provided")
        if not isinstance(self.truncation, bool):
            raise ValueError("truncation must be a boolean")
        for name, limit in (
            ("max_request_bytes", self.max_request_bytes),
            ("max_response_bytes", self.max_response_bytes),
        ):
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")
        if not isinstance(self.base_url, str):
            raise ValueError("base_url must be an HTTPS URL or loopback HTTP URL")
        validate_model_credentials({"base_url": self.base_url}, provider="voyage")
        validate_model_endpoint(self.base_url, provider="Voyage reranking")
        self.base_url = self.base_url.rstrip("/")

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> VoyageReranker:
        """Create an adapter from non-secret settings and a host environment credential."""
        validate_model_credentials(config, provider="voyage")
        base_url = config.get("base_url", "https://api.voyageai.com/v1")
        if not isinstance(base_url, str):
            raise ValueError("base_url must be an HTTPS URL or loopback HTTP URL")
        return cls(
            model=config.get("model", "rerank-2.5-lite"),
            api_key_env=config.get("api_key_env", "VOYAGE_API_KEY"),
            base_url=base_url.rstrip("/"),
            truncation=config.get("truncation", False),
            max_request_bytes=config.get("max_request_bytes", DEFAULT_MAX_MODEL_REQUEST_BYTES),
            max_response_bytes=config.get("max_response_bytes", DEFAULT_MAX_MODEL_RESPONSE_BYTES),
            timeout_seconds=config.get("timeout_seconds", 120.0),
        )

    async def rerank(
        self, query: str, documents: Sequence[Document], *, limit: int
    ) -> list[Document]:
        """Return provider-ranked original documents after validating result indexes."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if not isinstance(documents, Sequence) or isinstance(documents, (str, bytes)):
            raise TypeError("documents must be a sequence of Document values")
        if len(documents) > MAX_RETRIEVAL_DOCUMENTS:
            raise ValueError(f"documents must contain at most {MAX_RETRIEVAL_DOCUMENTS} values")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100:
            raise ValueError("limit must be an integer from 0 through 100")
        if limit == 0 or not query.strip() or not documents:
            return []
        for document in documents:
            if not isinstance(document, Document) or not isinstance(document.text, str):
                raise TypeError("documents must contain Document values with string text")

        payload = {
            "model": self.model,
            "query": query,
            "documents": [document.text for document in documents],
            "top_k": min(limit, len(documents)),
            "return_documents": False,
            "truncation": self.truncation,
        }
        self._ensure_request_size(payload)
        key = self.api_key or os.environ.get(self.api_key_env)
        if not key:
            raise RerankingError(f"Voyage API credential is missing from {self.api_key_env}")
        client = self._client
        if client is None or client.is_closed:
            client = self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
        try:
            async with client.stream(
                "POST", "/rerank", json=payload, timeout=httpx.Timeout(self.timeout_seconds)
            ) as response:
                if response.status_code >= 400:
                    raise RerankingError(f"Voyage reranking returned HTTP {response.status_code}")
                body = await self._read_response_limited(response)
                data = json.loads(body)
        except RerankingError:
            raise
        except (httpx.HTTPError, ValueError):
            raise RerankingError("Voyage reranking request failed") from None
        return self._parse_response(data, documents, limit=min(limit, len(documents)))

    async def aclose(self) -> None:
        """Close the shared HTTP connection pool."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    def _ensure_request_size(self, payload: dict[str, Any]) -> None:
        encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        byte_count = 0
        try:
            for part in encoder.iterencode(payload):
                byte_count += len(part.encode("utf-8"))
                if byte_count > self.max_request_bytes:
                    raise RerankingError(
                        "Serialized Voyage reranking request exceeded max_request_bytes="
                        f"{self.max_request_bytes}"
                    )
        except (TypeError, ValueError, UnicodeEncodeError):
            raise RerankingError("Voyage reranking request is not valid JSON") from None

    async def _read_response_limited(self, response: httpx.Response) -> bytearray:
        body = bytearray()
        async for chunk in response.aiter_bytes():
            if len(body) + len(chunk) > self.max_response_bytes:
                raise RerankingResponseSizeError(
                    "Voyage reranking response exceeded max_response_bytes="
                    f"{self.max_response_bytes}"
                )
            body.extend(chunk)
        return body

    @staticmethod
    def _parse_response(data: Any, documents: Sequence[Document], *, limit: int) -> list[Document]:
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise RerankingError("Voyage reranking returned an invalid response object")
        results = data["results"]
        if len(results) > limit:
            raise RerankingError("Voyage reranking returned more documents than requested")
        ranked: list[Document] = []
        seen: set[int] = set()
        for result in results:
            if not isinstance(result, dict):
                raise RerankingError("Voyage reranking returned an invalid result entry")
            index = result.get("index")
            score = result.get("relevance_score")
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(documents)
                or index in seen
            ):
                raise RerankingError("Voyage reranking returned an invalid document index")
            if isinstance(score, bool) or not isinstance(score, (int, float)):
                raise RerankingError("Voyage reranking returned an invalid relevance score")
            try:
                finite_score = math.isfinite(float(score))
            except OverflowError:
                finite_score = False
            if not finite_score:
                raise RerankingError("Voyage reranking returned an invalid relevance score")
            seen.add(index)
            ranked.append(documents[index])
        return ranked


@dataclass
class NvidiaReranker:
    """Rerank candidates with NVIDIA's hosted NeMo retrieval reranking API."""

    model: str = "nvidia/rerank-qa-mistral-4b"
    api_key: str | None = field(default=None, repr=False)
    api_key_env: str = "NVIDIA_API_KEY"
    base_url: str = "https://ai.api.nvidia.com"
    max_request_bytes: int = DEFAULT_MAX_MODEL_REQUEST_BYTES
    max_response_bytes: int = DEFAULT_MAX_MODEL_RESPONSE_BYTES
    timeout_seconds: float = 120.0
    _client: httpx.AsyncClient | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip() or len(self.model) > 128:
            raise ValueError("model must contain from 1 through 128 characters")
        self.model = self.model.strip()
        if not isinstance(self.api_key_env, str) or not re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_]*", self.api_key_env
        ):
            raise ValueError("api_key_env must be an environment variable name")
        if self.api_key is not None and (
            not isinstance(self.api_key, str) or not self.api_key.strip()
        ):
            raise ValueError("api_key must be a non-empty string when provided")
        for name, limit in (
            ("max_request_bytes", self.max_request_bytes),
            ("max_response_bytes", self.max_response_bytes),
        ):
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
                raise ValueError(f"{name} must be a positive integer")
        if (
            isinstance(self.timeout_seconds, bool)
            or not isinstance(self.timeout_seconds, (int, float))
            or not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
        ):
            raise ValueError("timeout_seconds must be a finite positive number")
        if not isinstance(self.base_url, str):
            raise ValueError("base_url must be an HTTPS URL or loopback HTTP URL")
        validate_model_credentials({"base_url": self.base_url}, provider="nvidia")
        validate_model_endpoint(self.base_url, provider="NVIDIA reranking")
        self.base_url = self.base_url.rstrip("/")

    @classmethod
    def from_config(cls, config: Mapping[str, Any]) -> NvidiaReranker:
        """Create an adapter from non-secret settings and host environment credentials."""
        validate_model_credentials(config, provider="nvidia")
        base_url = config.get("base_url", "https://ai.api.nvidia.com")
        if not isinstance(base_url, str):
            raise ValueError("base_url must be an HTTPS URL or loopback HTTP URL")
        return cls(
            model=config.get("model", "nvidia/rerank-qa-mistral-4b"),
            api_key_env=config.get("api_key_env", "NVIDIA_API_KEY"),
            base_url=base_url.rstrip("/"),
            max_request_bytes=config.get("max_request_bytes", DEFAULT_MAX_MODEL_REQUEST_BYTES),
            max_response_bytes=config.get("max_response_bytes", DEFAULT_MAX_MODEL_RESPONSE_BYTES),
            timeout_seconds=config.get("timeout_seconds", 120.0),
        )

    async def rerank(
        self, query: str, documents: Sequence[Document], *, limit: int
    ) -> list[Document]:
        """Return the provider-ranked top subset after validating result indexes and scores."""
        if not isinstance(query, str):
            raise TypeError("query must be a string")
        if not isinstance(documents, Sequence) or isinstance(documents, (str, bytes)):
            raise TypeError("documents must be a sequence of Document values")
        if len(documents) > MAX_RETRIEVAL_DOCUMENTS:
            raise ValueError(f"documents must contain at most {MAX_RETRIEVAL_DOCUMENTS} values")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100:
            raise ValueError("limit must be an integer from 0 through 100")
        if limit == 0 or not query.strip() or not documents:
            return []
        for document in documents:
            if not isinstance(document, Document) or not isinstance(document.text, str):
                raise TypeError("documents must contain Document values with string text")

        payload = {
            "model": self.model,
            "query": {"text": query},
            "passages": [{"text": document.text} for document in documents],
            "truncate": "NONE",
        }
        self._ensure_request_size(payload)
        key = self.api_key or os.environ.get(self.api_key_env)
        if not key:
            raise RerankingError(f"NVIDIA API credential is missing from {self.api_key_env}")
        client = self._client
        if client is None or client.is_closed:
            client = self._client = httpx.AsyncClient(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            )
        try:
            async with client.stream(
                "POST",
                "/v1/retrieval/nvidia/reranking",
                json=payload,
                timeout=httpx.Timeout(self.timeout_seconds),
            ) as response:
                if response.status_code >= 400:
                    raise RerankingError(f"NVIDIA reranking returned HTTP {response.status_code}")
                body = await self._read_response_limited(response)
                data = json.loads(body)
        except RerankingError:
            raise
        except (httpx.HTTPError, ValueError):
            raise RerankingError("NVIDIA reranking request failed") from None
        return self._parse_response(data, documents, limit=min(limit, len(documents)))

    async def aclose(self) -> None:
        """Close the shared HTTP connection pool."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
        self._client = None

    def _ensure_request_size(self, payload: dict[str, Any]) -> None:
        encoder = json.JSONEncoder(ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        byte_count = 0
        try:
            for part in encoder.iterencode(payload):
                byte_count += len(part.encode("utf-8"))
                if byte_count > self.max_request_bytes:
                    raise RerankingError(
                        "Serialized NVIDIA reranking request exceeded max_request_bytes="
                        f"{self.max_request_bytes}"
                    )
        except (TypeError, ValueError, UnicodeEncodeError):
            raise RerankingError("NVIDIA reranking request is not valid JSON") from None

    async def _read_response_limited(self, response: httpx.Response) -> bytearray:
        body = bytearray()
        async for chunk in response.aiter_bytes():
            if len(body) + len(chunk) > self.max_response_bytes:
                raise RerankingResponseSizeError(
                    "NVIDIA reranking response exceeded max_response_bytes="
                    f"{self.max_response_bytes}"
                )
            body.extend(chunk)
        return body

    @staticmethod
    def _parse_response(data: Any, documents: Sequence[Document], *, limit: int) -> list[Document]:
        if not isinstance(data, dict) or not isinstance(data.get("rankings"), list):
            raise RerankingError("NVIDIA reranking returned an invalid response object")
        rankings = data["rankings"]
        if len(rankings) > len(documents):
            raise RerankingError("NVIDIA reranking returned more passages than provided")
        ranked: list[Document] = []
        seen: set[int] = set()
        for result in rankings:
            if not isinstance(result, dict):
                raise RerankingError("NVIDIA reranking returned an invalid ranking entry")
            index = result.get("index")
            logit = result.get("logit")
            if (
                isinstance(index, bool)
                or not isinstance(index, int)
                or not 0 <= index < len(documents)
                or index in seen
            ):
                raise RerankingError("NVIDIA reranking returned an invalid passage index")
            if isinstance(logit, bool) or not isinstance(logit, (int, float)):
                raise RerankingError("NVIDIA reranking returned an invalid logit")
            try:
                finite_logit = math.isfinite(float(logit))
            except OverflowError:
                finite_logit = False
            if not finite_logit:
                raise RerankingError("NVIDIA reranking returned an invalid logit")
            seen.add(index)
            if len(ranked) < limit:
                ranked.append(documents[index])
        return ranked
