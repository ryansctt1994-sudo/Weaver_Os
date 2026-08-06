# MVP-0 Replay Checklist

Status: ROADMAP / NEXT AUTHORITY UPGRADE

MVP-0 is the minimum end-to-end run required to move the repository from architecture and component evidence toward replayable governance evidence.

## Required Flow

```text
Proposal
  -> Gate
  -> Chronicle append
  -> Receipt generation
  -> Replay verifier
  -> Negative fail-closed test
```

## Required Properties

- Deterministic input fixture.
- Canonical JSON serialization.
- Stable content hash.
- Append-only Chronicle event.
- Receipt bound to Chronicle head.
- Replay verifier reconstructs the same verdict.
- Invalid proposal fails closed.
- Replay mutation or hash tampering is detected.
- Test can run from a clean checkout with documented commands.

## Acceptance Criteria

| Criterion | Required Evidence |
|---|---|
| Clean install | Command transcript or CI log. |
| Positive path | Proposal admitted only after gate pass. |
| Negative path | Invalid proposal rejected without Chronicle authority promotion. |
| Receipt binding | Receipt includes or binds to payload hash, policy version, and Chronicle head. |
| Replay equivalence | Replay reproduces verdict and detects tampering. |
| Evidence capture | Logs, hashes, and test output preserved. |
| Independent replay readiness | One command or documented script for external runner. |

## Non-Goals

- Production readiness.
- Hardware enforcement.
- Full witness federation.
- Formal proof completion.
- UI integration.
- Mythic or symbolic artifact execution.

## Promotion Boundary

Passing MVP-0 may justify upgrading the specific MVP-0 path to L3 if run in CI. It does not upgrade the broader Cathedral Mesh to L4 or L5. L4 requires independent replay outside the originating environment.

## Suggested Command Target

```bash
python -m pytest tests/test_mvp0_replay.py
```

If a different test path is used, update this checklist and the registry in the same commit.
