# Portfolio Repair Baseline — 2026-09-04

Status: corrective governance baseline; no evidence or authority promotion

This file records the cross-portfolio interpretation rules applied during the 2026-09-04 repair pass. Its purpose is to stop strong architecture, mathematics, simulation, documentation, or local tests from being summarized later as stronger empirical claims than they earned.

## Universal invariants

```text
capability != authority
evidence != authority
witness != evidence
specification != implementation
architecture != execution
local_test != independent_reproduction
checksum != reproduction
signature != truth
simulation != physical_hardware_qualification
formal_model != whole_system_proof
benchmark_schema != benchmark_truth
proxy_metric != physical_measurement
policy_enforcement != safety_guarantee
research_hypothesis != discovered_law
```

No mechanism may silently convert uncertainty into authority.

## Canonical evidence axis

- E0 — concept / untested claim
- E1 — architecture, specification, theorem statement, or research artifact
- E2 — implemented and locally verified artifact
- E3 — fresh-environment same-team reproduction with exact artifact identity and receipt binding
- E4-A — organizationally independent reproduction
- E4-B — constitutional / governance review
- E4-C — adversarial assessment
- E5 — operational validation in the intended operating context
- E6 — external assessment or certification appropriate to the claim

Evidence is claim-specific and artifact-specific. Strong evidence for one property cannot silently promote another property or the surrounding system.

## Weaver / Cathedral / Foundry / Labyrinths / assurance stack

Keep architectural maturity separate from implementation and authority. Receipt generation, manifests, hash chains, provenance records, reality gates, and replay scaffolds are assurance mechanisms; they do not prove the truth of the claims passing through them. A digest proves byte identity/integrity properties, not semantic correctness. Independent reproduction remains a distinct gate from same-team replay.

Clean-room reconstructions must remain labeled reconstructions. They must never be rewritten as recovered originals merely because their behavior matches a narrative or specification.

## T81 computing stack

T81 determinism claims are surface-, implementation-, commit-, platform-, input-domain-, and toolchain-specific. A normative/frozen specification establishes project change-control precedence, not infallibility or operational authority. Storage compression, throughput, latency, energy, perplexity, security, and hardware behavior require separate receipts.

RTL simulation and emulator parity are not FPGA/ASIC qualification. Physical claims require synthesis/implementation reports, timing closure, target-board evidence, measurement procedure, raw logs, artifact digests, and—where independence is claimed—an independent witness.

## Cryptography

Custom ternary ciphers are research/toy constructions unless and until they have precise algorithms, threat models, formal security definitions, cryptanalysis/security reductions where applicable, independent expert review, standard test vectors, misuse analysis, and implementation security review.

Round-trip reversibility does not establish confidentiality. SHA-256 inside a construction does not make the construction secure. Low-entropy or constant ciphertext is not evidence of perfect secrecy.

## Formal mathematics, PSCA, curvature/topology, and cross-domain synthesis

Exact combinatorial, algebraic, geometric, or formal sub-results may be promoted only at the scope actually proved. A conditional theorem of the form "if physical hypothesis Γ holds, then property P follows" establishes the implication, not Γ.

Cross-domain bridges—e.g. mapping combinatorial structure to physical elasticity, curvature, morphogenesis, field dynamics, cognition, or ontology—remain hypotheses until a mechanism, measurement map, falsifiable predictions, and empirical evidence establish them. Mathematical resemblance or shared algebraic form is not a discovered physical law.

No unified-field, new-force, substrate, vacuum-mechanics, or equivalent physical claim is earned merely by an exact analogue in another physical system.

## Autogenous / endogenous signal work

Information-theoretic bounds are conditional mathematical results. A joint-confounder bound can strengthen an inference by closing synergy loopholes, but only if the confounder set and bound assumptions are defensible for the data-generating process. Predictive excess beyond a stated extrinsic-information budget is not by itself proof of consciousness, free will, agency, life, or ontological self-generation.

Empirical promotion requires identifiable observables, preregistered estimators, finite-sample error control, null models, sensitivity to omitted confounders, replication, and explicit alternative explanations.

## HRAP / multi-agent causal experiments

Experimental architecture, factorial design, routing contrasts, intervention notation, and preregistration plans do not become causal findings until the experiment is executed under the frozen protocol. Heterogeneous-agent complementarity, specialized-routing benefit, and consensus-independence effects remain hypotheses until adequately powered data and the preregistered analysis support them.

Do not treat a successful ensemble output as evidence that agent diversity caused the improvement unless the causal contrast actually identifies that effect.

## ASI Academy / AGI / RSI / advanced-agent portfolio

ASI Academy is a research, education, governance, and assurance architecture—not evidence that AGI, ASI, consciousness, or safe open-ended recursive self-improvement has been achieved.

Research on persona/character training, deliberative alignment, interpretability, corrigibility, multi-agent cooperation, or positive archetypes can motivate Academy experiments. It does not establish that misalignment is primarily a persona phenomenon, that relationship-based alignment is generally sufficient, or that the Academy thesis is empirically validated.

AGI/ASI timelines, post-AGI governance, decentralized autonomous institutions, and recursive-self-improvement scenarios must remain scenario/hypothesis material unless directly evidenced.

## Energy / data-centre forecasting

Keep measurement boundaries fixed before comparing figures. Consumption, generation-to-supply, combined data-centre+AI+crypto loads, and data-centre-only loads are different series. A central-case pair produced by two measurement bases is not an uncertainty interval.

Queue-completion probability, rebound elasticity, PUE, dependable capacity contribution, construction lead time, transmission deliverability, curtailment, local congestion, and generation-mix assumptions must be explicit variables with provenance and sensitivity ranges. A historical average such as a queue completion rate must not be applied as a universal regional constant without justification.

Forecast outputs are scenario-conditioned model results, not predictions with false precision. Preserve uncertainty, measurement-boundary changes, and superseded forecasts.

## Education reform / EIE / SIS / fidelity architecture

The education portfolio may accurately be described as architecturally mature, artifact-rich, and pilot-ready in selected areas where the underlying documentation supports that wording. It may not be described as having demonstrated district-wide educational outcome improvement, validated educator-effect estimates, production-scale privacy safety, or independent causal efficacy without live protected-data pilots and appropriate evaluation.

Educator feedback must remain protected from punitive individual scoring. Delivery fidelity must distinguish promised, scheduled, recorded, and actually experienced services. AI recommendations remain subordinate to accountable human educational authority.

## SynthaMed / healthcare architecture

Research architecture, synthetic scenarios, and governance pressure tests are not clinical validation. No diagnostic accuracy, treatment efficacy, patient-outcome benefit, autonomous medical authority, regulatory clearance, privacy compliance, cybersecurity assurance, or clinical safety claim follows from architecture alone.

## MASK-AI / FACECORE / respiratory platform

Pre-build and bench-test specifications remain nonprotective experimental work. Modified donor respirators lose their original certification unless separately recertified. Mechanical-simulator resistance, CO2, valve, seal, fogging, optical, noise, or failure-bypass tests are engineering evidence for the exact test article only.

No occupational, CBRN, IDLH, life-support, fall-arrest, rescue, or human-exposure claim is earned before the relevant standards, physical testing, human-factors gates, certification, and domain-specific safety engineering are completed.

## Hollow Earth / sinkhole initiative

The sinkhole program is a geological hazard-mitigation/reform architecture and speculative worldbuilding wrapper. Karst geology, subsidence observations, pipe/sewer failures, groundwater effects, radar precursors, hazard maps, insurance mechanisms, and mitigation economics can be real evidence. None of those facts establish a literal hollow Earth, global hidden interior civilization, or other unsupported ontology.

Keep invented program structures explicitly separated from sourced geological facts.

## Sacred geometry / comparative religion / mythic and theological work

Classical geometry can be exact mathematics. Textual correspondences can be evidence about texts and traditions. Neither geometric elegance nor cross-cultural motif recurrence is empirical evidence of a supernatural ontology, physical causal mechanism, or universal hidden code.

Experiential and theological claims may be recorded as experiential, philosophical, doctrinal, or interpretive claims without being silently converted into external scientific evidence.

## AI consciousness / personhood work

Arguments based on simulation-versus-instantiation, substrate dependence, computation, embodiment, thermodynamics, biological organization, or functional equivalence are philosophical and scientific positions with different premises. A formal theorem can show what follows from explicit axioms; it cannot settle consciousness empirically unless the disputed premises and measurement bridge are independently justified.

Behavioral sophistication, self-reference, continuity mechanisms, affective language, or model testimony do not by themselves prove or disprove subjective experience.

## Reform / policy portfolios

Government, education, economic, justice, infrastructure, and social reform architectures are normative/program-design proposals unless implemented and evaluated. Cost estimates, impact projections, and counterfactual benefits must be labeled modeled/estimated where applicable; proposed institutions are not existing outcomes.

## Promotion discipline

For every future summary, status document, README, portfolio page, or public claim:

1. Name the exact claim.
2. Name the exact artifact/version/commit.
3. Identify whether the support is definition, proof, implementation, simulation, local test, reproduction, independent witness, physical measurement, observational study, causal experiment, or external review.
4. State the measurement boundary and assumptions.
5. Preserve failures, nulls, skipped tests, contradictions, and uncertainty.
6. Do not inherit evidence across mirrors, repositories, domains, or abstraction layers.
7. If a required field is missing, cap the claim rather than filling it by inference.

## Portfolio-wide corrected status

The portfolio is an advanced, unusually broad research/engineering and governance body with substantial architecture, executable artifacts, local evidence, and increasingly rigorous assurance mechanics.

It is not portfolio-wide independently reproduced, production-authorized, clinically validated, physically hardware-qualified, cryptographically certified, AGI/ASI-proven, consciousness-proven, or a validated new theory of fundamental physics.

Those withheld claims are not failures. They are explicit promotion gates.
