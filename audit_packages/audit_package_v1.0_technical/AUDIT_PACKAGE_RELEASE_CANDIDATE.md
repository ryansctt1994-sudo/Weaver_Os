# Technical Audit Package v1.0 — Candidate Record

Status: `CANDIDATE_READY_FOR_USER_SIGNATURE`
External delivery ready: `false`
Reason: `not_yet_signed_by_user_key_or_published_as_release`
Authority: `NONE`
Authority weight: `0`

This record preserves the current technical audit package candidate without claiming final external-delivery status.

## Package

```text
audit_package_v1.0_technical.tar.gz
```

SHA256:

```text
73d8128c221d23e709239bb098efeaa4c5faae98aa9efbbafb44a02e8adf931a  audit_package_v1.0_technical.tar.gz
```

## Debug / CI Status

```yaml
repo: ryansctt1994-sudo/Weaver_Os
candidate_pr: 23
debug_trigger_pr: 22
boundary_integrity_workflow:
  workflow_name: Boundary Integrity Demo
  workflow_run: 27254223950
  job: Run Boundary Integrity Demo
  conclusion: success
  artifact: boundary-integrity-demo-v0-1-receipts
  artifact_id: 7526881742
  artifact_digest: sha256:9c1493bc34d6650901e0a9846b214da96c59d7a1c2243ffc9047e0269388dbd4
  artifact_expires_at: 2026-09-08T04:57:17Z
```

The workflow debug issue was trigger visibility. The initial push/manual workflow was not visible through the available connector. A `pull_request` trigger was added, PR #22 was opened as an inspection trigger, and the PR-associated run completed successfully.

## Admissible Evidence Included

```yaml
boundary_integrity_demo:
  repo: ryansctt1994-sudo/Weaver_Os
  workflow_run: 27254223950
  artifact_id: 7526881742
  artifact_digest: sha256:9c1493bc34d6650901e0a9846b214da96c59d7a1c2243ffc9047e0269388dbd4
  evidence_level: E2_GITHUB_ACTION_SANDBOX_TESTED
  authority: NONE

pr001_pr005:
  tests_collected: 79
  passed: 78
  skipped: 1
  evidence_level: E2_SANDBOX_TESTED
  authority: NONE
```

## Exclusions

The technical package excludes mythos, personal witness claims, fake PGP/contact references, placeholder hashes, placeholder receipts, and unverified independent replication claims.

## Missing Governance Docs

The built package includes `governance/GOVERNANCE_DOCS_STATUS.md` noting that the named governance docs were not found in the current repo search and were therefore not included as evidence.

## Next Gate

The package should not be sent to external auditors until Ryan signs and publishes the final release artifact.

Recommended local finalization:

```bash
git tag -s audit-package-v1.0 -m "Technical audit package v1.0 - E2 evidence only, authority NONE"
git tag -v audit-package-v1.0
git push origin audit-package-v1.0
```

If no signing key exists yet, create and register an SSH signing key with GitHub before signing.

## Registry Seal

```yaml
event: TECHNICAL_AUDIT_PACKAGE_V1_0_CANDIDATE_RECORD_UPDATED
status: CANDIDATE_READY_FOR_USER_SIGNATURE
external_delivery_ready: false
authority: NONE
authority_weight: 0
next_gate: USER_SIGNED_TAG_AND_RELEASE
seal: "🔐♾️📐⚖️✅"
```
