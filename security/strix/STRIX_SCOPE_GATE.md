# Strix Scope Gate

Strix is an adversarial security witness. Strix may challenge authority; it may not grant authority.

## Approved initial scope

```text
target: local TinyClaw/TinyOffice only
mode: non-production
network: local approved targets only
promotion_effect: challenge/HOLD only
```

## Focus areas

- auth bypass,
- sender pairing bypass,
- queue poisoning,
- TinyOffice settings mutation,
- file/config exposure,
- prompt injection through channel messages,
- unsafe provider or runtime invocation paths.

## Out of scope

- production systems,
- third-party targets without written authorization,
- physical robots,
- cloud spend,
- destructive actions.

## Rule

A critical/high finding opens a ChallengeGate docket and blocks promotion until fix verification and rescan evidence exist.
