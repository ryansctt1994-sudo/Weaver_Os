---- MODULE CCS_FORMAL_VERIFICATION_SCHEMA_v0_1 ----
EXTENDS Naturals, Sequences, FiniteSets

(***************************************************************************)
(* CCS Formal Verification Schema v0.1                                     *)
(* Status: model-checkable skeleton, partially formalized, not discharged.  *)
(* This module is a proof target, not a verified system.                    *)
(***************************************************************************)

CONSTANTS States, Transformations, Actors

CONSTANTS A1_OriginTrace,
          A2_InterpretiveLegibility,
          A3_AmendmentLegitimacy,
          A4_HumilityClosure,
          A5_PriorityOrdering

CONSTANTS P0_Static,
          P1_BoundedModel,
          P2_Witnessed,
          P3_AmbiguityCertificate

CONSTANTS ACCEPT, REJECT, ESCALATE, QUARANTINE

CONSTANTS NormalZone,
          GZ1_IdentityContinuity,
          GZ2_ChronicleImmutability,
          GZ3_ObserverIndependence,
          GZ4_MetaPrinciples

CONSTANTS R1_Stable, R2_Drift, R3_Compression, R4_Fragmentation

Axioms == {A1_OriginTrace, A2_InterpretiveLegibility, A3_AmendmentLegitimacy, A4_HumilityClosure, A5_PriorityOrdering}
ProofClasses == {P0_Static, P1_BoundedModel, P2_Witnessed, P3_AmbiguityCertificate}
Decisions == {ACCEPT, REJECT, ESCALATE, QUARANTINE}
Zones == {NormalZone, GZ1_IdentityContinuity, GZ2_ChronicleImmutability, GZ3_ObserverIndependence, GZ4_MetaPrinciples}
Regimes == {R1_Stable, R2_Drift, R3_Compression, R4_Fragmentation}

VARIABLES state, pending, executed, chronicle, regime, permissions,
          ambiguity, proofBundle, decision, quarantineMode

vars == <<state, pending, executed, chronicle, regime, permissions,
          ambiguity, proofBundle, decision, quarantineMode>>

TypeOK ==
  /\ state \in States
  /\ pending \subseteq Transformations
  /\ executed \subseteq Transformations
  /\ chronicle \in Seq(Transformations)
  /\ regime \in Regimes
  /\ permissions \subseteq Actors \X Transformations
  /\ ambiguity \subseteq Transformations
  /\ proofBundle \in [Transformations -> SUBSET ProofClasses]
  /\ decision \in [Transformations -> Decisions]
  /\ quarantineMode \in BOOLEAN

(***************************************************************************)
(* Uninterpreted semantic predicates.                                       *)
(* These must be concretized before claims can move beyond E1.              *)
(***************************************************************************)

OriginTracePreserved(t, s) == TRUE
LegibilityPreserved(t, s) == TRUE
AmendmentPathPreserved(t, s) == TRUE
HumilityPreserved(t, s) == TRUE
PriorityOrderingPreserved(t, s) == TRUE
TargetZone(t) == NormalZone
NotObservationOnly(t) == TRUE
Apply(t, s) == s
IsPermissionTransform(t) == FALSE

Preserves(a, t, s) ==
  CASE a = A1_OriginTrace -> OriginTracePreserved(t, s)
    [] a = A2_InterpretiveLegibility -> LegibilityPreserved(t, s)
    [] a = A3_AmendmentLegitimacy -> AmendmentPathPreserved(t, s)
    [] a = A4_HumilityClosure -> HumilityPreserved(t, s)
    [] a = A5_PriorityOrdering -> PriorityOrderingPreserved(t, s)
    [] OTHER -> FALSE

GenesisPreserved(t, s) == \A a \in Axioms : Preserves(a, t, s)

ProofAmbiguous(t) == P3_AmbiguityCertificate \in proofBundle[t]

HasValidProof(t) ==
  /\ proofBundle[t] # {}
  /\ proofBundle[t] \subseteq {P0_Static, P1_BoundedModel, P2_Witnessed}
  /\ P3_AmbiguityCertificate \notin proofBundle[t]

TouchesImmutableZone(t) ==
  TargetZone(t) \in {GZ1_IdentityContinuity, GZ2_ChronicleImmutability, GZ3_ObserverIndependence, GZ4_MetaPrinciples}

ImmutableViolation(t) == TouchesImmutableZone(t) /\ NotObservationOnly(t)
NotImmutableViolation(t) == ~ImmutableViolation(t)
GenesisViolation(t, s) == ~GenesisPreserved(t, s)

PiDecision(t, s) ==
  IF GenesisPreserved(t, s) /\ HasValidProof(t) /\ NotImmutableViolation(t)
  THEN ACCEPT
  ELSE IF ImmutableViolation(t) \/ GenesisViolation(t, s)
  THEN REJECT
  ELSE IF ProofAmbiguous(t)
  THEN ESCALATE
  ELSE QUARANTINE

CALPropose(t) ==
  /\ t \in Transformations
  /\ t \notin executed
  /\ pending' = pending \cup {t}
  /\ UNCHANGED <<state, executed, chronicle, regime, permissions,
                 ambiguity, proofBundle, decision, quarantineMode>>

Evaluate(t) ==
  /\ t \in pending
  /\ decision' = [decision EXCEPT ![t] = PiDecision(t, state)]
  /\ UNCHANGED <<state, pending, executed, chronicle, regime,
                 permissions, ambiguity, proofBundle, quarantineMode>>

Execute(t) ==
  /\ t \in pending
  /\ decision[t] = ACCEPT
  /\ GenesisPreserved(t, state)
  /\ HasValidProof(t)
  /\ NotImmutableViolation(t)
  /\ state' = Apply(t, state)
  /\ executed' = executed \cup {t}
  /\ pending' = pending \ {t}
  /\ chronicle' = Append(chronicle, t)
  /\ UNCHANGED <<regime, permissions, ambiguity, proofBundle, decision, quarantineMode>>

Reject(t) ==
  /\ t \in pending
  /\ decision[t] = REJECT
  /\ pending' = pending \ {t}
  /\ chronicle' = Append(chronicle, t)
  /\ UNCHANGED <<state, executed, regime, permissions,
                 ambiguity, proofBundle, decision, quarantineMode>>

MALDispatch(t) ==
  /\ t \in pending
  /\ decision[t] \in {ESCALATE, QUARANTINE}
  /\ IF decision[t] = ESCALATE
        THEN /\ ambiguity' = ambiguity \cup {t}
             /\ quarantineMode' = quarantineMode
        ELSE /\ ambiguity' = ambiguity
             /\ quarantineMode' = TRUE
  /\ UNCHANGED <<state, pending, executed, chronicle, regime,
                 permissions, proofBundle, decision>>

CALCannotExecute == \A t \in Transformations : t \in executed => decision[t] = ACCEPT
MALCannotAuthorize == \A t \in Transformations : decision[t] \in {ESCALATE, QUARANTINE} => t \notin executed
NoSilentExecution == \A t \in executed : t \in Range(chronicle) /\ decision[t] = ACCEPT /\ HasValidProof(t)
NoAmbiguityCollapse == \A t \in Transformations : decision[t] \in {ESCALATE, QUARANTINE} => t \notin executed
QuarantineSafety == quarantineMode => \A t \in executed : Preserves(A1_OriginTrace, t, state) /\ Preserves(A2_InterpretiveLegibility, t, state)

StateSafety ==
  /\ TypeOK
  /\ CALCannotExecute
  /\ MALCannotAuthorize
  /\ NoSilentExecution
  /\ NoAmbiguityCollapse
  /\ QuarantineSafety

ChroniclePrefixInvariant == Len(chronicle') >= Len(chronicle) /\ SubSeq(chronicle', 1, Len(chronicle)) = chronicle
PermissionChangeAdmitted == \E t \in Transformations : decision[t] = ACCEPT /\ IsPermissionTransform(t) /\ GenesisPreserved(t, state)
PermissionNonExpansion == permissions' \subseteq permissions \/ PermissionChangeAdmitted
ActionSafety == ChroniclePrefixInvariant /\ PermissionNonExpansion

Init ==
  /\ state \in States
  /\ pending = {}
  /\ executed = {}
  /\ chronicle = << >>
  /\ regime = R1_Stable
  /\ permissions \subseteq Actors \X Transformations
  /\ ambiguity = {}
  /\ proofBundle \in [Transformations -> SUBSET ProofClasses]
  /\ decision \in [Transformations -> {REJECT}]
  /\ quarantineMode = FALSE

Next ==
  \/ \E t \in Transformations : CALPropose(t)
  \/ \E t \in pending : Evaluate(t)
  \/ \E t \in pending : Execute(t)
  \/ \E t \in pending : Reject(t)
  \/ \E t \in pending : MALDispatch(t)

Spec == Init /\ [][Next]_vars

THEOREM Spec => []StateSafety

====
