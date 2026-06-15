# Environment Manifest

## Purpose

This file defines the minimum environment assumptions for review.

## Required environment

- Operating system: documented and stable
- Shell: POSIX-compatible or equivalent
- Hashing tool: SHA-256 capable
- Text editor or viewer: Markdown and JSON capable
- Optional: Python or equivalent for scripted validation

## Toolchain assumptions

- File hashing must be reproducible.
- Log inspection must be possible.
- Manifest parsing must be possible.
- No privileged access is assumed.

## Dependencies

All runtime or tool dependencies should be listed here with pinned versions if applicable.

If a dependency is external, the package must state whether it is required for viewing only, replay, verification, or optional inspection.

## Hardware assumptions

State any assumptions about CPU architecture, memory minimums, storage needs, accelerator requirements, or simulation-only conditions.

## Environment rule

If the reviewer environment diverges materially from this manifest, the reviewer must note the divergence and treat the result as conditional.

## Status

This manifest documents the declared environment only. It does not itself establish external replication.
