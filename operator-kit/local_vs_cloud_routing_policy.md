# Local vs Cloud Routing Policy

## Purpose

Route AI work according to privacy, latency, cost, capability, and verification needs.

## Local AI is preferred for

- Private notes and sensitive source material.
- Fast summarization and extraction.
- Low-latency drafting.
- Offline work.
- Repetitive classification.
- Pre-filtering before cloud escalation.

## Cloud AI is preferred for

- Large-context synthesis.
- Deep reasoning.
- Tool-connected operations.
- Repository-scale work.
- Multi-step implementation planning.
- Tasks requiring current external information.

## Hybrid AI is preferred for

- Sensitive workflows where private data should stay local but abstracted results can be escalated.
- Engineering tasks where local scans identify context and cloud reasoning produces plans.
- Registry work where local extraction feeds cloud audit.

## Routing rule

Data gravity and privacy decide where context lives. Capability decides where reasoning runs. Evidence discipline decides whether outputs can affect authority.

## Failure modes

- Sending private material to cloud unnecessarily.
- Trusting local model outputs beyond capability.
- Treating fast local inference as validated cognition.
- Treating cloud synthesis as verification.
- Losing provenance across local/cloud handoff.

## Required handoff metadata

Every routed task should record:

- Where input data was processed.
- Which model or tool class was used.
- What was escalated.
- What was withheld.
- What output was produced.
- What evidence label applies.