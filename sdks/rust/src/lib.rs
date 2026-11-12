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

//! Generated lightweight HTTP and SSE client for Gabby's versioned API.

use futures_util::StreamExt;
use reqwest::{header, Client as HttpClient, Response, Url};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Default)]
pub struct RunRequest {
    pub input: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub context: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub memory: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub metadata: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub host_context: Option<Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub include_trace: Option<bool>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct RunResponse {
    pub output: String,
    #[serde(default)]
    pub metadata: Value,
    pub trace_id: String,
    pub trace: Option<Value>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct StreamEvent {
    #[serde(rename = "type")]
    pub event_type: String,
    #[serde(default)]
    pub data: Value,
    pub event_id: Option<String>,
}

#[derive(Debug, Error)]
pub enum GabbyError {
    #[error("invalid base URL: {0}")]
    InvalidUrl(String),
    #[error("{error_type}: {message} (HTTP {status})")]
    Http { status: u16, error_type: String, message: String },
    #[error(transparent)]
    Transport(#[from] reqwest::Error),
    #[error("invalid SSE event: {0}")]
    Sse(#[from] serde_json::Error),
}

#[derive(Clone)]
pub struct Client {
    http: HttpClient,
    base_url: Url,
    agent_name: String,
    bearer_token: Option<String>,
}

impl Client {
    pub fn new(base_url: &str, agent_name: impl Into<String>) -> Result<Self, GabbyError> {
        let url = Url::parse(base_url).map_err(|err| GabbyError::InvalidUrl(err.to_string()))?;
        let host = url.host_str().unwrap_or_default();
        let loopback = matches!(host, "localhost" | "127.0.0.1" | "::1");
        if !(url.scheme() == "https" || (url.scheme() == "http" && loopback))
            || url.username() != ""
            || url.password().is_some()
            || url.query().is_some()
            || url.fragment().is_some()
        {
            return Err(GabbyError::InvalidUrl(
                "use HTTPS outside loopback and omit credentials, query, and fragment".into(),
            ));
        }
        let agent_name = agent_name.into();
        if agent_name.trim().is_empty() {
            return Err(GabbyError::InvalidUrl("agent name must not be empty".into()));
        }
        Ok(Self {
            http: HttpClient::new(),
            base_url: url,
            agent_name,
            bearer_token: None,
        })
    }

    pub fn with_bearer_token(mut self, token: impl Into<String>) -> Self {
        self.bearer_token = Some(token.into());
        self
    }

    fn endpoint(&self, action: &str) -> Url {
        let mut url = self.base_url.clone();
        {
            let mut segments = url.path_segments_mut().expect("HTTP URL is hierarchical");
            segments.pop_if_empty();
            segments.push("v1").push("agents").push(&self.agent_name).push(action);
        }
        url
    }

    fn request(&self, action: &str, body: &RunRequest) -> reqwest::RequestBuilder {
        let request = self.http.post(self.endpoint(action)).json(body);
        match &self.bearer_token {
            Some(token) => request.bearer_auth(token),
            None => request,
        }
    }

    pub async fn run(&self, body: &RunRequest) -> Result<RunResponse, GabbyError> {
        let response = self.request("run", body).send().await?;
        if !response.status().is_success() { return Err(decode_error(response).await); }
        Ok(response.json().await?)
    }

    pub async fn stream(
        &self,
        body: &RunRequest,
        idempotency_key: Option<&str>,
        last_event_id: Option<&str>,
    ) -> Result<impl futures_util::Stream<Item = Result<StreamEvent, GabbyError>>, GabbyError> {
        let mut request = self.request("stream", body).header(header::ACCEPT, "text/event-stream");
        if let Some(key) = idempotency_key { request = request.header("Idempotency-Key", key); }
        if let Some(id) = last_event_id { request = request.header("Last-Event-ID", id); }
        let response = request.send().await?;
        if !response.status().is_success() { return Err(decode_error(response).await); }
        Ok(parse_sse(response))
    }
}

async fn decode_error(response: Response) -> GabbyError {
    let status = response.status();
    let value = response.json::<Value>().await.unwrap_or(Value::Null);
    let detail = value.get("detail").unwrap_or(&value);
    GabbyError::Http {
        status: status.as_u16(),
        error_type: detail.get("error_type").and_then(Value::as_str).unwrap_or("HTTPError").into(),
        message: detail.get("error").and_then(Value::as_str).unwrap_or(status.canonical_reason().unwrap_or("request failed")).into(),
    }
}

fn parse_sse(response: Response) -> impl futures_util::Stream<Item = Result<StreamEvent, GabbyError>> {
    async_stream::try_stream! {
        let mut source = response.bytes_stream();
        let mut buffer = Vec::<u8>::new();
        while let Some(chunk) = source.next().await {
            buffer.extend_from_slice(&chunk?);
            while let Some((boundary, delimiter_len)) = sse_boundary(&buffer) {
                let block = buffer.drain(..boundary + delimiter_len).collect::<Vec<_>>();
                if let Some(event) = parse_sse_block(&block)? { yield event; }
            }
        }
        if !buffer.is_empty() {
            if let Some(event) = parse_sse_block(&buffer)? { yield event; }
        }
    }
}

fn sse_boundary(buffer: &[u8]) -> Option<(usize, usize)> {
    let lf = buffer.windows(2).position(|pair| pair == b"\n\n").map(|index| (index, 2));
    let crlf = buffer
        .windows(4)
        .position(|pair| pair == b"\r\n\r\n")
        .map(|index| (index, 4));
    match (lf, crlf) {
        (Some(left), Some(right)) => Some(if left.0 < right.0 { left } else { right }),
        (Some(value), None) | (None, Some(value)) => Some(value),
        (None, None) => None,
    }
}

fn parse_sse_block(block: &[u8]) -> Result<Option<StreamEvent>, GabbyError> {
    let text = String::from_utf8_lossy(block);
    let mut data = Vec::new();
    let mut id = None;
    for line in text.lines() {
        if line.is_empty() || line.starts_with(':') { continue; }
        let (field, value) = line.split_once(':').unwrap_or((line, ""));
        let value = value.strip_prefix(' ').unwrap_or(value);
        match field { "data" => data.push(value), "id" => id = Some(value.to_owned()), _ => {} }
    }
    if data.is_empty() { return Ok(None); }
    let mut event: StreamEvent = serde_json::from_str(&data.join("\n"))?;
    if event.event_id.is_none() { event.event_id = id; }
    Ok(Some(event))
}
