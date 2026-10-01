# Independent RC1 reproduction and short demonstration

Target claim: the frozen RC1 constructed-command witness accepts its authorized
command, rejects its unauthorized command without changing protected state,
reconstructs the accepted outcome in a fresh process, and rejects its included
receipt and Chronicle mutations. This does not test real-world authority or
Academy learning. Academy model runs remain on hold pending independent core
reproduction and separate adjudication.

## Trust and independence

Obtain the full checkout commit, SHA-256 of `reproduction-seal.json`, archive
digest, and publisher key fingerprint through a separately trusted channel.
The checked-in seal is a publisher checksum manifest, not an independent witness
signature. Do not accept a replacement seal from a failing target.

The operator must be distinct from the authors/development process and declare
authorship, employment, funding, shared infrastructure, and other relevant ties.
A different AI assistant or another author-controlled CI run is not independent.
The operator controls their signing key; no private key belongs in this repository.

## Fixed commands

Use a fresh clone and the full 40-character commit supplied with the handoff:

```sh
git clone https://github.com/ryansctt1994-sudo/Weaver_Os.git weaver-reproduction
cd weaver-reproduction
git checkout --detach FULL_COMMIT_FROM_HANDOFF
git status --porcelain
sha256sum docs/releases/reproduction-seal.json
python3 -m venv .venv
. .venv/bin/activate
python -m pip install 'cryptography==46.0.0'
python -m tools.reproduce_witness --operator YOUR_IDENTITY --output ../witness-result
```

Compare the seal hash with the separately obtained value before running code.
The wrapper checks the sealed runner, verifier, demo, and archive bytes. It then
invokes the verified-snapshot runner, requires all nine witness checks, and binds
the outcome to the sealed archive digest. Dependencies are version-pinned here;
this is not a hermetic or hash-locked dependency build. Installation and download
time are separate from the timed demo. The runner has a 60-second deadline.

Keep the terminal transcript, including install errors. Never repair the target
during an outcome run. Preserve FAIL and ERROR bundles; reruns use new output
directories. If installation prevents execution, record UNAVAILABLE and the raw
error instead of inferring a result.

## Operator declaration and signature

Add `operator-declaration.txt` and `environment.txt` to the result directory.
State your identity, independence disclosures, full checkout SHA, whether you
modified anything, and how you authenticated the handoff digests. Record OS,
architecture, Python, `python -m pip freeze`, and the relevant terminal transcript.
The generated outcome records its unsigned state at creation; a detached signature
below authenticates the resulting bundle, not independence or correctness.

With an existing operator-controlled SSH signing key and OpenSSH supporting `-Y`:

```sh
cd ../witness-result
sha256sum reproduction-seal.json runner.stdout.txt runner.stderr.txt outcome.json \
  operator-declaration.txt environment.txt > SHA256SUMS
ssh-keygen -Y sign -f /PATH/TO/OPERATOR_PRIVATE_KEY -n weaver-witness SHA256SUMS
```

If a separate transcript file is included, include its hash in SHA256SUMS before
signing. Publish all listed files, SHA256SUMS, SHA256SUMS.sig, and your public key.
Transmit your public-key fingerprint through a separate identity-authenticated
channel. Do not send your private key. No witness has been commissioned by this
document, and no outcome is represented as independently reproduced yet.

## Receiving and adjudicating the result

The reviewer creates `allowed_signers` from the independently authenticated key:
`OPERATOR_ID ssh-ed25519 BASE64_PUBLIC_KEY`. Then, in the received result directory:

```sh
ssh-keygen -Y verify -f /PATH/TO/allowed_signers -I OPERATOR_ID \
  -n weaver-witness -s SHA256SUMS.sig < SHA256SUMS
sha256sum -c SHA256SUMS
```

Check the signed file list includes every claimed evidence file; compare the seal
to the original handoff; inspect raw output, all check results, exit codes, and
operator independence. Record PASS, FAIL, ERROR, or UNAVAILABLE for this exact
claim. Any W-axis update requires acceptance of the independent result; a signed
file alone cannot make that update. Operating authority remains separately assigned.
