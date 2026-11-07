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

## Legacy canonicalizers (C-CANON-001)

Running the vectors through Weaver's three existing canonicalizers found real differences:

| Canonicalizer | Diverging vectors | Cause |
|---|---|---|
| `triadic_controls.crypto.verifier.canonicalize_json` | `V12-key-order-utf16` | Sorts keys by code point, not UTF-16 code units. Only differs when keys mix astral-plane characters (e.g. emoji) with BMP characters at U+E000 or above |
| `tools.spine_hash.canonical` | V09, V10, V11, V12, V13, V17 | `ensure_ascii=True` escapes every non-ASCII character as `\uXXXX`, plus the same key-order difference |
| `tools.mathos_bench.mathos_bench_v0_1.canonical_json` | `V12-key-order-utf16` | Same as `triadic_controls`. It also accepts floats, which WX-CJSON-1 rejects |

All three produce identical bytes for integer-only data in which every string, keys and values
alike, is ASCII. A scan of every
committed `.json`/`.jsonl` file found that this holds everywhere **except MathOS bench**:
`mathos_bench_claimset_key_v0_1.json` and `mathos_bench_smoke_input_v0_1.json` contain non-ASCII
strings, and `mathos_bench_smoke_receipt_v0_1.json` contains floats. Those MathOS digests cannot be
reproduced under WX-CJSON-1 at all, because floats are out of profile.

None of the three is **changed** in this step, because their digests are pinned in existing
fixtures and receipts. The divergence sets are pinned in tests, so any
change in either direction shows up in review. Migrating them is open as `C-CANON-001`.

`PG001R-JSON-1` (Lumen-Nexus) remains a separate, named diagnostic profile for PG-001R fingerprints.
