# ADR 0121: Runtime specialization boundary

- Status: accepted
- Date: 2026-11-10

## Decision

Gabby gives an agent its requested character through user-defined instructions, enforced by the AI
enforcer within policies, tools, knowledge, approvals, verification, and execution pipelines. It does
not train models, modify model weights, or load model adapters.

## Rationale

Agent character and behavior belong in explicit, inspectable runtime configuration and governance
rules. This keeps Gabby's responsibility focused on enforcing those choices while executing the
configured agent request.
