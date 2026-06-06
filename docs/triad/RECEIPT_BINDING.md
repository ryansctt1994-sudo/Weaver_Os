# Receipt Binding Contract

A receipt is a cryptographically and semantically bound evidence packet. It is not a narrative note.

## Minimum Bound Fields

Every authority-relevant receipt must bind:

- `actor_id`
- `actor_public_key` or stable key reference
- `event_hash`
- `previous_event_hash`
- `policy_version`
- `event_timestamp`
- `proposal_payload_hash`
- `admissibility_result`
- `replay_result`
- `verifier_id` or verifier key reference
- `signature`

## Binding Rule

The signature must cover the event hash or a canonical envelope that includes the event hash. Signing loose prose, partial payloads, or mutable summaries is insufficient.

## Replay Rule

A receipt does not authorize execution by itself. It records evidence. Authority is recomputed from replay under the declared policy and current admissibility rules.

## Invalid Receipt Conditions

A receipt must be rejected or downgraded if:

- its signature cannot be verified;
- its event hash does not match the canonical event;
- its prior hash does not connect to the ledger chain;
- its policy version is missing or incompatible;
- its payload hash cannot be reproduced;
- its replay result cannot be reproduced;
- its verifier identity is absent when required.

## Non-Claim

Receipt binding improves auditability. It does not prove that the underlying policy is correct, complete, ethical, or safe.
