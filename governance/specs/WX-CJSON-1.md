# WX-CJSON-1: Canonical JSON Profile

**Status:** SPECIFIED + IMPLEMENTED (`weaver_contracts.canonical`)
**Evidence:** R2[self] (implementation plus origin-controlled tests in this repository)
**Authority:** O0
**Outline step:** 2 (§5.1)

## Definition

WX-CJSON-1 is [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785) (JSON Canonicalization
Scheme) restricted so that independent implementations cannot disagree on numbers:

| Rule | Reason |
|---|---|
| Values: object (string keys), array, string, integer, `true`, `false`, `null` | Floats need ES6 number formatting, a common source of cross-runtime mismatch |
| Integers in `[-(2^53-1), 2^53-1]` | The I-JSON safe range. Larger integers lose precision in JavaScript and other double-based runtimes |
| Strings are valid Unicode; no lone surrogates | They cannot be encoded as UTF-8 |
| Object keys sorted by UTF-16 code units | RFC 8785 §3.2.3 |
| String escaping exactly as RFC 8785 §3.2.2.2 | `\"`, `\\`, `\b \f \n \r \t`, other controls as lowercase `\u00xx`; all else literal UTF-8 |
| No whitespace | RFC 8785 |

The strict reader (`parse_strict`) additionally rejects duplicate keys, a byte-order mark,
invalid UTF-8, exponents, `NaN`/`Infinity`, and trailing data.

A digest under this profile is `sha256(canonicalize(value))`, written as 64 lowercase hex digits.

## Conformance vectors

`packages/contracts/weaver_contracts/vectors/wx_cjson_1.json` contains:

- **19 valid vectors** (input text → canonical text → SHA-256), covering escapes, Unicode,
  UTF-16 key order, safe-integer bounds, nesting, and whitespace removal;
- **14 reject vectors** (input bytes as hex → expected rejection reason).

Every valid vector is checked against **two implementations** in `tests/contracts/test_canonical.py`:
this repository's reference, and the independent `rfc8785` 0.1.4 package (Trail of Bits).
They agree on all 19.

Any other runtime claiming WX-CJSON-1 must reproduce all 19 canonical outputs byte for byte
and reject all 14 reject vectors.

## Legacy serializers (C-CANON-001)

Weaver code that hashes or signs JSON mostly uses `json.dumps(..., sort_keys=True)` rather than a
canonical profile. **Correction:** step 2 of the outline listed three such serializers. A
repository-wide search in step 4 found about a dozen. The full inventory is in
`governance/CONTRADICTIONS.yaml` under `C-CANON-001`. They fall into two classes:

| Class | Diverges on | Cause | Examples (pinned in tests where importable) |
|---|---|---|---|
| `ensure_ascii=False` | `V12-key-order-utf16` | Keys sorted by code point, not UTF-16 code units | `weaver_verifier.crypto.canonicalize_json`, `triadic_controls.ledger.canonical_json`, `tools.mathos_bench…canonical_json` |
| default `ensure_ascii=True` | V09–V13, V17 | Every non-ASCII character escaped as `\uXXXX`, plus the same key order | `tools.spine_hash.canonical`, `weaver_verifier.claim_transition._canonical_bytes`, `witness_py/sign_attestation.py`, release-guard provenance, and others |

All of them produce identical bytes for integer-only data in which every string, keys and values
alike, is ASCII. MathOS bench data and triad ledger events contain floats, so their digests are
outside WX-CJSON-1 entirely.

None of them is **changed** by the outline steps so far, because their digests and signatures are
pinned in existing fixtures and receipts. `tests/contracts/test_canonical.py` pins the five
importable divergence sets, and a guard test fails if a pinned entry has no test.
`tools/check_trust_domains.py` rejects any new `json.dumps(sort_keys=True)` under `packages/`
outside a three-file allowlist. Migrating or freezing each one is open as `C-CANON-001`.

`PG001R-JSON-1` (Lumen-Nexus) remains a separate, named diagnostic profile for PG-001R fingerprints.
