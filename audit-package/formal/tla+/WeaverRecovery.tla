---- MODULE WeaverRecovery ----
EXTENDS Naturals, FiniteSets
CONSTANTS R1, R2
Requests == {R1, R2}
Dispositions == {"Absent", "Intent", "Pass", "Reject", "Indeterminate"}
Phases == {"Idle", "IntentBuffered", "Ready", "Running", "PassBuffered", "RejectBuffered"}
Bases == {"None", "Reconciled", "Waived"}
VARIABLES durable, phase, recoveryBuffer, mode, executions, effects,
          reconciliation, basis, authorityDelta, unknownEver, intentCommitted
vars == <<durable, phase, recoveryBuffer, mode, executions, effects,
          reconciliation, basis, authorityDelta, unknownEver, intentCommitted>>

\* R1 is the original, R2 a replacement for the SAME semantic operation.
\* Valid external authority is assumed for both; recovery cannot create it.
CanStart(r) ==
  /\ durable[r] = "Absent"
  /\ IF r = R1 THEN durable[R2] = "Absent"
     ELSE /\ durable[R1] = "Indeterminate"
          /\ reconciliation \in {"Reconciled", "Waived"}
Normalize(d) == [r \in Requests |-> IF d[r] = "Intent" THEN "Indeterminate" ELSE d[r]]
Init ==
  /\ durable = [r \in Requests |-> "Absent"]
  /\ phase = [r \in Requests |-> "Idle"]
  /\ recoveryBuffer = {}
  /\ mode = "Online"
  /\ executions = [r \in Requests |-> 0]
  /\ effects = [r \in Requests |-> "None"]
  /\ reconciliation = "None"
  /\ basis = [r \in Requests |-> "None"]
  /\ authorityDelta = 0
  /\ unknownEver = {}
  /\ intentCommitted = {}
WriteIntent(r) ==
  /\ mode = "Online" /\ phase[r] = "Idle" /\ CanStart(r)
  /\ phase' = [phase EXCEPT ![r] = "IntentBuffered"]
  /\ UNCHANGED <<durable, recoveryBuffer, mode, executions, effects,
                 reconciliation, basis, authorityDelta, unknownEver, intentCommitted>>
FsyncIntent(r) ==
  /\ mode = "Online" /\ phase[r] = "IntentBuffered" /\ CanStart(r)
  /\ durable' = [durable EXCEPT ![r] = "Intent"]
  /\ intentCommitted' = intentCommitted \cup {r}
  /\ phase' = [phase EXCEPT ![r] = "Ready"]
  /\ basis' = [basis EXCEPT ![r] = IF r = R2 THEN reconciliation ELSE "None"]
  /\ UNCHANGED <<recoveryBuffer, mode, executions, effects,
                 reconciliation, authorityDelta, unknownEver>>
Dispatch(r) ==
  /\ mode = "Online" /\ phase[r] = "Ready" /\ durable[r] = "Intent"
  /\ executions[r] = 0
  /\ phase' = [phase EXCEPT ![r] = "Running"]
  /\ executions' = [executions EXCEPT ![r] = @ + 1]
  /\ effects' = [effects EXCEPT ![r] = "Partial"]
  /\ UNCHANGED <<durable, recoveryBuffer, mode, reconciliation, basis,
                 authorityDelta, unknownEver, intentCommitted>>
Complete(r, verdict) ==
  /\ mode = "Online" /\ phase[r] = "Running"
  /\ verdict \in {"PassBuffered", "RejectBuffered"}
  /\ phase' = [phase EXCEPT ![r] = verdict]
  /\ effects' = [effects EXCEPT ![r] = "Complete"]
  /\ UNCHANGED <<durable, recoveryBuffer, mode, executions, reconciliation,
                 basis, authorityDelta, unknownEver, intentCommitted>>
FsyncTerminal(r) ==
  /\ mode = "Online" /\ phase[r] \in {"PassBuffered", "RejectBuffered"}
  /\ durable' = [durable EXCEPT ![r] = IF phase[r] = "PassBuffered" THEN "Pass" ELSE "Reject"]
  /\ phase' = [phase EXCEPT ![r] = "Idle"]
  /\ UNCHANGED <<recoveryBuffer, mode, executions, effects, reconciliation,
                 basis, authorityDelta, unknownEver, intentCommitted>>
CrashChoices(r) ==
  CASE phase[r] = "IntentBuffered" -> {"Absent", "Intent"}
    [] phase[r] = "PassBuffered" -> {"Intent", "Pass"}
    [] phase[r] = "RejectBuffered" -> {"Intent", "Reject"}
    [] r \in recoveryBuffer -> {"Intent", "Indeterminate"}
    [] OTHER -> {durable[r]}
Crash ==
  /\ mode # "Down" /\ mode' = "Down"
  /\ phase' = [r \in Requests |-> "Idle"]
  /\ recoveryBuffer' = {}
  /\ durable' \in [Requests -> Dispositions]
  /\ \A r \in Requests : durable'[r] \in CrashChoices(r)
  /\ intentCommitted' = intentCommitted \cup {r \in Requests : durable'[r] # "Absent"}
  /\ unknownEver' = unknownEver \cup {r \in Requests : durable'[r] = "Indeterminate"}
  /\ basis' = [r \in Requests |->
       IF r = R2 /\ phase[r] = "IntentBuffered" /\ durable'[r] = "Intent"
       THEN reconciliation ELSE basis[r]]
  /\ UNCHANGED <<executions, effects, reconciliation, authorityDelta>>
Boot ==
  /\ mode = "Down" /\ mode' = "Recovering"
  /\ UNCHANGED <<durable, phase, recoveryBuffer, executions, effects,
                 reconciliation, basis, authorityDelta, unknownEver, intentCommitted>>
StageRecovery(r) ==
  /\ mode = "Recovering" /\ durable[r] = "Intent" /\ r \notin recoveryBuffer
  /\ recoveryBuffer' = recoveryBuffer \cup {r}
  /\ UNCHANGED <<durable, phase, mode, executions, effects, reconciliation,
                 basis, authorityDelta, unknownEver, intentCommitted>>
FsyncRecovery(r) ==
  /\ mode = "Recovering" /\ r \in recoveryBuffer /\ durable[r] = "Intent"
  /\ durable' = [durable EXCEPT ![r] = "Indeterminate"]
  /\ recoveryBuffer' = recoveryBuffer \ {r}
  /\ unknownEver' = unknownEver \cup {r}
  /\ UNCHANGED <<phase, mode, executions, effects, reconciliation,
                 basis, authorityDelta, intentCommitted>>
Resume ==
  /\ mode = "Recovering" /\ \A r \in Requests : durable[r] # "Intent"
  /\ mode' = "Online"
  /\ UNCHANGED <<durable, phase, recoveryBuffer, executions, effects,
                 reconciliation, basis, authorityDelta, unknownEver, intentCommitted>>
\* EXTERNAL policy fact. Reconciled means no duplicate-relevant effect and no live worker.
Resolve(choice) ==
  /\ mode = "Online" /\ reconciliation = "None" /\ durable[R1] = "Indeterminate"
  /\ choice \in {"Reconciled", "Waived"}
  /\ (choice = "Reconciled" => effects[R1] = "None")
  /\ reconciliation' = choice
  /\ UNCHANGED <<durable, phase, recoveryBuffer, mode, executions, effects,
                 basis, authorityDelta, unknownEver, intentCommitted>>
Next ==
  \/ \E r \in Requests : WriteIntent(r) \/ FsyncIntent(r) \/ Dispatch(r) \/ FsyncTerminal(r)
  \/ \E r \in Requests, v \in {"PassBuffered", "RejectBuffered"} : Complete(r, v)
  \/ Crash \/ Boot \/ Resume
  \/ \E r \in Requests : StageRecovery(r) \/ FsyncRecovery(r)
  \/ \E c \in {"Reconciled", "Waived"} : Resolve(c)
Spec == Init /\ [][Next]_vars
TypeOK ==
  /\ durable \in [Requests -> Dispositions] /\ phase \in [Requests -> Phases]
  /\ recoveryBuffer \subseteq Requests /\ mode \in {"Online", "Down", "Recovering"}
  /\ executions \in [Requests -> 0..1] /\ effects \in [Requests -> {"None", "Partial", "Complete"}]
  /\ reconciliation \in Bases /\ basis \in [Requests -> Bases]
  /\ unknownEver \subseteq Requests /\ intentCommitted \subseteq Requests /\ authorityDelta = 0
Inv_DurableBeforeDispatch == \A r \in Requests : executions[r] > 0 => r \in intentCommitted
Inv_UnknownNeverRedispatched ==
  /\ \A r \in unknownEver : durable[r] = "Indeterminate" /\ phase[r] = "Idle"
  /\ \A r \in Requests : executions[r] <= 1
Inv_RecoveryIdempotent ==
  /\ Normalize(Normalize(durable)) = Normalize(durable)
  /\ \A r \in Requests : durable[r] = "Indeterminate" => r \in intentCommitted
Inv_NoAuthorityGain == authorityDelta = 0
Inv_ReplacementRequiresResolution ==
  durable[R2] # "Absent" => basis[R2] \in {"Reconciled", "Waived"}
Inv_TerminalEvidence ==
  \A r \in Requests : durable[r] \in {"Pass", "Reject"} => executions[r] = 1
====
