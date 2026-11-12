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

"""Bounded pool of prestarted, single-use sandbox containers."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import replace

from .config import SandboxDefinition
from .sandbox import (
    ContainerSpec,
    EngineAdapter,
    SandboxCommandResult,
    SandboxError,
    SandboxResourceUsage,
    SandboxUnavailable,
    _adapter_for,
)


class WarmSandboxPool:
    """Keep a small number of ready Linux containers for one server-owned sandbox profile.

    A container is leased to exactly one run and removed after use. Prewarmed containers with
    per-run host mounts are never reused; they fall back to ordinary per-run startup. The pool
    deliberately requires a host-mount-free sandbox profile so caller workspaces and temporary
    tool payloads cannot cross run boundaries.
    """

    def __init__(
        self,
        config: SandboxDefinition,
        *,
        size: int,
        adapter: EngineAdapter | None = None,
    ) -> None:
        if isinstance(size, bool) or not isinstance(size, int) or size < 1 or size > 64:
            raise ValueError("warm sandbox pool size must be from 1 through 64")
        if config.workspace is not None:
            raise ValueError("warm sandbox pools require sandbox.workspace to be unset")
        self._config = config
        self._engine = adapter if adapter is not None else _adapter_for(config)
        self._owns_engine = adapter is None
        self._target_size = size
        self._idle: list[str] = []
        self._prototype: ContainerSpec | None = None
        self._lock = asyncio.Lock()
        self._refill_lock = asyncio.Lock()
        self._refill_task: asyncio.Task[None] | None = None
        self._refill_failures = 0
        self._closed = False

    async def start(self) -> None:
        """Validate the engine and fill the idle pool before the API accepts requests."""
        try:
            daemon_os = (await self._engine.daemon_os(timeout=30)).lower()
            if daemon_os != "linux":
                raise SandboxUnavailable("Warm sandbox pools currently require a Linux engine")
            image_os = await self._engine.image_os(self._config.image, timeout=30)
            if image_os is None:
                await self._engine.pull_image(self._config.image, timeout=120)
                image_os = await self._engine.image_os(self._config.image, timeout=30)
            if image_os is None or image_os.lower() != daemon_os:
                raise SandboxUnavailable("Warm sandbox image is unavailable or has the wrong OS")
            if self._config.process_limit is None:
                raise SandboxError("Warm Linux sandbox pools require a process limit")
            self._prototype = ContainerSpec(
                run_id="warm-" + uuid.uuid4().hex,
                image=self._config.image,
                image_os=image_os.lower(),
                daemon_os=daemon_os,
                keepalive_argv=self._config.keepalive_argv,
                workspace_host_path=None,
                workspace_container_path=None,
                workspace_read_only=True,
                cpus=self._config.cpus,
                memory_bytes=self._config.memory_bytes,
                process_limit=self._config.process_limit,
                runtime=self._config.runtime,
                user=self._config.user,
            )
            await self._refill()
        except BaseException:
            await self.aclose()
            raise

    async def _refill(self) -> None:
        async with self._refill_lock:
            while True:
                async with self._lock:
                    if self._closed or self._prototype is None:
                        return
                    if len(self._idle) >= self._target_size:
                        return
                    spec = replace(self._prototype, run_id="warm-" + uuid.uuid4().hex)
                container_id = await self._engine.start_container(spec, timeout=60)
                async with self._lock:
                    if self._closed:
                        should_remove = True
                    else:
                        self._idle.append(container_id)
                        should_remove = False
                if should_remove:
                    await self._engine.remove_container(container_id, timeout=10)
                    return

    def _matches_profile(self, spec: ContainerSpec) -> bool:
        prototype = self._prototype
        return (
            prototype is not None
            and spec.workspace_host_path is None
            and spec.workspace_container_path is None
            and spec.tool_input_host_path is None
            and spec.tool_input_container_path is None
            and (
                spec.image,
                spec.image_os,
                spec.daemon_os,
                spec.keepalive_argv,
                spec.cpus,
                spec.memory_bytes,
                spec.process_limit,
                spec.runtime,
                spec.user,
            )
            == (
                prototype.image,
                prototype.image_os,
                prototype.daemon_os,
                prototype.keepalive_argv,
                prototype.cpus,
                prototype.memory_bytes,
                prototype.process_limit,
                prototype.runtime,
                prototype.user,
            )
        )

    async def start_container(self, spec: ContainerSpec, *, timeout: float) -> str:
        """Lease a matching ready container or fall back to normal startup."""
        if not self._matches_profile(spec):
            return await self._engine.start_container(spec, timeout=timeout)
        async with self._lock:
            container_id = self._idle.pop() if self._idle else None
        if container_id is None:
            container_id = await self._engine.start_container(spec, timeout=timeout)
        self._schedule_refill()
        return container_id

    def _schedule_refill(self) -> None:
        if not self._closed and (self._refill_task is None or self._refill_task.done()):
            self._refill_task = asyncio.create_task(self._refill_safely())

    async def _refill_safely(self) -> None:
        try:
            await self._refill()
        except Exception:
            self._refill_failures += 1

    @property
    def refill_failures(self) -> int:
        """Return the count of background refill attempts that failed."""
        return self._refill_failures

    async def remove_container(self, container_id: str, *, timeout: float) -> None:
        """Destroy every leased container, then replenish the pool asynchronously."""
        await self._engine.remove_container(container_id, timeout=timeout)
        self._schedule_refill()

    async def daemon_os(self, *, timeout: float) -> str:
        return await self._engine.daemon_os(timeout=timeout)

    async def validate_windows_sandbox_support(self, *, timeout: float) -> None:
        await self._engine.validate_windows_sandbox_support(timeout=timeout)

    async def image_os(self, image: str, *, timeout: float) -> str | None:
        return await self._engine.image_os(image, timeout=timeout)

    async def pull_image(self, image: str, *, timeout: float) -> None:
        await self._engine.pull_image(image, timeout=timeout)

    async def exec(
        self,
        container_id: str,
        argv: Sequence[str],
        *,
        timeout: float,
        working_directory: str | None = None,
        environment: dict[str, str] | None = None,
    ) -> SandboxCommandResult:
        return await self._engine.exec(
            container_id,
            argv,
            timeout=timeout,
            working_directory=working_directory,
            environment=environment,
        )

    async def read_archive(self, container_id: str, path: str, *, timeout: float) -> bytes:
        return await self._engine.read_archive(container_id, path, timeout=timeout)

    async def write_archive(
        self, container_id: str, path: str, archive: bytes, *, timeout: float
    ) -> None:
        await self._engine.write_archive(container_id, path, archive, timeout=timeout)

    async def resource_usage(
        self, container_id: str, *, timeout: float
    ) -> SandboxResourceUsage | None:
        reader = getattr(self._engine, "resource_usage", None)
        if reader is None:
            return None
        result = await reader(container_id, timeout=timeout)
        return result if isinstance(result, SandboxResourceUsage) else None

    async def aclose(self) -> None:
        """Remove idle containers and close only an adapter created by this pool."""
        async with self._lock:
            if self._closed:
                return
            self._closed = True
            idle, self._idle = self._idle, []
        task = self._refill_task
        if task is not None and task is not asyncio.current_task() and not task.done():
            await asyncio.gather(task, return_exceptions=True)
        for container_id in idle:
            with suppress(Exception):
                await self._engine.remove_container(container_id, timeout=10)
        if self._owns_engine:
            await self._engine.aclose()
