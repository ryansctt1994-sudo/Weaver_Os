---- MODULE WeaverActivation ----
EXTENDS Naturals, FiniteSets

CONSTANTS
  R1, R2,
  B1, B2,
  CP1, CP2,
  C1, C2,
  I1, I2,
  O1, O2,
  A1, A2,
  NONE,
  ContractV1

Requests == {R1, R2}
Backends == {B1, B2}
Checkpoints == {CP1, CP2}
Contracts == {C1, C2}
Inputs == {I1, I2}
Outputs == {O1, O2}
AuthorityEvents == {A1, A2}

States ==
  {"Proposed", "Authorized", "ContractBound", "Executed",
   "ResultVerified", "Recorded", "Rejected"}

RejectCodes ==
  {"CONTRACT_VERSION_MISMATCH", "MALFORMED_IDENTITY",
   "AUTHORITY_INVALID", "AUTHORITY_BINDING_MISMATCH", "BACKEND_FAILED",
   "RESULT_IDENTITY_MISMATCH", "METRIC_INVALID", "RETENTION_GATE_FAILED"}

AuthRequest(a) == IF a = A1 THEN R1 ELSE R2
AuthContract(a) == IF a = A1 THEN C1 ELSE C2
AuthBackend(a) == IF a = A1 THEN B1 ELSE B2
AuthCheckpoint(a) == IF a = A1 THEN CP1 ELSE CP2
AuthInput(a) == IF a = A1 THEN I1 ELSE I2

VARIABLES
  state,
  boundContract,
  boundBackend,
  boundCheckpoint,
  boundInput,
  boundAuthority,
  consumedRequests,
  executionCount,
  resultOutput,
  recordedEvidence,
  authorityDelta,
  protectedState

vars ==
  <<state, boundContract, boundBackend, boundCheckpoint, boundInput,
    boundAuthority, consumedRequests, executionCount, resultOutput,
    recordedEvidence, authorityDelta, protectedState>>

Receipt(r, verdict, code, output) ==
  [ requestId       |-> r,
    contractVersion |-> ContractV1,
    contract        |-> boundContract[r],
    backend         |-> boundBackend[r],
    checkpoint      |-> boundCheckpoint[r],
    input           |-> boundInput[r],
    output          |-> output,
    authorityEvent  |-> boundAuthority[r],
    verdict         |-> verdict,
    rejectionCode   |-> code,
    authorityDelta  |-> 0 ]

Init ==
  /\ state = [r \in Requests |-> "Proposed"]
  /\ boundContract = [r \in Requests |-> NONE]
  /\ boundBackend = [r \in Requests |-> NONE]
  /\ boundCheckpoint = [r \in Requests |-> NONE]
  /\ boundInput = [r \in Requests |-> NONE]
  /\ boundAuthority = [r \in Requests |-> NONE]
  /\ consumedRequests = {}
  /\ executionCount = [r \in Requests |-> 0]
  /\ resultOutput = [r \in Requests |-> NONE]
  /\ recordedEvidence = {}
  /\ authorityDelta = [r \in Requests |-> 0]
  /\ protectedState = 0

Authorize(r, authEvent) ==
  /\ state[r] = "Proposed"
  /\ authEvent \in AuthorityEvents
  /\ AuthRequest(authEvent) = r
  /\ state' = [state EXCEPT ![r] = "Authorized"]
  /\ boundAuthority' = [boundAuthority EXCEPT ![r] = authEvent]
  /\ UNCHANGED
       <<boundContract, boundBackend, boundCheckpoint, boundInput,
         consumedRequests, executionCount, resultOutput, recordedEvidence,
         authorityDelta, protectedState>>

BindContract(r, c, b, cp, inp) ==
  /\ state[r] = "Authorized"
  /\ c \in Contracts
  /\ b \in Backends
  /\ cp \in Checkpoints
  /\ inp \in Inputs
  /\ boundAuthority[r] \in AuthorityEvents
  /\ c = AuthContract(boundAuthority[r])
  /\ b = AuthBackend(boundAuthority[r])
  /\ cp = AuthCheckpoint(boundAuthority[r])
  /\ inp = AuthInput(boundAuthority[r])
  /\ state' = [state EXCEPT ![r] = "ContractBound"]
  /\ boundContract' = [boundContract EXCEPT ![r] = c]
  /\ boundBackend' = [boundBackend EXCEPT ![r] = b]
  /\ boundCheckpoint' = [boundCheckpoint EXCEPT ![r] = cp]
  /\ boundInput' = [boundInput EXCEPT ![r] = inp]
  /\ UNCHANGED
       <<boundAuthority, consumedRequests, executionCount, resultOutput,
         recordedEvidence, authorityDelta, protectedState>>

Execute(r) ==
  /\ state[r] = "ContractBound"
  /\ r \notin consumedRequests
  /\ executionCount[r] = 0
  /\ state' = [state EXCEPT ![r] = "Executed"]
  /\ consumedRequests' = consumedRequests \cup {r}
  /\ executionCount' = [executionCount EXCEPT ![r] = @ + 1]
  /\ UNCHANGED
       <<boundContract, boundBackend, boundCheckpoint, boundInput,
         boundAuthority, resultOutput, recordedEvidence, authorityDelta,
         protectedState>>

VerifyGood(r, actualB, actualCP, actualInput, output) ==
  /\ state[r] = "Executed"
  /\ actualB = boundBackend[r]
  /\ actualCP = boundCheckpoint[r]
  /\ actualInput = boundInput[r]
  /\ output \in Outputs
  /\ state' = [state EXCEPT ![r] = "ResultVerified"]
  /\ resultOutput' = [resultOutput EXCEPT ![r] = output]
  /\ UNCHANGED
       <<boundContract, boundBackend, boundCheckpoint, boundInput,
         boundAuthority, consumedRequests, executionCount, recordedEvidence,
         authorityDelta, protectedState>>

RejectSubstitution(r, actualB, actualCP, actualInput) ==
  /\ state[r] = "Executed"
  /\ \/ actualB # boundBackend[r]
     \/ actualCP # boundCheckpoint[r]
     \/ actualInput # boundInput[r]
  /\ state' = [state EXCEPT ![r] = "Rejected"]
  /\ recordedEvidence' =
       recordedEvidence \cup
         {Receipt(r, "REJECT", "RESULT_IDENTITY_MISMATCH", NONE)}
  /\ UNCHANGED
       <<boundContract, boundBackend, boundCheckpoint, boundInput,
         boundAuthority, consumedRequests, executionCount, resultOutput,
         authorityDelta, protectedState>>

RejectNonFinite(r) ==
  /\ state[r] = "Executed"
  /\ state' = [state EXCEPT ![r] = "Rejected"]
  /\ recordedEvidence' =
       recordedEvidence \cup {Receipt(r, "REJECT", "METRIC_INVALID", NONE)}
  /\ UNCHANGED
       <<boundContract, boundBackend, boundCheckpoint, boundInput,
         boundAuthority, consumedRequests, executionCount, resultOutput,
         authorityDelta, protectedState>>

AllowedReject(s, code) ==
  CASE s = "Proposed" ->
         code \in {"CONTRACT_VERSION_MISMATCH", "MALFORMED_IDENTITY",
                   "AUTHORITY_INVALID"}
    [] s = "Authorized" ->
         code = "AUTHORITY_BINDING_MISMATCH"
    [] s = "Executed" ->
         code \in {"BACKEND_FAILED", "RESULT_IDENTITY_MISMATCH",
                   "METRIC_INVALID", "RETENTION_GATE_FAILED"}
    [] OTHER -> FALSE

Reject(r, code) ==
  /\ state[r] \in {"Proposed", "Authorized", "Executed"}
  /\ code \in RejectCodes
  /\ AllowedReject(state[r], code)
  /\ state' = [state EXCEPT ![r] = "Rejected"]
  /\ recordedEvidence' =
       recordedEvidence \cup {Receipt(r, "REJECT", code, NONE)}
  /\ UNCHANGED
       <<boundContract, boundBackend, boundCheckpoint, boundInput,
         boundAuthority, consumedRequests, executionCount, resultOutput,
         authorityDelta, protectedState>>

RecordPass(r) ==
  /\ state[r] = "ResultVerified"
  /\ resultOutput[r] \in Outputs
  /\ state' = [state EXCEPT ![r] = "Recorded"]
  /\ recordedEvidence' =
       recordedEvidence \cup {Receipt(r, "PASS", NONE, resultOutput[r])}
  /\ UNCHANGED
       <<boundContract, boundBackend, boundCheckpoint, boundInput,
         boundAuthority, consumedRequests, executionCount, resultOutput,
         authorityDelta, protectedState>>

Next ==
  \/ \E r \in Requests, a \in AuthorityEvents : Authorize(r, a)
  \/ \E r \in Requests, c \in Contracts, b \in Backends,
        cp \in Checkpoints, inp \in Inputs : BindContract(r, c, b, cp, inp)
  \/ \E r \in Requests : Execute(r)
  \/ \E r \in Requests, b \in Backends, cp \in Checkpoints,
        inp \in Inputs, o \in Outputs : VerifyGood(r, b, cp, inp, o)
  \/ \E r \in Requests, b \in Backends, cp \in Checkpoints,
        inp \in Inputs : RejectSubstitution(r, b, cp, inp)
  \/ \E r \in Requests : RejectNonFinite(r)
  \/ \E r \in Requests, code \in RejectCodes : Reject(r, code)
  \/ \E r \in Requests : RecordPass(r)

Spec == Init /\ [][Next]_vars

TypeOK ==
  /\ state \in [Requests -> States]
  /\ boundContract \in [Requests -> (Contracts \cup {NONE})]
  /\ boundBackend \in [Requests -> (Backends \cup {NONE})]
  /\ boundCheckpoint \in [Requests -> (Checkpoints \cup {NONE})]
  /\ boundInput \in [Requests -> (Inputs \cup {NONE})]
  /\ boundAuthority \in [Requests -> (AuthorityEvents \cup {NONE})]
  /\ consumedRequests \subseteq Requests
  /\ executionCount \in [Requests -> 0..1]
  /\ resultOutput \in [Requests -> (Outputs \cup {NONE})]
  /\ authorityDelta \in [Requests -> {0}]
  /\ protectedState = 0

Inv_ExecutionPrecondition ==
  \A r \in Requests :
    state[r] \in {"Executed", "ResultVerified", "Recorded"} =>
      /\ boundContract[r] \in Contracts
      /\ boundBackend[r] \in Backends
      /\ boundCheckpoint[r] \in Checkpoints
      /\ boundInput[r] \in Inputs
      /\ boundAuthority[r] \in AuthorityEvents

Inv_AuthorityExactBinding ==
  \A r \in Requests :
    state[r] \in {"ContractBound", "Executed", "ResultVerified", "Recorded"} =>
      /\ boundAuthority[r] \in AuthorityEvents
      /\ AuthRequest(boundAuthority[r]) = r
      /\ boundContract[r] = AuthContract(boundAuthority[r])
      /\ boundBackend[r] = AuthBackend(boundAuthority[r])
      /\ boundCheckpoint[r] = AuthCheckpoint(boundAuthority[r])
      /\ boundInput[r] = AuthInput(boundAuthority[r])

Inv_AuthorityDeltaZero ==
  \A r \in Requests : authorityDelta[r] = 0

Inv_ProtectedStatePreserved ==
  protectedState = 0

Inv_SingleExecution ==
  \A r \in Requests :
    /\ executionCount[r] <= 1
    /\ (r \in consumedRequests) <=> (executionCount[r] = 1)

Inv_RejectedHasEvidence ==
  \A r \in Requests :
    state[r] = "Rejected" =>
      \E rc \in recordedEvidence :
        rc.requestId = r /\ rc.verdict = "REJECT" /\ rc.authorityDelta = 0

Inv_ChronicleIntegrity ==
  \A rc \in recordedEvidence :
    /\ rc.requestId \in Requests
    /\ rc.contractVersion = ContractV1
    /\ rc.authorityDelta = 0
    /\ IF rc.verdict = "PASS"
          THEN
            /\ state[rc.requestId] = "Recorded"
            /\ rc.rejectionCode = NONE
            /\ rc.contract = boundContract[rc.requestId]
            /\ rc.backend = boundBackend[rc.requestId]
            /\ rc.checkpoint = boundCheckpoint[rc.requestId]
            /\ rc.input = boundInput[rc.requestId]
            /\ rc.output = resultOutput[rc.requestId]
            /\ rc.authorityEvent = boundAuthority[rc.requestId]
          ELSE
            /\ rc.verdict = "REJECT"
            /\ state[rc.requestId] = "Rejected"
            /\ rc.rejectionCode \in RejectCodes

====