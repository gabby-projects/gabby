from __future__ import annotations

import asyncio
import json
import sys
from types import SimpleNamespace
from typing import Any

import pytest

from gabby.mcp import load_mcp_tools
from gabby.orchestrators import langgraph_node
from gabby.tracing import (
    LFTraceExporter,
    OpenTelemetryTracer,
    SignedAuditExporter,
    TraceEvent,
)


@pytest.mark.asyncio
async def test_mcp_tools_are_allowlisted_and_return_structured_results() -> None:
    class FakeClient:
        async def __aenter__(self) -> FakeClient:
            return self

        async def __aexit__(self, *_: Any) -> None:
            return None

        async def list_tools(self) -> Any:
            return SimpleNamespace(
                tools=[
                    SimpleNamespace(
                        name="lookup",
                        description="Look up a record",
                        inputSchema={"type": "object", "properties": {"id": {"type": "string"}}},
                    ),
                    SimpleNamespace(
                        name="delete",
                        description="Delete a record",
                        inputSchema={"type": "object", "properties": {}},
                    ),
                ]
            )

        async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
            assert name == "lookup"
            return SimpleNamespace(isError=False, structuredContent={"id": arguments["id"]})

    registry = await load_mcp_tools(
        {"servers": {"records": {"url": "https://mcp.example.test", "allow_tools": ["lookup"]}}},
        client_factory=lambda _: FakeClient(),
    )
    assert registry.names() == ["records_lookup"]
    tool = registry.get("records_lookup")
    assert await tool.handler(id="42") == {"id": "42"}


@pytest.mark.asyncio
async def test_langgraph_adapter_maps_input_to_result_and_trace() -> None:
    class Client:
        async def arun(self, task: str, *, context: Any = None) -> Any:
            assert task == "Summarize this"
            assert context == {"locale": "en"}
            return SimpleNamespace(output="Summary", trace_id="trace-1")

    node = langgraph_node(Client(), context_key="context")
    assert await node({"input": "Summarize this", "context": {"locale": "en"}}) == {
        "gabby_output": "Summary",
        "gabby_trace_id": "trace-1",
    }


def test_otel_adapter_exports_safe_attributes_only() -> None:
    class Span:
        attributes: dict[str, Any]

        def __enter__(self) -> Span:
            self.attributes = {}
            return self

        def __exit__(self, *_: Any) -> None:
            return None

        def set_attribute(self, key: str, value: Any) -> None:
            self.attributes[key] = value

    class Tracer:
        def start_as_current_span(self, _: str) -> Span:
            self.span = Span()
            return self.span

    tracer = Tracer()
    exporter = OpenTelemetryTracer(tracer)

    async def record() -> None:
        await exporter.on_event(
            trace_id="trace-1",
            agent_name="test-agent",
            event=TraceEvent("tool_call", duration_ms=5, details={"secret": "do-not-export"}),
        )

    asyncio.run(record())
    assert tracer.span.attributes == {
        "gabby.trace_id": "trace-1",
        "gabby.agent": "test-agent",
        "gabby.event": "tool_call",
        "gabby.duration_ms": 5,
    }


def test_signed_audit_chain_records_policy_and_persona_without_payloads(tmp_path: Any) -> None:
    cryptography = pytest.importorskip("cryptography.hazmat.primitives.asymmetric.ed25519")
    key = cryptography.Ed25519PrivateKey.generate()
    raw_key = key.private_bytes_raw()
    path = tmp_path / "audit.jsonl"
    exporter = SignedAuditExporter(path, raw_key)

    async def record() -> None:
        await exporter.on_event(
            trace_id="trace-1",
            agent_name="test-agent",
            event=TraceEvent("tool_call", details={"name": "search", "arguments": {"secret": "x"}}),
        )
        await exporter.on_event(
            trace_id="trace-1",
            agent_name="test-agent",
            event=TraceEvent(
                "persona_verification",
                details={"result": {"passed": True, "method": "rule-check", "details": "private"}},
            ),
        )

    asyncio.run(record())
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert rows[0]["policy_decision"] == "allowed"
    assert rows[1]["persona_check"] == {"passed": True}
    assert rows[1]["previous_hash"] == rows[0]["record_hash"]
    assert "secret" not in path.read_text()
    SignedAuditExporter(path, raw_key)


def test_lf_trace_exporter_signs_tool_transcript_and_correlates_audit(
    tmp_path: Any, monkeypatch: Any
) -> None:
    signed_records: list[dict[str, Any]] = []

    def sign_record(record: dict[str, Any], key: Any) -> dict[str, Any]:
        signed = {**record, "signature": f"signed-by-{key}"}
        signed_records.append(signed)
        return signed

    canonical_json = SimpleNamespace(
        dumps=lambda value: json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    )
    monkeypatch.setitem(sys.modules, "agentrust_trace", SimpleNamespace(sign_record=sign_record))
    monkeypatch.setitem(sys.modules, "rfc8785", canonical_json)
    exporter = LFTraceExporter(
        tmp_path,
        claims={"subject": "spiffe://example/agent/test"},
        private_key="test-key",
    )

    async def record() -> None:
        await exporter.on_event(
            trace_id="trace-2",
            agent_name="test-agent",
            event=TraceEvent("tool_call", details={"name": "search"}),
        )
        await exporter.on_event(
            trace_id="trace-2",
            agent_name="test-agent",
            event=TraceEvent(
                "tool_error", details={"name": "delete", "error_code": "policy_denied"}
            ),
        )
        await exporter.on_event(
            trace_id="trace-2", agent_name="test-agent", event=TraceEvent("run_completed")
        )

    asyncio.run(record())
    trace_record = json.loads((tmp_path / "trace-2.trace.json").read_text())
    assert trace_record["tool_transcript"]["call_count"] == 2
    assert trace_record["tool_transcript"]["hash"].startswith("sha256:")
    assert trace_record["eat_profile"] == "tag:agentrust-io.com,2026:trace-v0.2"
    assert signed_records[0]["signature"] == "signed-by-test-key"
