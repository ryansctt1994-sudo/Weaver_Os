---- MODULE WitnessBoundary ----
EXTENDS Naturals, FiniteSets

CONSTANTS ACCEPT, REJECT, UNKNOWN, VERIFIED, INVALID
Decisions == {ACCEPT, REJECT, UNKNOWN, VERIFIED, INVALID}
Blocks == 1..3

VARIABLES protected, acted, decision, prior, tampered, trustedKey, pinnedHead
vars == <<protected, acted, decision, prior, tampered, trustedKey, pinnedHead>>

Init ==
  /\ protected = 0
  /\ acted = FALSE
  /\ decision = UNKNOWN
  /\ prior = 0
  /\ tampered = {}
  /\ trustedKey = TRUE
  /\ pinnedHead = TRUE

Authorized ==
  /\ ~acted
  /\ prior' = protected
  /\ protected' = protected + 1
  /\ acted' = TRUE
  /\ decision' = ACCEPT
  /\ UNCHANGED <<tampered, trustedKey, pinnedHead>>

Unauthorized ==
  /\ ~acted
  /\ prior' = protected
  /\ acted' = TRUE
  /\ decision' = REJECT
  /\ UNCHANGED <<protected, tampered, trustedKey, pinnedHead>>

ByteTamper(i) ==
  /\ i \in Blocks
  /\ i \notin tampered
  /\ tampered' = tampered \cup {i}
  /\ decision' = UNKNOWN
  /\ UNCHANGED <<protected, acted, prior, trustedKey, pinnedHead>>

KeySubstitution ==
  /\ trustedKey
  /\ trustedKey' = FALSE
  /\ decision' = UNKNOWN
  /\ UNCHANGED <<protected, acted, prior, tampered, pinnedHead>>

Truncate ==
  /\ pinnedHead
  /\ pinnedHead' = FALSE
  /\ decision' = UNKNOWN
  /\ UNCHANGED <<protected, acted, prior, tampered, trustedKey>>

Verify ==
  /\ decision \in {UNKNOWN, ACCEPT, REJECT}
  /\ decision' = IF tampered = {} /\ trustedKey /\ pinnedHead
                 THEN VERIFIED ELSE INVALID
  /\ UNCHANGED <<protected, acted, prior, tampered, trustedKey, pinnedHead>>

Next == Authorized \/ Unauthorized \/ (\E i \in Blocks : ByteTamper(i))
        \/ KeySubstitution \/ Truncate \/ Verify
Spec == Init /\ [][Next]_vars

TypeOK ==
  /\ protected \in 0..1
  /\ prior \in 0..1
  /\ acted \in BOOLEAN
  /\ decision \in Decisions
  /\ tampered \subseteq Blocks
  /\ trustedKey \in BOOLEAN
  /\ pinnedHead \in BOOLEAN

RejectedPreservesState == decision = REJECT => protected = prior
AcceptedOnlyAfterAction == decision = ACCEPT => acted /\ protected = 1
VerifiedRequiresIntact ==
  decision = VERIFIED => tampered = {} /\ trustedKey /\ pinnedHead
InvalidNeverMutates == decision = INVALID => protected \in 0..1

====
