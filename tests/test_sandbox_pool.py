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

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from gabby.agent import Agent
from gabby.config import AgentDefinition, SandboxDefinition
from gabby.models import ModelResponse
from gabby.sandbox import (
    ContainerSpec,
    SandboxCommandResult,
    SandboxError,
    SandboxResourceUsage,
    SandboxUnavailable,
)
from gabby.sandbox_pool import WarmSandboxPool
from gabby.server import create_app


class FakeEngine:
    def __init__(self) -> None:
        self.started: list[ContainerSpec] = []
        self.removed: list[str] = []
        self.closed = False
        self.next_id = 0
        self.daemon_platform = "linux"
        self.image_platform: str | None = "linux"
        self.pull_count = 0
        self.fail_start_on: int | None = None
        self.windows_validation_count = 0
        self.exec_calls: list[tuple[str, Sequence[str]]] = []
        self.archive_writes: list[tuple[str, str, bytes]] = []

    async def daemon_os(self, *, timeout: float) -> str:
        assert timeout > 0
        return self.daemon_platform

    async def validate_windows_sandbox_support(self, *, timeout: float) -> None:
        self.windows_validation_count += 1

    async def image_os(self, image: str, *, timeout: float) -> str | None:
        assert image == "example/sandbox:1"
        assert timeout > 0
        return self.image_platform

    async def pull_image(self, image: str, *, timeout: float) -> None:
        assert image == "example/sandbox:1"
        assert timeout > 0
        self.pull_count += 1

    async def start_container(self, spec: ContainerSpec, *, timeout: float) -> str:
        assert timeout > 0
        self.next_id += 1
        if self.next_id == self.fail_start_on:
            raise RuntimeError("container start failed")
        self.started.append(spec)
        return f"container-{self.next_id}"

    async def exec(
        self,
        container_id: str,
        argv: Sequence[str],
        *,
        timeout: float,
        working_directory: str | None = None,
        environment: dict[str, str] | None = None,
    ) -> SandboxCommandResult:
        self.exec_calls.append((container_id, argv))
        return SandboxCommandResult(0, b"", b"")

    async def read_archive(self, container_id: str, path: str, *, timeout: float) -> bytes:
        return b""

    async def write_archive(
        self, container_id: str, path: str, archive: bytes, *, timeout: float
    ) -> None:
        self.archive_writes.append((container_id, path, archive))

    async def remove_container(self, container_id: str, *, timeout: float) -> None:
        self.removed.append(container_id)

    async def aclose(self) -> None:
        self.closed = True


def _sandbox() -> SandboxDefinition:
    return SandboxDefinition(
        engine="docker",
        image="example/sandbox:1",
        keepalive_argv=("sleep", "infinity"),
        process_limit=64,
    )


def _run_spec(*, tool_input: bool = False) -> ContainerSpec:
    return ContainerSpec(
        run_id="run-1",
        image="example/sandbox:1",
        image_os="linux",
        daemon_os="linux",
        keepalive_argv=("sleep", "infinity"),
        workspace_host_path=None,
        workspace_container_path=None,
        workspace_read_only=True,
        cpus=2.0,
        memory_bytes=2 * 1024**3,
        process_limit=64,
        tool_input_host_path="/tmp/run-input" if tool_input else None,
        tool_input_container_path="/tmp/gabby-tool-input" if tool_input else None,
        user="65532:65532",
    )


@pytest.mark.asyncio
async def test_pool_leases_prestarted_single_use_containers_and_refills() -> None:
    engine = FakeEngine()
    pool = WarmSandboxPool(_sandbox(), size=2, adapter=engine)
    await pool.start()

    assert len(engine.started) == 2
    first = await pool.start_container(_run_spec(), timeout=10)
    assert first in {"container-1", "container-2"}
    assert len(engine.started) == 2

    await pool.remove_container(first, timeout=10)
    await pool._refill()
    assert len(engine.started) == 3
    assert first in engine.removed

    idle_ids = {spec.run_id for spec in engine.started[-2:]}
    await pool.aclose()
    assert engine.closed is False  # Injected adapters remain host-owned.
    assert len(engine.removed) == 3
    assert len(idle_ids) == 2


@pytest.mark.asyncio
async def test_pool_falls_back_for_per_run_mounts() -> None:
    engine = FakeEngine()
    pool = WarmSandboxPool(_sandbox(), size=1, adapter=engine)
    await pool.start()

    container_id = await pool.start_container(_run_spec(tool_input=True), timeout=10)

    assert container_id == "container-2"
    assert len(engine.started) == 2
    await pool.aclose()


@pytest.mark.asyncio
async def test_pool_start_fails_closed_for_unsupported_engine_or_image() -> None:
    cases = [
        ("windows", "linux", "Linux engine"),
        ("linux", None, "image is unavailable"),
        ("linux", "windows", "wrong OS"),
    ]
    for daemon_os, image_os, message in cases:
        engine = FakeEngine()
        engine.daemon_platform = daemon_os
        engine.image_platform = image_os
        if image_os is None:
            engine.image_platform = None
        pool = WarmSandboxPool(_sandbox(), size=1, adapter=engine)

        with pytest.raises(SandboxUnavailable, match=message):
            await pool.start()

        assert engine.closed is False
        assert not engine.started
        assert engine.pull_count == (1 if image_os is None else 0)


@pytest.mark.asyncio
async def test_pool_pulls_missing_image_then_rechecks_before_warming() -> None:
    class PullThenAvailableEngine(FakeEngine):
        image_checks = 0

        async def image_os(self, image: str, *, timeout: float) -> str | None:
            self.image_checks += 1
            if self.image_checks == 1:
                return None
            return "linux"

    engine = PullThenAvailableEngine()
    pool = WarmSandboxPool(_sandbox(), size=1, adapter=engine)
    await pool.start()

    assert engine.pull_count == 1
    assert engine.image_checks == 2
    assert len(engine.started) == 1
    await pool.aclose()


@pytest.mark.asyncio
async def test_pool_requires_process_limit_and_closes_owned_engine_on_start_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from gabby import sandbox_pool

    engine = FakeEngine()
    monkeypatch.setattr(sandbox_pool, "_adapter_for", lambda _: engine)
    config = SandboxDefinition(
        engine="docker",
        image="example/sandbox:1",
        keepalive_argv=("sleep", "infinity"),
        process_limit=None,
    )
    pool = WarmSandboxPool(config, size=1)

    with pytest.raises(SandboxError, match="process limit"):
        await pool.start()

    assert engine.closed is True


@pytest.mark.asyncio
async def test_pool_falls_back_when_empty_and_records_background_refill_failure() -> None:
    engine = FakeEngine()
    engine.fail_start_on = 2
    pool = WarmSandboxPool(_sandbox(), size=1, adapter=engine)
    await pool.start()

    leased = await pool.start_container(_run_spec(), timeout=10)
    assert leased == "container-1"
    assert pool._refill_task is not None
    await pool._refill_task
    assert pool.refill_failures == 1

    engine.fail_start_on = None
    fallback = await pool.start_container(_run_spec(), timeout=10)
    assert fallback == "container-3"
    await pool.aclose()


@pytest.mark.asyncio
async def test_pool_does_not_reuse_mismatched_profile_and_proxies_engine_calls() -> None:
    from dataclasses import replace

    engine = FakeEngine()
    pool = WarmSandboxPool(_sandbox(), size=1, adapter=engine)
    await pool.start()
    fallback = await pool.start_container(replace(_run_spec(), user="1000:1000"), timeout=7)
    assert fallback == "container-2"

    assert await pool.daemon_os(timeout=2) == "linux"
    await pool.validate_windows_sandbox_support(timeout=2)
    assert engine.windows_validation_count == 1
    assert await pool.image_os("example/sandbox:1", timeout=2) == "linux"
    await pool.pull_image("example/sandbox:1", timeout=2)
    assert engine.pull_count == 1
    result = await pool.exec("container-x", ["true"], timeout=2)
    assert result.exit_code == 0
    assert engine.exec_calls == [("container-x", ["true"])]
    assert await pool.read_archive("container-x", "/tmp/data", timeout=2) == b""
    await pool.write_archive("container-x", "/tmp/data", b"data", timeout=2)
    assert engine.archive_writes == [("container-x", "/tmp/data", b"data")]
    assert await pool.resource_usage("container-x", timeout=2) is None

    async def read_usage(container_id: str, *, timeout: float) -> SandboxResourceUsage:
        assert container_id == "container-x"
        assert timeout == 2
        return SandboxResourceUsage(cpu_percent=1, memory_current_bytes=2)

    engine.resource_usage = read_usage  # type: ignore[attr-defined]
    assert await pool.resource_usage("container-x", timeout=2) == SandboxResourceUsage(
        cpu_percent=1, memory_current_bytes=2
    )

    async def malformed_usage(container_id: str, *, timeout: float) -> object:
        return {"cpu_percent": 1}

    engine.resource_usage = malformed_usage  # type: ignore[attr-defined]
    assert await pool.resource_usage("container-x", timeout=2) is None
    await pool.aclose()


@pytest.mark.asyncio
async def test_pool_close_is_idempotent_and_tolerates_container_cleanup_errors() -> None:
    class FailingCleanupEngine(FakeEngine):
        async def remove_container(self, container_id: str, *, timeout: float) -> None:
            raise RuntimeError("cleanup unavailable")

    engine = FailingCleanupEngine()
    pool = WarmSandboxPool(_sandbox(), size=1, adapter=engine)
    await pool.start()

    await pool.aclose()
    await pool.aclose()

    assert engine.closed is False
    assert pool._closed is True


def test_pool_rejects_workspace_mounts(tmp_path: Path) -> None:
    from gabby.config import WorkspaceMount

    config = SandboxDefinition(
        engine="docker",
        image="example/sandbox:1",
        keepalive_argv=("sleep", "infinity"),
        workspace=WorkspaceMount(tmp_path, "read_only", "/workspace"),
    )
    with pytest.raises(ValueError, match="workspace to be unset"):
        WarmSandboxPool(config, size=1, adapter=FakeEngine())


@pytest.mark.parametrize("size", [-1, 65, True, 1.5])
def test_fastapi_rejects_invalid_warm_pool_sizes(size: object) -> None:
    with pytest.raises(ValueError, match="warm_sandbox_pool_size"):
        create_app(
            make_minimal_agent(),
            warm_sandbox_pool_size=size,  # type: ignore[arg-type]
            allow_unauthenticated=True,
        )


def make_minimal_agent() -> Agent:
    class Model:
        name = "test-model"

        async def complete(self, **_: object) -> ModelResponse:
            return ModelResponse(content="ok")

    return Agent(
        AgentDefinition(name="pool-agent", model={"provider": "fake", "model": "test-model"}),
        model=Model(),
    )


@pytest.mark.asyncio
async def test_fastapi_lifespan_warms_and_closes_pool() -> None:
    class Model:
        name = "test-model"

        async def complete(self, **_: object) -> ModelResponse:
            return ModelResponse(content="ok")

    engine = FakeEngine()
    original_adapter = engine
    agent = Agent(
        AgentDefinition(
            name="pool-agent",
            model={"provider": "fake", "model": "test-model"},
            sandbox=_sandbox(),
        ),
        model=Model(),
        sandbox_adapter=engine,
    )
    app = create_app(agent, warm_sandbox_pool_size=2, allow_unauthenticated=True)

    async with app.router.lifespan_context(app):
        assert len(engine.started) == 2
        assert agent.sandbox_adapter is not original_adapter

    assert engine.closed is False
    assert len(engine.removed) == 2
    assert agent.sandbox_adapter is original_adapter
