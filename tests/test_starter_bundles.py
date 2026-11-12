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

import base64
import filecmp
from pathlib import Path

import pytest

from gabby.config import load_agent, load_skill
from gabby.skill_packages import inspect_skill_package
from scripts.build_starter_bundles import STARTER_NAMES, build

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("bundle_name", STARTER_NAMES)
def test_starter_bundle_agent_and_skill_configs_load(bundle_name: str) -> None:
    bundle = ROOT / "bundles" / "starter-packs" / bundle_name

    agent = load_agent(bundle / "agent.yaml")
    skill = load_skill(bundle / "skills" / bundle_name / "skill.yaml")

    assert agent.skills == [f"{bundle_name}@1.0.0"]
    assert skill.name == bundle_name
    assert skill.version == "1.0.0"
    assert set(skill.tools).issubset(agent.tools)
    assert set(agent.policies["allowed_tools"]).issubset(agent.tools)


def test_starter_bundle_build_requires_publisher_key(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv("GABBY_STARTER_SIGNING_KEY", raising=False)
    monkeypatch.delenv("GABBY_STARTER_SIGNING_KEY_ID", raising=False)

    with pytest.raises(ValueError, match="GABBY_STARTER_SIGNING_KEY_ID"):
        build(tmp_path / "starter-output")

    assert not (tmp_path / "starter-output").exists()


def test_starter_bundle_build_rejects_unsafe_key_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("GABBY_STARTER_SIGNING_KEY_ID", "../../outside")
    monkeypatch.setenv("GABBY_STARTER_SIGNING_KEY", base64.b64encode(b"0" * 32).decode())

    with pytest.raises(ValueError, match="key ID"):
        build(tmp_path / "starter-output")

    assert not (tmp_path / "starter-output").exists()


def test_starter_bundle_build_signs_and_verifies_all_packages(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    cryptography = pytest.importorskip("cryptography")
    del cryptography
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private_key = Ed25519PrivateKey.generate()
    raw_private_key = private_key.private_bytes(
        serialization.Encoding.Raw,
        serialization.PrivateFormat.Raw,
        serialization.NoEncryption(),
    )
    monkeypatch.setenv("GABBY_STARTER_SIGNING_KEY_ID", "test-starter-key")
    monkeypatch.setenv("GABBY_STARTER_SIGNING_KEY", base64.b64encode(raw_private_key).decode())
    output = tmp_path / "starter-output"

    build(output)

    public_key = (output / "trusted-publishers" / "test-starter-key.pub").read_bytes()
    for bundle_name in STARTER_NAMES:
        archive = output / f"{bundle_name}-1.0.0.gabskill"
        inspection = inspect_skill_package(archive, trusted_keys={"test-starter-key": public_key})
        assert inspection.signature_verified
        assert inspection.name == bundle_name
        assert (output / f"{bundle_name}.agent.yaml").is_file()
        assert (output / f"{bundle_name}.AUDIT.md").is_file()
    assert (output / "workspace" / ".gitkeep").is_file()
    assert all("private" not in path.name for path in output.rglob("*"))


@pytest.mark.parametrize("language", ["typescript", "go", "rust"])
def test_generated_sdks_match_repository_templates(language: str) -> None:
    template_root = ROOT / "sdks" / "templates" / language
    generated_root = ROOT / "sdks" / language
    template_files = sorted(path.relative_to(template_root) for path in template_root.rglob("*"))
    expected_files = [path for path in template_files if (template_root / path).is_file()]
    generated_files = sorted(
        path.relative_to(generated_root)
        for path in generated_root.rglob("*")
        if path.is_file()
        and "target" not in path.relative_to(generated_root).parts
        and path.name != "Cargo.lock"
    )
    assert generated_files == expected_files
    assert all(
        filecmp.cmp(template_root / path, generated_root / path, shallow=False)
        for path in expected_files
    )


def test_generated_sdk_sources_implement_run_sse_and_resume_contracts() -> None:
    typescript = (ROOT / "sdks/typescript/src/index.ts").read_text(encoding="utf-8")
    go = (ROOT / "sdks/go/client.go").read_text(encoding="utf-8")
    rust = (ROOT / "sdks/rust/src/lib.rs").read_text(encoding="utf-8")
    for source in (typescript, go):
        assert "/v1/agents/" in source
        assert "run" in source and "stream" in source
        assert "Idempotency-Key" in source
        assert "Last-Event-ID" in source
    assert '"v1").push("agents' in rust
    assert "run" in rust and "stream" in rust
    assert "Idempotency-Key" in rust
    assert "Last-Event-ID" in rust
