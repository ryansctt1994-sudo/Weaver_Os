# Revised RTL/packet publication receipt — 2026-11-06

**Revised source publication verified; silicon E3.1 remains NOT_READY.**
This is an author-issued source checkpoint, not a vendor bitstream/build checkpoint,
physical observation, outside witness receipt, public witness quorum or production
authorization. All missing physical/independence claims remain explicitly false.

## Exact subject and public receipt

- Repository: `ryansctt1994-sudo/cathedral-verified`
- Source commit: `0f3b0973b95ecbadb49ca4f7d989ed1da8a2f6b9`
- Git tree: `b65401d12826ec3fe62c929982c588f51b055be9`
- Packet checksum-list SHA-256: `d668739d2db6c219a7bb6373807254f800434195f8a835ba38e67aba53bea8bd`
- Checkpoint SHA-256: `b0439f7d0878dd8d888bd7fde2dc37baca645829d10e999609c79b38a3018332`
- Rekor global index: **3721019269**; integrated at **2026-11-06T16:13:28Z**
- [Public entry](https://rekor.sigstore.dev/api/v1/log/entries/108e9186e8c5677a6cfe12dcdf288a3e1048689ef22977bed7d3880e55f77c74a740b8967e26296b)

The source manifest binds 34 source/packet/evidence/license files, including all
30 files named by the packet checksum list and that list itself. The appended
Chronicle entry additionally binds the source manifest (35 artifact bindings).
The existing failure trace, startup fix, unfilled witness forms and author-run
simulation/mapping results are preserved. These are not new physical observations.

The original one-entry Chronicle is retained byte-for-byte as the prefix of the
two-entry ledger. The previous checkpoint and its Rekor proof remain in `previous/`.
The same author key signed both checkpoints; this establishes key continuity,
not independent custody. The original Rekor index **3719860200** is unchanged.
Publication timestamps bound when a digest was logged; they do not measure an
actual hardware event or provide an independent timing receipt.

## Reproduce offline verification

First verify `revised-bundle.sha256` against `revised-bundle.zip` using the published
immutable repository commit, then extract into a new directory. With Python 3.10+
and `cryptography==50.0.0` installed in a dedicated virtual environment:

```sh
python verify_revision.py \
  --checkpoint-sha256 b0439f7d0878dd8d888bd7fde2dc37baca645829d10e999609c79b38a3018332 \
  --source-commit 0f3b0973b95ecbadb49ca4f7d989ed1da8a2f6b9
```

Use the digest/source pin from a trusted publication reference, not merely from
an incoming bundle. The helper verifies both original and revised log inclusion,
author signatures/key continuity, signed entry timestamps, pinned log key and signed
checkpoints, retained public readback, exact original Chronicle prefix, chain/head/
Merkle roots, source inventory and all packet file hashes. Its imported verifier
and Chronicle code are themselves included among the pinned source artifacts.
Expected result: `VERIFIED_REVISED_SOURCE_PUBLICATION`, with `silicon_E3_1=NOT_READY`.
The helper/packaging are supplied in this follow-up; they are not misrepresented
as files in the earlier source commit or circularly covered by this checkpoint.

`python verifier_mutations.py` checks five synthetic mutations in a temporary copy:
changed RTL, altered original ledger prefix, changed checkpoint metadata, corrupted
original log signature and corrupted new readback signature. All five rejected;
unchanged evidence verified before and afterward. These are author-run verifier
checks and a limited coverage estimate, not independent witnessing.

`interlock-gate.json` records the actual existing Weaver gate against this new
bundle and local test SQLite state. It verified external inclusion, Chronicle/
artifacts and existing replay state, then returned **NOT_READY, exit 2**, because
external authority policy/physical receipts remain unconfigured. The current
Weaver gate still does not enforce the proposed public quorum or timing protocol.

## Trust limits and remaining work

The pinned Rekor log key was matched to the current service key and previously
retrieved official Sigstore trusted-root metadata over HTTPS. Full TUF-chain
verification was not performed. An initial pre-submit comparison encountered the
API's JSON-encoded PEM; decoding it and comparing the DER key digest confirmed the
same pinned key. No entry was posted until that check passed.

Chronicle prefix continuity and both inclusion proofs were verified. A Rekor
Merkle-tree consistency proof between the two signed checkpoints was **not**
verified; no fork-immunity or future availability guarantee is claimed. No
outside person was contacted, enrolled, or claimed to have observed hardware.

The immutable reproduction packet described a new source anchor as pending when
written. This receipt completes that source-publication step without editing the
packet's frozen bytes. A later Vivado-produced bitstream, its reports, fixture,
physical measurements/video and independent receipts still need their own new
checkpoints. Do not reuse this source-only anchor as evidence for future bytes.

No board was programmed or flashed, no physical measurement occurred, no outside
reproduction or public quorum exists, and permanent irreversibility is absent.
Production authority remains unearned.
