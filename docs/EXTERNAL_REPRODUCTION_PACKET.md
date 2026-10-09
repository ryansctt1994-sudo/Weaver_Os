# External reproduction packet

**Classification:** local identity packet. Not an attestation.
**Pinned review head:** `e2232fcb2bb70e1535c43750429baa719fed815b` (PR #87).
**Dependency:** P0-006 commit `36b49fa8cd324e49f968ab65db3b443b31d565c4`.
**Authorization:** E2 ceiling / W0 / O0 WITHHELD / PRODUCTION PROHIBITED.

## What this packet is

`tools/emit_external_reproduction_packet.py` writes a canonical JSON record of:

- the pinned review commit and the observed HEAD,
- SHA-256 digests of the P0-007 producer, consumer, schema, and repair note,
- hosted workflow run identifiers, labelled `UNAUTHENTICATED_CLAIM`,
- the trust anchors that are still absent.

A matching local digest shows that this machine saw those bytes. It does not show that GitHub Actions produced them, that an independent witness signed them, or that a ruleset prevented a later rewrite.

## What this packet refuses

`--claim-witness` exits 2 and writes no packet. The tool has no key, no witness protocol, and no path that sets `authenticated_attestation` to true.

`--require-pinned-head` exits 1 unless the observed HEAD is the pinned review commit. A later commit that contains this tool is not that commit.

## Replay

```bash
python -m tools.emit_external_reproduction_packet \
  --root . \
  --observed-head "$(git rev-parse HEAD)" \
  --output verification-output/external-reproduction-packet.json
python -m pytest -q tests/test_external_reproduction_packet.py
```

Review the hosted checks on PR #87 at the pinned head. Do not treat this packet as a substitute for those checks, or as promotion evidence.

## Still withheld

- Independently authenticated witness.
- Effective branch and ruleset enforcement. A candidate ruleset is recorded in `docs/governance/MAIN_RULESET_EVALUATE.json`. GitHub rejected evaluate mode on the current plan (`Enforcement evaluate option is not supported on this plan`). Active enforcement was not created, because an unreviewed active ruleset could block `main` without an independent reviewer.
- Adjudication of the historical E3.5/E4 witness-policy version discrepancy.
- An external anchor against a coherent evidence-chain rewrite.
