<!--
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

     https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

Copyright 2026-present Gabby Contributors.
-->

# Live integration acceptance

## Container sandbox

These checks use a real Docker or Podman Linux runtime and are separate from the ordinary test
suite. They verify effective container settings, disabled network access, workspace mount modes,
shell and custom-tool execution, sandboxed Python source execution through the private tool-input
mount, cleanup after normal completion, and cleanup when an active run is cancelled.
The tests require the matching CLI and daemon; API-adapter checks also exercise the container API.

Run the complete Linux sandbox matrix with:

```sh
GABBY_RUN_DOCKER_INTEGRATION=1 GABBY_RUN_PODMAN_INTEGRATION=1 \
uv run --frozen pytest tests/integration/test_docker_sandbox_live.py \
  tests/integration/test_podman_sandbox_live.py -q
```

The matrix uses `python:3.14-slim`, pulling it when needed. Each run creates temporary containers
and workspaces, and asserts that each created container has been removed. Host/engine combinations
other than the Linux Docker and Podman runs still need separate acceptance evidence.
Native Windows Docker runs additionally require Docker Engine 29.1.4 or newer; Gabby checks this
before starting a Windows container with networking disabled.

The Docker API checks discover a local Unix socket from `DOCKER_HOST=unix://...`, then try
`/var/run/docker.sock` and Docker Desktop's `~/.docker/run/docker.sock`. Set
`GABBY_DOCKER_API_SOCKET` to override discovery when a host uses another local socket path. On
macOS with Docker Desktop, run the same Docker acceptance with:

```sh
GABBY_DOCKER_API_SOCKET="$HOME/.docker/run/docker.sock" \
GABBY_RUN_DOCKER_INTEGRATION=1 \
uv run --frozen pytest tests/integration/test_docker_sandbox_live.py -q
```

This command exercises both the Docker CLI and API adapters on the macOS host. It is acceptance
coverage to run on macOS; a passing Linux Docker run does not verify it.

## Native Windows Docker

Run this acceptance on a Windows host with the Hyper-V feature enabled, a Windows-container Docker
daemon at version 29.1.4 or newer, and an image compatible with that host. The image must contain
PowerShell and `cmd.exe`; read/write workspace acceptance also requires the image user to have
permission to write to the temporary bind mount. Gabby checks Hyper-V isolation, CPU and memory
settings, network denial from inside the container, read-only and read/write workspace behavior,
and per-run cleanup, including cancellation. These checks are opt-in. The API adapter connects to
Docker Desktop's named pipe and requires the `windows-sandbox` extra:

```powershell
uv sync --extra windows-sandbox
$env:GABBY_RUN_WINDOWS_DOCKER_INTEGRATION = "1"
$env:GABBY_WINDOWS_DOCKER_IMAGE = "mcr.microsoft.com/windows/servercore:ltsc2022"
$env:GABBY_WINDOWS_DOCKER_NAMED_PIPE = "\\.\pipe\docker_engine"
uv run --frozen pytest tests/integration/test_windows_docker_sandbox_live.py -q
```

Choose a Windows image tag supported by the host and ensure Docker can pull it. The test does not
configure the Docker daemon or install/enable Hyper-V for you. It runs the isolation, mount, network,
and cleanup checks through both the CLI adapter and the API adapter over the named pipe. The API
adapter requires the standard Proactor event loop used by Windows Python; alternate event loops that
do not support named pipes are rejected by the transport.

## Live model-provider acceptance

These checks contact real model providers, so they are opt-in and skipped in the normal test
suite. Hosted providers receive one completion and one streaming completion;
acceptance loads a selected checkpoint and runs one bounded completion. Use a model endpoint,
checkpoint, and account approved for the prompts used by these smoke tests.

## Cohere reranking

The reranker acceptance is opt-in and verifies the live API contract and candidate identity mapping.
It does not measure ranking quality. Configure `COHERE_API_KEY` and optionally select a model:

```sh
GABBY_RUN_COHERE_RERANK_INTEGRATION=1 \
GABBY_COHERE_RERANK_MODEL=rerank-v4.0-fast \
uv run --frozen pytest tests/integration/test_cohere_reranker_live.py -q
```

The adapter defaults to `https://api.cohere.com/v2/rerank`, sends candidate text to Cohere, and does
not send source metadata or document IDs. The model and endpoint must be enabled for the account.

## Jina reranking

This opt-in check verifies a live ranking request and candidate identity mapping; it does not measure
general ranking quality. Set `JINA_API_KEY` and optionally select a model:

```sh
GABBY_RUN_JINA_RERANK_INTEGRATION=1 \
GABBY_JINA_RERANK_MODEL=jina-reranker-v3.5 \
uv run --frozen pytest tests/integration/test_jina_reranker_live.py -q
```

The adapter posts candidate text to Jina's `https://api.jina.ai/v1/rerank` endpoint. Review [Jina's
reranker API](https://jina.ai/en-US/reranker/) and account terms before enabling the check; usage
charges may apply.

## Voyage reranking

This opt-in check verifies a live ranking request and candidate identity mapping; it does not measure
general ranking quality. Set `VOYAGE_API_KEY` and run:

```sh
GABBY_RUN_VOYAGE_RERANK_INTEGRATION=1 \
GABBY_VOYAGE_RERANK_MODEL=rerank-2.5-lite \
uv run --frozen pytest tests/integration/test_voyage_reranker_live.py -q
```

The adapter posts to `https://api.voyageai.com/v1/rerank`, asks for index-only results, and disables
provider-side truncation by default. Candidate text is sent to Voyage; the live check may incur
account usage charges. Review Voyage's [reranker API reference](https://docs.voyageai.com/reference/reranker-api)
and account terms before enabling it.

## NVIDIA reranking

This opt-in contract check sends candidate text to NVIDIA and verifies ranking and candidate identity
mapping; it does not measure general ranking quality. Set `NVIDIA_API_KEY` and run:

```sh
GABBY_RUN_NVIDIA_RERANK_INTEGRATION=1 \
GABBY_NVIDIA_RERANK_MODEL=nvidia/rerank-qa-mistral-4b \
uv run --frozen pytest tests/integration/test_nvidia_reranker_live.py -q
```

The default endpoint is NVIDIA's hosted NeMo reranking API. Review [its API reference](https://docs.api.nvidia.com/nim/reference/nvidia-nim-rerankqa-mistral-4b-v3-infer)
and service terms before enabling the check; account usage charges may apply.

## Ollama

Make sure Ollama is running and the selected model is available locally, then run:

```sh
GABBY_RUN_OLLAMA_INTEGRATION=1 \
GABBY_OLLAMA_MODEL=your-local-model \
uv run --frozen pytest tests/integration/test_model_providers_live.py -k ollama -q
```

The adapter defaults to `http://localhost:11434/v1`. Set `GABBY_OLLAMA_BASE_URL` to use another
endpoint and `GABBY_OLLAMA_API_KEY` when that endpoint requires a bearer token. Remote endpoints
must use HTTPS; HTTP is accepted only for loopback.

## Hugging Face Inference Providers

Provide a token through the host environment and select a model available to your account:

```sh
GABBY_RUN_HUGGINGFACE_INTEGRATION=1 \
GABBY_HUGGINGFACE_MODEL=org/model:provider \
HF_TOKEN=... \
uv run --frozen pytest tests/integration/test_model_providers_live.py -k huggingface -q
```

The adapter defaults to `https://router.huggingface.co/v1`; set
`GABBY_HUGGINGFACE_BASE_URL` to override it. Model availability depends on the selected model,
provider, account, and current service access. Do not put a real token in a command recorded to shell
history; use the host's secret manager or protected environment injection.

## Anthropic Messages API

Set an Anthropic API key through the host environment and choose a model enabled for that account:

```sh
GABBY_RUN_ANTHROPIC_INTEGRATION=1 \
GABBY_ANTHROPIC_MODEL=your-enabled-model-id \
uv run --frozen pytest tests/integration/test_model_providers_live.py -k anthropic -q
```

The check performs one completion and one streamed completion through the native Messages API. The
default endpoint is `https://api.anthropic.com/v1`; use `GABBY_ANTHROPIC_BASE_URL` for an approved
compatible endpoint. It can incur API usage charges. Keep `ANTHROPIC_API_KEY` in a secret manager or
protected environment injection and out of shell history. See Anthropic's
[Messages API reference](https://docs.anthropic.com/en/api/messages).

## Google Gemini

Set a Gemini API key through the host environment and choose a model available to the account:

```sh
GABBY_RUN_GEMINI_INTEGRATION=1 \
GABBY_GEMINI_MODEL=your-enabled-model-id \
uv run --frozen pytest tests/integration/test_model_providers_live.py -k gemini -q
```

The check performs one completion and one streamed completion against the native Gemini
GenerateContent API. The default endpoint is Google's `v1beta` API; set `GABBY_GEMINI_BASE_URL` only
for an approved compatible endpoint. It can incur API usage charges. Keep `GEMINI_API_KEY` in a
secret manager or protected environment injection and out of shell history. Model and API
availability depends on the account and selected model.

## Both providers

Set both opt-in flags, both model IDs, and `HF_TOKEN`, then run the test file without `-k`. Only the
enabled providers make requests. The assertions check non-empty completion output, streamed text
deltas, and one completion event. They do not evaluate answer quality or prove tool-calling behavior.
