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

# ADR 0023: Injectable event-by-event tracer

**Status:** Accepted by the project architect.  
**Date:** 2026-09-29.

## Context

Each execution already returns an `ExecutionTrace`, but applications cannot export events while a
run is in progress through a framework extension point. Core should support host-owned telemetry
without coupling the runtime to a vendor-specific telemetry SDK or storage service.

## Decision

- `Agent` accepts an optional async `Tracer` implementation. It receives structured `TraceEvent`
  snapshots in order within each run while the existing `ExecutionTrace` remains the run result.
  Events from concurrent runs may interleave; tracer implementations must support concurrent calls.
- Gabby does not include or configure a telemetry backend. The host owns tracer setup and lifecycle,
  credentials, transport security, storage, retention, and deletion.
- Each callback is bounded by the smaller of the run's remaining deadline and 250 ms. On the first
  timeout or exception, Gabby appends a sanitized `tracer_error` event to the local trace, disables
  that tracer for the rest of that run, and continues execution.
- Tracers receive a copy of each event so they cannot mutate the result trace. Events that have a
  duration expose it in the typed `duration_ms` field.

## Consequences

Event delivery is ordered and can add up to 250 ms per callback. A failing exporter does not fail an
agent run, but the trace exporter may receive only a prefix of that run's events. A host must treat
trace event data as potentially sensitive and implement its own filtering and retention policy.

## Alternatives considered

- Export only the complete trace after a run: simpler, but provides no live progress to external
  telemetry systems and misses the opportunity to persist events before an interrupted response.
- Bundle a vendor-specific telemetry SDK: provides an ecosystem, but couples the framework contract and
  dependency graph to one telemetry API and package stack.
- Fail the execution when tracing fails: guarantees telemetry completeness, but makes an optional
  observability integration an availability dependency for agent work.
