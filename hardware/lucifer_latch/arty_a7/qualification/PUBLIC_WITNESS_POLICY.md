# Public witness policy v1 — pending enrollment

**Configured witnesses: zero. Observed outside reproductions: zero. Public witness
quorum: NOT_READY.** The Rekor service is a publication authority, not an observer
of a board. Author-run CI and new keys under the same principal do not count.

This packet proposes a concrete admission policy: **two of three pre-enrolled
outside witnesses**, with the two counted affirmative signers each having directly
reproduced the silicon protocol on independently controlled benches. The procedure
and original RTL authors, target operator and their controlled agents/keys cannot
be counted as those outsiders. A reader who only reviews text is valuable but
cannot sign a direct physical execution claim. No signer is enrolled by this file.

Before any qualifying run, publish a roster of three named controlling principals,
Ed25519 public keys, custody statements, conflicts, public receipt locations and a
key-revocation policy. Pin the exact roster bytes/hash through an external channel
and public append-only checkpoint. Actual owners must approve their participation;
the author cannot assign them keys. A roster change is a dated amendment requiring
new review, not retrospective replacement of a dissenter. One principal gets at
most one vote, regardless of machines, organizations' account aliases or agents.

Each physical run also needs a timing witness whose capture equipment, timebase
and signing key are controlled independently from its operator and attack host.
A roster member may time-witness another member's run; they may not call timing
captured on their own attack host independent. Disclose shared power, network,
clock, premises and employment/control relationships. Identity/custody claims need
external substantiation; public keys alone cannot establish independence.

## Bind without circular receipts

1. **Build checkpoint B:** anchor the protocol/roster/fixture hashes, source inputs,
   vendor bitstream digest and reports before the run. Each independent rebuild
   gets its own digest and checkpoint; bind the exact build that each board used.
2. **Run evidence R:** timing witness issues a signed fresh challenge, then signs
   a receipt binding B, challenge, run ID, raw-trace/video manifest digest, timing
   uncertainty, observation scope and exclusions. The physical operator signs their
   direct-execution statement separately. Their private keys never enter the
   attack host or this author workspace.
3. **Results checkpoint C:** append raw-evidence manifests and exact signed receipts
   to Chronicle and publish a new anchor. Include prior checkpoint identity and a
   verifiable consistency link; preserve the earlier candidate and every failure.
4. **Quorum votes Q:** outsiders sign the same C and roster digest, their own run
   IDs/build checkpoints, coverage crosswalk, unresolved findings and bounded claim.
   Publish signatures and raw receipt bytes at independently controlled public
   locations, then anchor their digest set. Do not hash a receipt inside a
   checkpoint the same receipt is supposed to sign.

Timing template signature domain is `LUCIFER-TIMING-RECEIPT-v1\n`; outsider vote
uses `LUCIFER-PHYSICAL-WITNESS-v1\n`. Here `\n` means one LF byte. Sign Ed25519 over
the domain followed by UTF-8 JSON of `payload`, sorted keys, compact separators,
ASCII escapes, no nonfinite numbers or duplicate keys. Signature is strict base64.
Publish the exact payload bytes and name who independently recomputed each hash.
These are new collection formats, **not** interchangeable with Weaver's existing
`WEAVER-SILICON-EVIDENCE-v1` role receipts; no verifier for these new quorum formats
is implemented by this documentation change.

## Admission and limits

A human evidence adjudicator, named and conflict-disclosed before the run, checks
identity/custody, signature domains, all bindings, public availability, raw timing
and video continuity, observer noninterference, positive controls, coverage and
fixture equivalence. Missing evidence leaves NOT_READY; ambiguous measurements
remain INCONCLUSIVE. A confirmed contradictory result cannot be outvoted into a
clean result. Retain it and resolve/reproduce the cause under a dated amendment.
Two affirmative direct-reproduction votes with no unresolved material finding make
the packet eligible for E3.1 review, not automatically approved for production.

A 2-of-3 attestation threshold is not Byzantine fork-proof consensus: conflicting
quorums can intersect only in an equivocating signer. Publish/gossip checkpoints,
reject detected conflicting histories and retain revocations. Do not claim
fork immunity, guaranteed availability, or guaranteed correctness. A stronger
fault model requires a separately designed consistency/quorum protocol.

Weaver's current software gate checks two declared role receipts and can return
READY_FOR_E3_1_REVIEW without implementing this public-quorum/timing protocol.
That result alone is insufficient under this policy. Human release review remains
blocked until public receipts and independent physical reproductions are verified;
production authority stays false. No existing software output may be relabeled
as an E3.1 award.
