# Weaver + Cathedral offline reproduction candidate

Status: LOCAL CANDIDATE / W0 / O0 / PRODUCTION PROHIBITED. No independent
operator receipt exists. Passing this kit does not close the VTK containment,
second-verifier, external-anchor, silicon, or portfolio promotion blockers.

## Publisher preparation

From this directory, download the locked wheels and build the environment:

```sh
python -m pip download --only-binary=:all: -r python.lock -d wheels
docker build -t weaver-reproduction:candidate .
python prepare.py --weaver .. --cathedral ../../cathedral-verified --output /absolute/new-kit
```

Preparation records base commits AND dirty working-tree status. The source tar
hash identifies the actual candidate under test; a base commit is not a claim
that the working tree equals that commit. Only tracked and unignored source files
are included. Publish the resulting artifacts together. Deliver the SHA256SUMS
hash through an independently authenticated channel before the operator executes.

The digest-pinned Python base and exact Python versions are build inputs. Apt
repositories are used during preparation; rebuilding the Dockerfile can produce a
new environment. The **exported environment.tar hash and image ID** freeze the
realized userspace. A rebuild requires a new manifest and another review.

## Independent operator procedure

Use a separate Linux amd64 machine with Docker, Python >=3.12, sufficient memory,
and at least 4 GB free disk. Obtain the manifest trust pin separately. First
verify SHA256SUMS against that pin with trusted local tools; verify and inspect
run.py before executing it. A verifier shipped in a bundle cannot authenticate
itself. The runner repeats digest verification before loading or executing images.

```sh
sha256sum SHA256SUMS
sha256sum --check SHA256SUMS
python run.py --manifest-sha256 <independently-obtained-hash> --output /absolute/new-results
```

The runner loads the exported environment and uses no network, a read-only root,
read-only kit, disposable source copies, and a fresh results directory. It runs
Weaver collection and its complete pytest suite, Cathedral's legacy adversarial
suite and RTL simulation, and Chronicle process/property tests. Every command,
exit code, raw stdout/stderr, installed Python and OS package versions, host kernel
and result hashes are retained. FAIL, timeout and infrastructure errors are never
PASS. Do not reuse a results directory or silently repair source inputs.

Scope: frozen userspace offline execution. The host kernel, CPU and Docker daemon
remain environmental dependencies and are not a VM-level isolation or hardware
attestation claim. Raw test logs may include temporary paths and timing variation;
compare assertions and source identities, not byte-identical execution logs.

## Witness and custody

Copy operator-receipt.template.json OUTSIDE the kit, complete it truthfully, and
sign the exact resulting bytes using a key whose owner identity was authenticated
separately. Bind the kit manifest digest AND results manifest digest; retain the
signature, public key, tool/version, custody record, raw results, and receipt.
Document operator/employer/infrastructure independence and all deviations. A
self-declared name or locally generated signature does not prove independence.
Do not place a completed receipt inside the already sealed results directory.

Have an external reviewer check identity, independence, pins, complete logs,
failures and custody. This tool never admits a witness, raises evidence tiers or
changes authority. Production remains prohibited even after a successful run.
