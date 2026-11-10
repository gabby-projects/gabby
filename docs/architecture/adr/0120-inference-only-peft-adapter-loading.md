# ADR 0120: Model adapter loading boundary

- Status: superseded
- Date: 2026-10-03

The previously accepted model adapter loading capability has been removed. Gabby does not train
models, modify model weights, or load model adapters. It gives agents a requested character by
applying user-defined instructions through the AI enforcer and governed runtime pipeline. See
[ADR 0121](0121-runtime-specialization-boundary.md).
