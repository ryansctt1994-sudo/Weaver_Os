# Risk: governance.claim_audit

**Risk level:** low. Deterministic and read-only.

| Concern | Boundary |
|---|---|
| Writes | Only the JSON report, and only when `--json` is given. |
| Execution | Runs `git ls-files` and `git rev-parse` in the target. Runs no code from the target. |
| Network | None. |
| Secrets | None needed. File contents appear in findings as snippets of up to 240 characters, so keep reports from private repositories private. |
| Large or binary files | Skipped: files over 2 MB, or with a NUL byte in the first 8 KB, or not valid UTF-8. |

**Main residual risk:** a false denial lets a real claim pass (see SKILL.md, Failure Modes). The audit supports human review; it does not replace it. A passing audit grants no authority to anything.
