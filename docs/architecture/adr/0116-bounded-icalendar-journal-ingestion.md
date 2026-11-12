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

# ADR 0116: Bounded iCalendar journal ingestion

- Status: Superseded by ADR 0125
- Date: 2026-10-03

## Context

`ICalendarTextParser` supports events and task records. iCalendar `VJOURNAL` components hold
time-stamped journal text, which can provide useful source material for research and knowledge
agents but is currently ignored.

## Decision

Extend the parser to index direct-child `VJOURNAL` components as cited pages in source order. Render
summary, start time, description, status, organizer, and attendee values when present; expose journal
UID, start, status, attendees, and per-file journal ordinal through `calendar_journal_*` metadata.
Use an independent `max_journals` limit. Preserve the existing event and task behavior. Dates remain
in their original RFC 5545 representation, and nested subcomponents remain excluded.

## Consequences

- Journal entries become independently searchable and filterable in supported knowledge stores.
- Event and task metadata and page behavior remain unchanged.
- `VFREEBUSY`, recurrence expansion, timezone conversion, and attendee parameter interpretation
  remain outside the parser's contract.

## Alternatives considered

- Treat journal components as unknown data. Rejected because their bounded text fields fit the
  existing cited-page and metadata model.
- Add a third-party calendar library. Deferred because extracting these fields does not require
  recurrence or timezone interpretation.
