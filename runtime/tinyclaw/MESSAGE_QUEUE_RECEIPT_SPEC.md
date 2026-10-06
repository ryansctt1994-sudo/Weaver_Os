# Message Queue Receipt Spec

Receipt type: `QueueMessageReceipt`

## Purpose

Record each TinyClaw queue message before any payload reaches an agent workspace.

## Minimum fields

```json
{
  "receipt_version": "0.1",
  "receipt_type": "QueueMessageReceipt",
  "timestamp": "ISO-8601",
  "runtime": "tinyclaw",
  "authority_id": "tinyclaw.local_runtime.v0_1",
  "sender_channel": "discord | telegram | whatsapp | tinyoffice | api",
  "sender_status": "approved | pending | denied",
  "message_id": "string",
  "message_hash": "sha256",
  "queue_transition": "received | blocked | enqueued | dead_lettered",
  "policy_decision": "allow | block | escalate",
  "previous_receipt_hash": null,
  "receipt_hash": "sha256"
}
```

## Rule

No queue message may enter an active workspace unless a receipt exists and the policy decision is `allow`.
