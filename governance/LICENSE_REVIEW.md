# License Review for the Consolidation

**Status:** FACTUAL REVIEW, 2026-11-07 — D4 decided by [GD-0001](decisions/GD-0001.md): **path A**
**Not legal advice.** This records what the repositories contain. It does not give an opinion
that would replace counsel.

## What each source repository declares

| Repository | License file | Declared in metadata | Commit authors (all history) | GitHub fork? |
|---|---|---|---|---|
| `Weaver_Os` | MIT, "Copyright (c) 2026 Ryan Scott" | MIT (README) | owner account | no |
| `cathedral-verified` | MIT, "Copyright (c) 2026 ryansctt1994-sudo" | MIT (README) | owner account | no |
| `Lumen-Nexus` | MIT, "Copyright (c) 2026 ryansctt1994-sudo" | MIT (README) | owner account | no |
| `Lumen-Elpis` | MIT | MIT (README) | owner account | no |
| `Lumen` | **Apache-2.0** | `pyproject.toml`: `license = Apache-2.0`, `authors = Ryan Scott` | 50/50 commits by the owner account | **yes**, parent `symmindprotocol618-dev/Lumen` |

## Runtime third-party dependencies

| Dependency | Used by | License |
|---|---|---|
| `cryptography` | Weaver | Apache-2.0 OR BSD-3-Clause |
| `jsonschema` | Weaver | MIT |
| `PyJWT` | Weaver | MIT |
| (standard library only) | Lumen, Lumen-Nexus, cathedral-verified | — |

All of these can be combined with an MIT-licensed repository. Nothing here is copyleft.

## The one open point: Lumen

Apache-2.0 code **can** live inside an MIT repository. It just has to keep its Apache terms:
the license text, any NOTICE (Lumen has none), and a note on files that were changed.

Two paths:

- **A — Keep Apache-2.0 on moved Lumen files.** Add `LICENSES/Apache-2.0.txt`, put an
  `SPDX-License-Identifier: Apache-2.0` header on each moved file, and note modifications.
  This needs no further facts and is always safe.
- **B — Relicense the moved Lumen code to MIT.** Only the copyright holder(s) can do this.
  Every commit in this repository is by the owner account, which points to the owner
  holding the copyright. But GitHub lists `symmindprotocol618-dev/Lumen` as the parent.
  Before taking B, confirm that the parent contributed no code that survives in the moved
  files, or get its holder's agreement.

**Recommendation:** use A for the first moves. It is reversible: B can be applied later
once the parent relationship is confirmed. A cannot be undone the other way round without
the same confirmation.

## Attribution regardless of path

Moved files carry a short provenance line (`Moved from ryansctt1994-sudo/<repo>@<sha>`),
and the source repositories are archived read-only, not deleted, so their history stays
available as evidence (outline §7).
