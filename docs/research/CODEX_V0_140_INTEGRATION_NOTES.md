# Codex v0.140 Integration Notes for Weaver

## Status

This document extracts operationally useful ideas from the Codex v0.140 changelog and maps them into the Weaver Governance Runtime roadmap.

It does not claim implementation.

Current Weaver status remains:

```text
E2_READY_FOR_E3
E3_NOT_CLAIMED
AUTHORITY_NOT_EARNED
PRODUCTION_PROHIBITED
CLINICAL_PROHIBITED
```

## Useful Items to Integrate

### 1. Usage Visibility

Codex added `/usage` views for daily, weekly, and cumulative token activity.

Weaver integration:

- Add receipt activity summaries.
- Track receipt generation count by day/week/all-time.
- Track validation runs, failed receipts, replay attempts, and witness attempts.

Possible Weaver command later:

```text
weaver usage
```

Minimum useful metrics:

- total receipts emitted
- PASS receipts
- FAIL receipts
- replay receipts
- witness receipts
- authority-review receipts
- latest evidence level

### 2. Goal Preservation for Oversized Text and Attachments

Codex improved `/goal` preservation for large text blocks and image attachments.

Weaver integration:

- Preserve oversized governance objectives as artifacts rather than truncating them.
- Hash large pasted claims or external attachments before admissibility review.
- Store source references in Chronicle or manifests before summarization.

Governance rule:

> Long input must be preserved or hashed before compression.

### 3. Permanent Session Deletion

Codex added permanent session deletion with confirmation safeguards and subagent cleanup.

Weaver integration:

- Add explicit deletion policy for local sessions, failed receipts, diagnostic logs, and imported external-agent state.
- Separate deletion of working artifacts from deletion of governance receipts.
- Require confirmation for deleting receipts or witness artifacts.

Open design point:

- Receipts may need immutable retention once used for promotion.
- Failed diagnostic artifacts may be deletable before promotion if not referenced.

### 4. External Agent Import

Codex added `/import` for Claude Code setup, project configuration, and recent chats.

Weaver integration:

- Treat imports as untrusted external lineage.
- Imported setup/configuration must enter through OMEGA admissibility.
- Imported chat/history must be tagged as `external_agent_import` and not treated as evidence until verified.

Possible import receipt fields:

```json
{
  "source_agent": "claude_code",
  "import_scope": "setup|config|recent_chats",
  "lineage_status": "imported_unverified",
  "authority_earned": false
}
```

### 5. Unified Mentions for Files, Plugins, and Skills

Codex unified `@` mentions across files, plugins, and skills.

Weaver integration:

- Design a unified reference resolver for artifacts.
- Allow receipts, manifests, schemas, and governance docs to be referenced uniformly.

Possible syntax:

```text
@receipt:gate1
@manifest:source-pre-gate
@schema:receipt
@layer:omega
@doc:constitutional-invariants
```

### 6. Managed Credential Storage

Codex added managed Bedrock API-key authentication and encrypted local storage for CLI/MCP OAuth credentials.

Weaver integration:

- Secrets must never appear in receipts.
- Credentials should be represented through hashes, key IDs, or redacted auth-mode metadata.
- Receipt environment capture should explicitly exclude secret values.

Required invariant:

```text
RECEIPT_MUST_NOT_LEAK_SECRETS
```

### 7. SQLite State Recovery

Codex added automatic recovery from corrupted SQLite state databases.

Weaver integration:

- Chronicle or receipt state stores should support corruption detection, backup, and rebuild from append-only rollout/receipt data.
- Rebuild should itself emit a recovery receipt.

Possible receipt type later:

```text
state_recovery
```

### 8. Review Cancellation Safety

Codex fixed `/review` crash behavior while preserving queued guidance.

Weaver integration:

- Cancelled promotion reviews should preserve queued reviewer guidance as non-authoritative context.
- Cancellation must not silently delete review context if it influenced later decisions.

### 9. MCP Reliability and Disabled Server Preservation

Codex improved MCP reliability with retries, credential-state reporting, and disabled-server preservation.

Weaver integration:

- Connector/tool failures should be classified as transient, auth failure, disabled, or unusable.
- Disabled external tools must not silently reactivate during validation.
- External witness tools require explicit availability state in receipts.

### 10. Remote Plugin Auth Requirements

Codex fixed remote plugin auth surfacing.

Weaver integration:

- Any external plugin/tool used during validation must declare auth requirements.
- Missing auth should fail closed before evidence generation.

### 11. Background Command Interruption

Codex allows interrupting non-TTY background commands while preserving final output and exit status.

Weaver integration:

- Interrupted validation runs should still produce FAIL receipts with partial logs and exit/interruption status.
- This directly maps to Gate 1 hardening already added.

Receipt addition later:

```json
{
  "interrupted": true,
  "partial_output_preserved": true
}
```

### 12. Large Repository and Long Session Performance

Codex improved responsiveness through fsmonitor preservation, avoiding duplicate history reads, archive lookup acceleration, and diff rendering cache.

Weaver integration:

- Manifest generation should avoid expensive duplicate scanning.
- Consider Git-aware source manifests using tracked files only.
- Cache source manifests by commit SHA.
- Avoid hashing logs/receipts into source manifests.

Current relevance:

The Gate 1 receipt generator now separates source manifest generation from receipts/logs.

### 13. Realtime Voice Removal

Codex removed experimental realtime voice controls and audio dependencies.

Weaver integration:

- Avoid optional interaction features that expand dependency surface before validation.
- Keep Weaver CLI narrow until receipt discipline is stable.

## Proposed Weaver Backlog Items

### High Priority

1. Add receipt activity summary command.
2. Add source-manifest generation using Git tracked files.
3. Add FAIL receipt preservation for interrupted validation runs.
4. Add explicit secret-redaction invariant to receipt schema/docs.
5. Add external-agent import policy under OMEGA.

### Medium Priority

1. Add state recovery receipt design.
2. Add unified artifact reference syntax.
3. Add tool/auth availability fields to witness receipts.
4. Add deletion and retention policy for logs, failed receipts, and promoted receipts.

### Defer

1. Plugin system expansion.
2. Remote app integration.
3. Voice or rich interaction controls.
4. Large multi-agent orchestration.

## Integration Rule

Codex operational features should be integrated only when they improve Weaver's evidence discipline:

```text
observability
reconstructability
receipt preservation
secret safety
state recovery
import provenance
auditability
```

They should not be integrated merely because they are available.
