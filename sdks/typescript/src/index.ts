// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      https://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
//
// Copyright 2026-present Gabby Contributors.

/** Generated lightweight client for Gabby's versioned HTTP and SSE API. */

export type JsonObject = Record<string, unknown>;

export interface RunRequest {
  input: string;
  context?: JsonObject;
  memory?: JsonObject;
  metadata?: JsonObject;
  host_context?: JsonObject | null;
  include_trace?: boolean;
}

export interface RunResponse {
  output: string;
  metadata: JsonObject;
  trace_id: string;
  trace: JsonObject | null;
}

export interface StreamEvent {
  type: string;
  data: JsonObject;
  event_id?: string;
}

export interface GabbyClientOptions {
  baseUrl: string;
  agentName: string;
  bearerToken?: string;
  headers?: Record<string, string>;
  fetch?: typeof fetch;
}

export class GabbyError extends Error {
  constructor(
    public readonly statusCode: number,
    public readonly errorType: string,
    message: string,
  ) {
    super(`${errorType}: ${message}`);
    this.name = "GabbyError";
  }
}

function validateBaseUrl(value: string): URL {
  const url = new URL(value);
  const loopback = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
  if (!new Set(["http:", "https:"]).has(url.protocol) || (url.protocol !== "https:" && !loopback)) {
    throw new TypeError("baseUrl must use HTTPS outside loopback");
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new TypeError("baseUrl must not contain credentials, a query, or a fragment");
  }
  return url;
}

export class GabbyClient {
  private readonly baseUrl: string;
  private readonly fetchImpl: typeof fetch;
  private readonly headers: Record<string, string>;

  constructor(options: GabbyClientOptions) {
    if (!options.agentName.trim()) throw new TypeError("agentName must not be empty");
    this.baseUrl = validateBaseUrl(options.baseUrl).toString().replace(/\/$/, "");
    this.fetchImpl = options.fetch ?? fetch;
    this.headers = { "content-type": "application/json", ...options.headers };
    if (options.bearerToken) this.headers.authorization = `Bearer ${options.bearerToken}`;
    this.agentName = options.agentName;
  }

  private readonly agentName: string;

  private endpoint(action: "run" | "stream"): string {
    return `${this.baseUrl}/v1/agents/${encodeURIComponent(this.agentName)}/${action}`;
  }

  async run(request: RunRequest, signal?: AbortSignal): Promise<RunResponse> {
    const response = await this.fetchImpl(this.endpoint("run"), {
      method: "POST",
      headers: this.headers,
      body: JSON.stringify(request),
      signal,
    });
    if (!response.ok) throw await this.toError(response);
    return (await response.json()) as RunResponse;
  }

  async *stream(
    request: RunRequest,
    options: { signal?: AbortSignal; idempotencyKey?: string; lastEventId?: string } = {},
  ): AsyncGenerator<StreamEvent> {
    const headers: Record<string, string> = { ...this.headers, accept: "text/event-stream" };
    if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;
    if (options.lastEventId) headers["Last-Event-ID"] = options.lastEventId;
    const response = await this.fetchImpl(this.endpoint("stream"), {
      method: "POST",
      headers,
      body: JSON.stringify(request),
      signal: options.signal,
    });
    if (!response.ok) throw await this.toError(response);
    if (!response.body) throw new Error("Gabby returned an empty SSE body");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let completed = false;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          completed = true;
          break;
        }
        buffer += decoder.decode(value, { stream: true });
        buffer = buffer.replace(/\r\n/g, "\n");
        let boundary: number;
        while ((boundary = buffer.indexOf("\n\n")) >= 0) {
          const block = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          const event = parseSseBlock(block);
          if (event) yield event;
        }
      }
      buffer = (buffer + decoder.decode()).replace(/\r\n/g, "\n");
      const finalEvent = parseSseBlock(buffer);
      if (finalEvent) yield finalEvent;
    } finally {
      if (!completed) {
        try {
          await reader.cancel();
        } catch {
          // Closing a caller-aborted stream is best-effort.
        }
      }
      reader.releaseLock();
    }
  }

  private async toError(response: Response): Promise<GabbyError> {
    try {
      const body = (await response.json()) as { detail?: { error?: string; error_type?: string } };
      return new GabbyError(
        response.status,
        body.detail?.error_type ?? "HTTPError",
        body.detail?.error ?? response.statusText,
      );
    } catch {
      return new GabbyError(response.status, "HTTPError", response.statusText);
    }
  }
}

function parseSseBlock(block: string): StreamEvent | undefined {
  const data: string[] = [];
  let eventId: string | undefined;
  for (const line of block.split("\n")) {
    if (!line || line.startsWith(":")) continue;
    const separator = line.indexOf(":");
    const field = separator < 0 ? line : line.slice(0, separator);
    const value = separator < 0 ? "" : line.slice(separator + 1).replace(/^ /, "");
    if (field === "data") data.push(value);
    if (field === "id") eventId = value;
  }
  if (!data.length) return undefined;
  const event = JSON.parse(data.join("\n")) as StreamEvent;
  if (eventId !== undefined) event.event_id = eventId;
  return event;
}
