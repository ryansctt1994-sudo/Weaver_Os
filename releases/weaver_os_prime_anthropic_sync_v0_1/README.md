# WEAVER OS PRIME – ANTHROPIC SYNC EDITION v0.1

Status: sealed local v0.1 governance architecture.

Promotion verdict: **HOLD**.
Authority default: **NONE**.

This release bundle contains base64-encoded ZIP packages for the sealed Weaver OS Prime v0.1 modules. Decode each package before use.

## Boundary

This is local executable governance infrastructure with local build receipts and local tests. It is not E4 independent reproduction, production readiness, clinical authorization, hardware validation, legal certification, security certification, formal proof, or deployment approval.

## Modules

1. `weaver_artifact_evidence_card_v0_1.zip`
2. `weaver_responsible_promotion_policy_v0_1.zip`
3. `weaver_behavioral_constitution_v0_1.zip`
4. `weaver_scenario_ledger_v0_1.zip`
5. `weaver_authority_passport_v0_1.zip`
6. `weaver_domain_authority_packs_v0_1.zip`
7. `weaver_academy_v0_1.zip`
8. `weaver_public_evidence_portal_v0_1.zip`

## Decode

```bash
cd releases/weaver_os_prime_anthropic_sync_v0_1
for f in packages/*.zip.b64; do base64 -d "$f" > "${f%.b64}"; done
```

## Verify

Use the SHA-256 values in `MANIFEST.json` after decoding.

## Canonical statement

WEAVER OS PRIME is an evidence-control layer for AI research and agentic systems, designed to turn safety principles, claims, receipts, replay, witnesses, promotion gates, domain boundaries, operator fluency, and public evidence into an auditable operating discipline.

Authority is NONE by default. Evidence must be claimed and receipted. Promotion requires validated evidence. Uncertainty blocks expansion, not removal. Public summaries are bounded and redacted. Nothing grants authority without a passport. No passport grants authority without evidence.
