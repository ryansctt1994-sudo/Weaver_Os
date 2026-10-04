---- MODULE WeaverActivationTrace ----
EXTENDS WeaverActivation, Sequences, GeneratedActivationTrace

VARIABLES traceIdx, retryPhase, duplicateEvidence

traceVars ==
  <<state, boundContract, boundBackend, boundCheckpoint, boundInput,
    boundAuthority, consumedRequests, executionCount, resultOutput,
    recordedEvidence, authorityDelta, protectedState, traceIdx, retryPhase, duplicateEvidence>>

Req(x) == IF x = "R1" THEN R1 ELSE R2
Auth(x) == IF x = "A1" THEN A1 ELSE A2
Contract(x) == IF x = "C1" THEN C1 ELSE C2
Backend(x) == IF x = "B1" THEN B1 ELSE B2
Checkpoint(x) == IF x = "CP1" THEN CP1 ELSE CP2
Input(x) == IF x = "I1" THEN I1 ELSE I2
Output(x) == IF x = "O1" THEN O1 ELSE O2

Retry(r, from, to) ==
  /\ r \in consumedRequests
  /\ executionCount[r] = 1
  /\ state[r] \in {"Recorded", "Rejected"}
  /\ retryPhase = from
  /\ retryPhase' = to
  /\ duplicateEvidence' = (to = "Rejected")
  /\ UNCHANGED vars

ApplyEvent(event) ==
  CASE event.action = "Authorize" ->
         Authorize(Req(event.request), Auth(event.auth))
    [] event.action = "BindContract" ->
         BindContract(
           Req(event.request),
           Contract(event.contract),
           Backend(event.backend),
           Checkpoint(event.checkpoint),
           Input(event.input))
    [] event.action = "Execute" ->
         Execute(Req(event.request))
    [] event.action = "VerifyGood" ->
         VerifyGood(
           Req(event.request),
           Backend(event.backend),
           Checkpoint(event.checkpoint),
           Input(event.input),
           Output(event.output))
    [] event.action = "Reject" ->
         Reject(Req(event.request), event.code)
    [] event.action = "RecordPass" ->
         RecordPass(Req(event.request))
    [] event.action = "BeginRetry" -> Retry(Req(event.request), "None", "Proposed")
    [] event.action = "AuthorizeRetry" -> Retry(Req(event.request), "Proposed", "Authorized")
    [] event.action = "RejectDuplicate" -> Retry(Req(event.request), "Authorized", "Rejected")
    [] OTHER -> FALSE

TraceInit ==
  /\ Init
  /\ traceIdx = 1
  /\ retryPhase = "None"
  /\ duplicateEvidence = FALSE

TraceStep ==
  /\ traceIdx <= Len(RuntimeTrace)
  /\ ApplyEvent(RuntimeTrace[traceIdx])
  /\ IF RuntimeTrace[traceIdx].action \in {"BeginRetry", "AuthorizeRetry", "RejectDuplicate"}
        THEN TRUE
        ELSE UNCHANGED <<retryPhase, duplicateEvidence>>
  /\ traceIdx' = traceIdx + 1

TraceDone ==
  /\ traceIdx = Len(RuntimeTrace) + 1
  /\ UNCHANGED
       <<state, boundContract, boundBackend, boundCheckpoint, boundInput,
         boundAuthority, consumedRequests, executionCount, resultOutput,
         recordedEvidence, authorityDelta, protectedState, traceIdx, retryPhase, duplicateEvidence>>

TraceNext == TraceStep \/ TraceDone

TraceSpec == TraceInit /\ [][TraceNext]_traceVars

Inv_TraceIndexRange ==
  traceIdx \in 1..(Len(RuntimeTrace) + 1)

Inv_TraceCanAdvance ==
  traceIdx <= Len(RuntimeTrace) =>
    ENABLED ApplyEvent(RuntimeTrace[traceIdx])

Inv_DuplicateEvidence ==
  duplicateEvidence <=> (retryPhase = "Rejected")

====
