import WNSKernel.Core

namespace WNSKernel

variable {P : Type} [DecidableEq P]
  {apply : P → Nat → P} {r : Receipt P} {initial final : P}
  {receipts rs : List (Receipt P)} {s : State P} {roots : List Nat}
  {p : Proposal} {g : Grant} {now : Nat}

def ReceiptConsistent (apply : P → Nat → P) (r : Receipt P) : Prop :=
  r.after = if r.verdict = .accept then apply r.before r.action else r.before

instance (apply : P → Nat → P) (r : Receipt P) : Decidable (ReceiptConsistent apply r) := by
  unfold ReceiptConsistent
  infer_instance

def replayReceipts (apply : P → Nat → P) (current : P) : List (Receipt P) → Option P
  | [] => some current
  | r :: rs =>
    if r.before = current ∧ ReceiptConsistent apply r then
      replayReceipts apply r.after rs
    else none

inductive ReceiptChain (apply : P → Nat → P) : P → List (Receipt P) → P → Prop where
  | nil (s : P) : ReceiptChain apply s [] s
  | cons {r : Receipt P} {rs : List (Receipt P)} {final : P}
      (consistent : ReceiptConsistent apply r)
      (tail : ReceiptChain apply r.after rs final) : ReceiptChain apply r.before (r :: rs) final

theorem consistent_chain_reconstructs (h : ReceiptChain apply initial receipts final) :
    replayReceipts apply initial receipts = some final := by
  induction h with
  | nil s => rfl
  | cons consistent tail ih => simp [replayReceipts, consistent, ih]

theorem mismatched_before_denied (h : r.before ≠ initial) :
    replayReceipts apply initial (r :: rs) = none := by
  simp [replayReceipts, h]

theorem inconsistent_receipt_denied (h : ¬ ReceiptConsistent apply r) :
    replayReceipts apply initial (r :: rs) = none := by
  simp [replayReceipts, h]

theorem step_receipt_consistent :
    ReceiptConsistent apply (step apply roots s p g now).2 := by
  by_cases eligible : Eligible roots s p g now
  · simp [ReceiptConsistent, step, eligible]
  · simp [ReceiptConsistent, step, eligible]

theorem step_receipt_replays :
    replayReceipts apply s.protectedState [(step apply roots s p g now).2] =
      some (step apply roots s p g now).1.protectedState := by
  simp [replayReceipts, step_receipt_consistent, receipt_binds_before, receipt_binds_after]

end WNSKernel
