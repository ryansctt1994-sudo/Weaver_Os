# Team Chain Receipt Spec

Receipt type: `TeamHandoffReceipt`

## Purpose

Record each agent-to-agent or agent-to-team handoff in TinyClaw without granting authority to the team chain.

## Minimum fields

```json
{
  "receipt_version": "0.1",
  "receipt_type": "TeamHandoffReceipt",
  "timestamp": "ISO-8601",
  "runtime": "tinyclaw",
  "authority_id": "tinyclaw.local_runtime.v0_1",
  "team_id": "string",
  "from_agent": "string",
  "to_agent_or_team": "string",
  "handoff_reason_hash": "sha256",
  "input_hash": "sha256",
  "output_hash": "sha256",
  "policy_decision": "allow | block | escalate",
  "previous_receipt_hash": "sha256",
  "receipt_hash": "sha256"
}
```

## Rule

Every team handoff must be chained to the prior receipt. Broken chains block promotion.
