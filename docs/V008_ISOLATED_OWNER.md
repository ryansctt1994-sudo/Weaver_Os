# WEAVER-V008, first slice: separately privileged resource owner

Status: research prototype on top of the PR #125 review baseline. HOLD is unchanged. This
slice adds a two-process topology and an adversarial acceptance suite. It does not close V008,
promote any evidence class, or authorise any deployment.

## What changed

PR #125 proved a bounded signed write inside one process. Its strict `xfail`
(`test_v008_direct_sqlite_bypass_must_be_denied_by_os`) records that a same-uid process can
edit the SQLite file directly. That test and its meaning are left as they were: the
in-process owner still has no isolation.

This slice adds a second topology in which the owner is its own OS principal.

```
requester (uid R)  --Unix socket-->  owner service (uid O)  -->  SQLite in a 0700 directory owned by O
       |                                   |
 proposal + signed grant            kernel-reported peer uid (SO_PEERCRED)
 only; no config, no key            decides who may even be read
```

| File | Role |
|---|---|
| `packages/runtime/weaver_runtime/owner_ipc.py` | Strict frames, `SO_PEERCRED` reader, `assert_trusted_path`, `OwnerClient` |
| `packages/runtime/weaver_runtime/owner_service.py` | `OwnerService` wrapping `ProtectedWriteOwner`; `FileVeto` |
| `packages/runtime/weaver_runtime/owner_main.py` | Hardened launcher (refuses root, inherited descriptors, loose config) |
| `tests/test_owner_ipc.py` | Unprivileged unit tests, run in every CI job |
| `tests/isolation/test_v008_isolated_owner.py` | Cross-uid acceptance tests, need root |
| `tools/check_v008_mutations.py` | 15 control removals the tests must catch, needs root |
| `.github/workflows/v008-isolation.yml` | Runs the two root-only items with skipping turned into failure |

## Declared attacker model

An unprivileged local user on the same host. They can run any code under their own uid, know
every path and the wire protocol, and may be a listed requester or an unlisted user.

Out of scope: root, the owner uid, kernel and hypervisor bugs, hardware, a compromised trusted
launcher, a compromised issuer signing key, and any network attacker.

## Controls and the tests that exercise them

| Control | Acceptance test |
|---|---|
| Owner and database run as a different uid; database directory is 0700 | requester cannot read, append, list, create, rename, or open the database or WAL; original V008 bypass script exits non-zero |
| Peer uid from the kernel decides access; the default is deny | a valid signed grant from an unlisted uid commits nothing and the owner keeps serving |
| Each peer uid may speak only for listed actor ids | listed uid proposing as another actor is refused |
| Trust root comes only from the owner-private config | grant signed by an untrusted key is rejected; requester cannot write the config or the code |
| Client checks the server's uid before sending | a server under another uid receives zero bytes |
| Socket path chain cannot be rewritten by an unprivileged user | symlinked leaf or ancestor, or attacker-owned directory, is refused; requester cannot unlink, rename or symlink in the socket directory |
| Owner refuses unsafe startup | root, inherited descriptors, group-writable or foreign-owned config, unknown config fields, symlinked or loose data directory, loose socket directory, foreign-owned database |
| Owner is not dumpable | requester cannot open `/proc/<pid>/mem`, `environ` or `fd`, cannot `PTRACE_ATTACH`, cannot signal the owner |
| Frames are strict | oversize, empty, truncated, non-UTF-8, duplicate-key and non-finite frames are refused |

The mutation runner removes each control in turn and checks that the named test fails. It
detects 15 of 15. Three of those (`symlink-check-skipped`, `root-refusal-removed`,
`path-trust-disabled`) are caught only because a second, redundant layer still refuses for a
different reason, so the tests pin the specific message. `frame-size-limit-removed` is caught by
a timeout. Detection shows these tests are not vacuous. It does not show the controls are enough.

## What is not claimed

- **Evidence class unchanged.** The runs were made by the same operator on one Linux container
  (kernel 6.18, as root, with real uids 61001 to 61003). That is not an independent witness.
- **One process-level topology, one effect.** Only `WRITE_KEY`. Requests are served one at a
  time. Distributed crash recovery for the two-process case (requester or owner crashing before
  or after commit, lost acknowledgement, idempotent outcome query) is the next item and is not
  done here. The V012 hard-exit test still covers only the in-process case.
- **No receipt for refusals at the service edge.** A request refused for peer uid or actor id
  never reaches the gate, so it leaves no receipt. Only an in-memory counter moves.
- **The socket file is mode 0666 on purpose.** Who may talk to the owner is decided by the
  kernel-reported peer uid, not by file mode.
- **Ptrace results depend on the host.** This container has no Yama LSM, so denial rests on the
  uid mismatch alone. A host that grants `CAP_SYS_PTRACE` to the requester defeats it.
- **Launch is trusted.** The launcher that starts the owner, writes its config and creates its
  directories is assumed correct. Nothing here protects against it.
- **Historical authorization and external evidence custody** (roadmap items 3 and 4) are not
  touched.
- **Tests need root.** Without it they skip, and a green ordinary `pytest` run says nothing
  about them. `WEAVER_REQUIRE_ISOLATION=1` turns the skip into a failure; the workflow sets it.

## Running it

```bash
sudo -E env "PATH=$PATH" WEAVER_REQUIRE_ISOLATION=1 \
  python -m pytest -q -p no:cacheprovider tests/isolation tests/test_owner_ipc.py
sudo -E env "PATH=$PATH" python -m tools.check_v008_mutations
```
