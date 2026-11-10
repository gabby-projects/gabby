# Host approval and audit

Gabby pauses a sensitive tool call and asks the injected `ApprovalHandler` for a decision. The
application owns reviewer identity, notification, UI, database path, retention, and access controls.
Approval decisions are transient and scoped to one tool call; Gabby does not retain them as agent
memory.

## Select an audit backend

`ApprovalAuditSink` is the async extension contract for durable decisions. `SQLiteApprovalAudit` is
the bundled single-host implementation, and `AuditedApprovalHandler` composes any sink with the
host's asynchronous review callback:

```python
from gabby import AuditedApprovalHandler, SQLiteApprovalAudit

audit = SQLiteApprovalAudit("./private/approvals.sqlite3")
approval_handler = AuditedApprovalHandler(review_in_my_app, audit)
agent = Agent.from_file("agent.yaml", approval_handler=approval_handler)
```

The helper records the run and call IDs, agent and tool names, decision, timestamp, and SHA-256 of
the canonical JSON arguments. It does not persist raw arguments. Principal subjects are omitted by
default; set `include_principal_subject=True` only when the application's audit policy needs them.
Argument serialization is capped at 1 MiB by default, audit calls run outside the event loop, and
audit write failures propagate as a sanitized approval failure so the tool does not execute. Reads
are asynchronous and limited to 1,000 records per call. Invocation IDs and names are bounded before
storage; oversized or non-JSON arguments fail closed.

The database remains host-owned. The application must set filesystem permissions, choose retention
and backup policies, and restrict access. This is a local single-host SQLite option.

The sink implements `ApprovalAuditSink` and must finish recording before returning. If it
raises or times out, Gabby fails closed and does not execute the tool. The host remains responsible
for backend durability, idempotency, availability, retention, and access control.
`AuditedApprovalHandler` does not catch backend exceptions; Gabby's runtime turns them into a
sanitized approval-unavailable tool failure.

See [the runnable example](../examples/approval_audit.py),
[the approval decision](architecture/adr/0025-host-owned-tool-approval.md), and
[ADR 0093](architecture/adr/0093-reusable-sqlite-approval-audit.md) and
[ADR 0102](architecture/adr/0102-approval-audit-sink-contract.md).
