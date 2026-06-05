# EGS-SM-001 Transition Table

Outcome model:

```text
STATE + EVENT + GUARDS -> ADVANCE | DENY | ESCALATE | FAIL_CLOSED
```

Definitions:

- ADVANCE: edge is defined and all required guards are true.
- DENY: edge is defined, but one or more required guards are false. The state does not advance.
- ESCALATE: edge is defined as an escalation route. Local execution is denied and routed upward.
- FAIL_CLOSED: edge is undefined, revocation is active, tamper is detected, or an unpermissioned state attempts to advance matter.

| From | Event | Guards | To | Outcome |
|---|---|---|---|---|
| IDLE | AUTHENTICATE | identity_valid, institution_valid | AUTHENTICATED | ADVANCE or DENY |
| AUTHENTICATED | LOAD | token_valid, device_attested, reagent_attested, facility_valid | LOADED | ADVANCE or DENY |
| LOADED | SCREEN | known_hazard_clear, functional_screen_clear | SCREENED | ADVANCE or DENY |
| SCREENED | ARM | tier_allowed_for_facility, quorum_valid, not_revoked | ARMED | ADVANCE or DENY |
| ARMED | COMMIT_SYNTHESIS | final_quorum_valid, chamber_sealed, audit_sink_available | SYNTHESIZING | ADVANCE or DENY |
| SYNTHESIZING | VERIFY | product_verified, hazard_recheck_clear | VERIFIED | ADVANCE or DENY |
| VERIFIED | RELEASE | release_authorized, custody_receipt_written | RELEASED | ADVANCE or DENY |
| LOADED | ESCALATE | escalation_quorum_required | RECERTIFICATION_REQUIRED | ESCALATE |
| SCREENED | ESCALATE | escalation_quorum_required | RECERTIFICATION_REQUIRED | ESCALATE |
| ARMED | ESCALATE | escalation_quorum_required | RECERTIFICATION_REQUIRED | ESCALATE |

Every undefined state/event pair must produce FAIL_CLOSED.

The matter-commit edge is ARMED + COMMIT_SYNTHESIS -> SYNTHESIZING. No transition may enter SYNTHESIZING unless the edge is defined and all guards are true.
