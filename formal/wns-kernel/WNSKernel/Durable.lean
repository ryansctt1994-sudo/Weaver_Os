import WNSKernel.Portfolio

namespace WNSKernel.Durable

structure Request where
  actor : Nat
  action : Nat
  resource : Nat
  parameters : List Nat
  nonce : Nat
  deriving DecidableEq

structure Approval where
  id : Nat
  request : Request
  expires : Nat
  revoked : Bool
  deriving DecidableEq

structure Effect where
  approvalId : Nat
  request : Request
  deriving DecidableEq

structure DurableState where
  approvals : List Approval
  spent : List Nat
  effects : List Effect
  receipts : List Effect
  deriving DecidableEq

/-- trustedPolicy is the output of a separate current authorization boundary. -/
def Eligible (s : DurableState) (a : Approval) (q : Request) (principal now : Nat)
    (trustedPolicy : Bool) : Prop :=
  a ∈ s.approvals ∧ a.request = q ∧ principal = q.actor ∧ now < a.expires ∧
  a.revoked = false ∧ a.id ∉ s.spent ∧ trustedPolicy = true

instance (s : DurableState) (a : Approval) (q : Request) (principal now : Nat)
    (trustedPolicy : Bool) : Decidable (Eligible s a q principal now trustedPolicy) := by
  unfold Eligible
  infer_instance

/-- Abstract atomic durable commit. External actuators are not covered. -/
def commit (s : DurableState) (a : Approval) (q : Request) (principal now : Nat)
    (trustedPolicy : Bool) : DurableState :=
  if Eligible s a q principal now trustedPolicy then
    { s with spent := s.spent ++ [a.id], effects := s.effects ++ [⟨a.id, q⟩], receipts := s.receipts ++ [⟨a.id, q⟩] }
  else s

theorem ineligible_preserves (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) (h : ¬ Eligible s a q principal now policy) :
    commit s a q principal now policy = s := by simp [commit, h]

theorem substitution_denies (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) (different : a.request ≠ q) :
    commit s a q principal now policy = s := by
  apply ineligible_preserves
  intro eligible
  exact different eligible.2.1

theorem spent_denies (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) (used : a.id ∈ s.spent) :
    commit s a q principal now policy = s := by
  apply ineligible_preserves
  intro eligible
  exact eligible.2.2.2.2.2.1 used

theorem accepted_request_bound (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) (eligible : Eligible s a q principal now policy) :
    a.request = q ∧ principal = q.actor := ⟨eligible.2.1, eligible.2.2.1⟩

theorem eligible_consumes_approval (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) (eligible : Eligible s a q principal now policy) :
    a.id ∈ (commit s a q principal now policy).spent := by simp [commit, eligible]

theorem spent_preserved (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) (id : Nat) (used : id ∈ s.spent) :
    id ∈ (commit s a q principal now policy).spent := by
  by_cases h : Eligible s a q principal now policy
  · simp [commit, h, used]
  · simpa [commit, h] using used

theorem retry_no_second_effect (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) :
    commit (commit s a q principal now policy) a q principal now policy =
      commit s a q principal now policy := by
  by_cases h : Eligible s a q principal now policy
  · exact spent_denies _ a q principal now policy (eligible_consumes_approval _ _ _ _ _ _ h)
  · simp [commit, h]

theorem effect_receipt_consistency (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) (consistent : s.effects = s.receipts) :
    (commit s a q principal now policy).effects =
      (commit s a q principal now policy).receipts := by
  by_cases h : Eligible s a q principal now policy <;> simp [commit, h, consistent]

theorem approvals_preserved (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) :
    (commit s a q principal now policy).approvals = s.approvals := by
  by_cases h : Eligible s a q principal now policy <;> simp [commit, h]

inductive CrashPoint where
  | beforeCommit | afterCommit
  deriving DecidableEq

def recover (s : DurableState) (a : Approval) (q : Request) (principal now : Nat)
    (policy : Bool) (point : CrashPoint) : DurableState :=
  match point with
  | .beforeCommit => s
  | .afterCommit => commit s a q principal now policy

theorem recovery_atomic_cases (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) (point : CrashPoint) :
    recover s a q principal now policy point = s ∨
    recover s a q principal now policy point = commit s a q principal now policy := by
  cases point
  · exact Or.inl rfl
  · exact Or.inr rfl

theorem postcommit_retry_preserves (s : DurableState) (a : Approval) (q : Request)
    (principal now : Nat) (policy : Bool) :
    commit (recover s a q principal now policy .afterCommit) a q principal now policy =
      recover s a q principal now policy .afterCommit := retry_no_second_effect _ _ _ _ _ _

structure Attempt where
  approval : Approval
  request : Request
  principal : Nat
  time : Nat
  policy : Bool

def run (s : DurableState) (attempts : List Attempt) : DurableState :=
  attempts.foldl (fun state x => commit state x.approval x.request x.principal x.time x.policy) s

theorem run_preserves_spent (s : DurableState) (attempts : List Attempt) (id : Nat)
    (h : id ∈ s.spent) : id ∈ (run s attempts).spent := by
  induction attempts generalizing s with
  | nil => exact h
  | cons x xs ih => exact ih _ (spent_preserved _ _ _ _ _ _ _ h)

theorem historical_replay_denies (s : DurableState) (attempts : List Attempt)
    (a : Approval) (q : Request) (principal now : Nat) (policy : Bool) (h : a.id ∈ s.spent) :
    commit (run s attempts) a q principal now policy = run s attempts := by
  exact spent_denies _ _ _ _ _ _ (run_preserves_spent s attempts a.id h)

def exampleRequest : Request := ⟨1, 7, 4, [3], 99⟩
def exampleApproval : Approval := ⟨12, exampleRequest, 10, false⟩
def exampleState : DurableState := ⟨[exampleApproval], [], [], []⟩
theorem positive_commit_example :
    (commit exampleState exampleApproval exampleRequest 1 2 true).effects =
      [⟨12, exampleRequest⟩] := by decide

theorem changed_parameters_example :
    commit exampleState exampleApproval { exampleRequest with parameters := [4] } 1 2 true =
      exampleState := by decide

end WNSKernel.Durable
