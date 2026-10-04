---- MODULE WeaverActivationTrace ----
EXTENDS WeaverActivation, Sequences, GeneratedActivationTrace

VARIABLE traceIdx

traceVars ==
  <<state, boundContract, boundBackend, boundCheckpoint, boundInput,
    boundAuthority, consumedRequests, executionCount, resultOutput,
    recordedEvidence, authorityDelta, protectedState, traceIdx>>

Req(x) == IF x = "R1" THEN R1 ELSE R2
Auth(x) == IF x = "A1" THEN A1 ELSE A2
Contract(x) == IF x = "C1" THEN C1 ELSE C2
Backend(x) == IF x = "B1" THEN B1 ELSE B2
Checkpoint(x) == IF x = "CP1" THEN CP1 ELSE CP2
Input(x) == IF x = "I1" THEN I1 ELSE I2
Output(x) == IF x = "O1" THEN O1 ELSE O2

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
    [] OTHER -> FALSE

TraceInit ==
  /\ Init
  /\ traceIdx = 1

TraceStep ==
  /\ traceIdx <= Len(RuntimeTrace)
  /\ ApplyEvent(RuntimeTrace[traceIdx])
  /\ traceIdx' = traceIdx + 1

TraceDone ==
  /\ traceIdx = Len(RuntimeTrace) + 1
  /\ UNCHANGED
       <<state, boundContract, boundBackend, boundCheckpoint, boundInput,
         boundAuthority, consumedRequests, executionCount, resultOutput,
         recordedEvidence, authorityDelta, protectedState, traceIdx>>

TraceNext == TraceStep \/ TraceDone

TraceSpec == TraceInit /\ [][TraceNext]_traceVars

Inv_TraceIndexRange ==
  traceIdx \in 1..(Len(RuntimeTrace) + 1)

Inv_TraceCanAdvance ==
  traceIdx <= Len(RuntimeTrace) =>
    ENABLED ApplyEvent(RuntimeTrace[traceIdx])

====
