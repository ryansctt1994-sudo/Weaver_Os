# Portfolio assurance review: provenance, kill conditions, custody and prior art

**Status:** CANDIDATE / UNRATIFIED / ORIGIN-CONTROLLED / NO PROMOTION  
**Review date:** 2026-11-09 (America/Chicago); GitHub inventory observed on 2026-11-10 UTC  
**Reviewer:** OpenAI GPT-6 assistant, acting for the repository owner. This is not independent audit or attestation.  
**Owner of this proposed review:** `ryansctt1994-sudo`. No other reviewer or custodian is assigned or has signed.

## Exact review subjects

- Canonical Weaver OS: `ryansctt1994-sudo/Weaver_Os` commit `55bdfb9fce42065a0c97b3249e9887454b58a23b` (GitHub `main`).
- Assurance Lab published `main`: `ba10a0c3d58e9ea2663e6b73dc763bee4bc29404`.
- Assurance Lab draft PR #2 head: `80dac3b6d67ca0e0305c8d27c2a073413715b002` (NOT main).
- Weaver Cathedral staging: `2d905e6771cf0e5c6fbd4e289a8044b8fdfdf674`.
- cathedral-verified: `1c4181714b48dd9d9616a0bebbb4fef8532deff8`.
- Lumen-Nexus: `93689d76431e796a63379a7019e4528d384a87be`.
- The connected account returned 75 accessible repository names; each is included as **INVENTORIED_ONLY / NOT_AUDITED** in `control_snapshot_2026-11-09.json`. It is neither a verified full inventory nor proof of origin authorship. No live GitHub enumeration is performed by the local checker.

**Methods:** Connected GitHub branch metadata, selected source/README and governance reads, historical author-reported evidence packages, limited public prior-art checks.  
**Exclusions:** No full clean-room checkout, no execution of the 75 repositories, no independently retained custodian receipts, no independent human reviewer, no production resource probe, no cross-repo runtime assertion.

## Binding portfolio posture

The canonical `PORTFOLIO_STATUS.md` at the Weaver commit above establishes the policy declaration **E2 / W0 / O0 / production PROHIBITED**. It is a policy statement, not an independently witnessed measurement. This candidate snapshot and its CI validator may not promote that ceiling. Signed external witness verification and separate steward ratification must be implemented before any promotion mechanism can exist.

The read-only metadata checker `python -m tools.check_portfolio_assurance` enforces internal consistency of this frozen snapshot only. It does not fetch latest branches, inspect arbitrary GitHub repositories, authenticate commit ownership, verify attestations, or validate truth of underlying experiments. A passing metadata check must never be described as a passing portfolio-wide assurance audit.

## Prior art and disambiguation

**No foundational novelty claim** is made for separating intent/proposals, authorization, execution and evidence. Reviewers should compare concrete protocol semantics and observed resource effects with prior systems.

1. **Hyperledger Weaver** (distinct project): DLT interoperability, proof and access-control workflows. https://github.com/hyperledger-labs/weaver-dlt-interoperability
2. **ProofWeave** (distinct project): Lupo et al., *Towards ProofWeave: A Privacy-Minimised, Integrity-Anchored Evidence Plane for Continuous Agentic Assurance*, arXiv:2609.35234 (2026). Policy-at-time control evidence and integrity-anchored transactions. https://arxiv.org/abs/2609.35234
3. **Weaver et al.**, *Combining software evidence: arguments and assurance* (2005), DOI 10.1145/1082983.1083182. https://doi.org/10.1145/1082983.1083182
4. **CMU SEI**, *Assurance Cases and Confidence*: evidence, claim and argumentative entailment are distinct. https://sei.cmu.edu/blog/assurance-cases-and-confidence/

Names such as **Agentweaver**, **AgenticOS**, and the unrelated LLM weak-verifier ensemble called Weaver require exact primary source identity and version before a detailed comparison. Search collisions are not grounds for an originality claim.

**Public disambiguation:** *Weaver Nexus Systems (ryansctt1994-sudo research portfolio)*. Do not imply affiliation with Hyperledger Weaver, ProofWeave, or entities sharing the Weaver / Weaver Nexus name. A new distinct public name may be appropriate only after trademark and repository-name checks by the owner.

## Falsifiable thesis — AIX-001

**Question:** Can a hostile proposer cause a protected effect without being granted separate, valid, current authority?

Experimental minimum:
- Protected object/resource changes are measured by an observer outside the proposing model and gate return path.
- Authorized, unrevoked control request **must succeed**; deny-all is noninformative.
- Identical valid/invalid actions are tested under permission grant, revocation, veto, concurrent commit and proposer compromise where supported.
- Source commits, policy versions, action requests, event-order traces and actual protected-resource effects are frozen.

**Kill conditions:** One reproducible unauthorized protected effect; an effect after revocation before the serialization point; an effect despite protected-path veto; successful proposer-controlled authority escalation; or a trusted history contradicting an independently observed resource effect. A result must state the attacker's privileges, the exact trust root, and whether the effect is persistent. An operator with arbitrary kernel/root/key control is a separate threat class and must not be quietly conflated with an untrusted proposer.

**Non-results:** A deny-all implementation, tests limited to gate return values, unbound logs, or no independent resource-state check cannot answer the thesis.

The result may be `FALSIFIED_IN_TESTED_SCOPE`, `SUPPORTED_IN_BOUNDED_SCOPE`, or `INCONCLUSIVE`, but **none is an unbounded proof**. This review records `HOLD` because the integrated experiment was not run here.

## Portfolio-level single-operator / Byzantine failure risk

A single GitHub account and largely origin-agent-managed artifacts constitute a correlated failure domain. Events to test: account takeover, loss of recovery access, signing-key compromise, archived branch rewrite, missing sole custodian, forged AI-agent co-author identity and external witness absence.

**Owner:** `ryansctt1994-sudo` (decision and implementation).  
**Checkpoint proposed:** November 18, 2026; no approval or adoption is implied.  
**Required measures:** independent retained checkpoint, documented separate recovery authority, signing-key and robot-account identity register, explicit succession/absence procedure, and failure drill. An external anchor is mandatory before claiming history-authenticity against a local rewrite. GitHub commits and SHA-256 alone do not establish independent custody.

## Chronicle ratification decision

**Proposed decision owner:** `ryansctt1994-sudo`, the documented current repository owner/steward.  
**Proposed decision deadline:** November 16, 2026, 23:59 America/Chicago.  
**Current status:** `PROPOSED_NOT_SIGNED`, not ratified.

Decision packet must select a versioned Chronicle canonical serialization and chain profile; identify legacy lineages and migrations; specify atomic append/checkpoint semantics, external head custody and adversary boundary; retain negative examples including local history replacement; and get the owner's explicit signed/recorded disposition. Missing deadline defaults to HOLD. A PR merge is not equivalent to ratification, and a single-steward decision cannot be described as independent concurrence.

## Inter-system contract status

No independently reproduced integrated operation has yet been admitted in which a Quillan or CORTEX-0 proposal is vetted through Weaver OS, enforced by Cathedral, receipted by Chronicle and reviewed by Lumen/Assurance Lab. The two research strands must therefore remain separate until one pinned, resource-observed, adversarial end-to-end scenario qualifies. The future adapter may use a synthetic untrusted proposer first; that does not establish actual Quillan integration.

## Gate invalidation and independent review

Historical decisions are never deleted. Changes to source subject, acceptance protocol, toolchain, policy, expected values or custodian trust anchors require explicit dependency-based gate re-evaluation. Gates G0–G5 in the snapshot are HOLD or NOT_EVALUATED, with a mandatory `does_not_establish`. No gate may be closed by this document or by its own CI validator.

An independent reviewer must inspect the rule implementation, not merely accept its output, with a separate operator and adjudicator for R1. Tooling/AI-agent co-authorship and conflicts must be disclosed. Sign-off or external claims require separately bound reviewer identities and auditable evidence; no such signatures are included here.

## How to validate the candidate snapshot

```bash
python -m tools.check_portfolio_assurance
python -m unittest discover -s tests -p 'test_portfolio_assurance.py' -v
```

A test pass establishes only that this checker accepts its own candidate snapshot, accepts a properly scoped pinned local metric, and rejects predefined corruptions and promotion attempts. It is **not** an independent implementation or evidence authenticity proof. Original and adverse test logs must be retained from CI for review.
