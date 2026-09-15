# Sender Pairing Policy

Unknown senders do not reach agents.

## States

```text
unknown -> pending -> approved
unknown -> denied
approved -> revoked
```

## Rules

- First message from an unknown sender may create a pending pairing event only.
- Pending senders may not enqueue executable work.
- Approved senders may enqueue messages only through AI Governance Runtime evaluation.
- Revoked senders are blocked silently and recorded.
- Sender identity must include channel, channel sender ID, pairing state, and approval receipt hash.

## Required receipt

`SenderPairingReceipt` must exist before a sender can become approved.

## Denied by default

```text
unknown_sender_to_agent: deny
pending_sender_to_agent: deny
revoked_sender_to_agent: deny
approved_sender_direct_to_workspace: deny
```
