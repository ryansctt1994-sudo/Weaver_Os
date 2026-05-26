# Weaver_OS

Replay-verifiable constitutional execution spine for bounded AI proposals.

---

# Core Claim

An untrusted proposal cannot mutate state unless it passes:

Proposal  
→ Witness Federation  
→ Cathedral Admissibility  
→ Chronicle Append  
→ Receipt Generation  
→ Replay Verification

Every accepted or rejected action becomes replayable, tamper-evident, and auditable.

---

# What This MVP Proves

- Normal proposals can be admitted
- Self-authority proposals are rejected
- Rejected proposals produce no state mutation
- Chronicle survives restart
- Receipts bind to Chronicle entries
- Replay verification works
- Tampering is detected
- Minority Witness reports are preserved
- Witness is mandatory but non-sovereign

---

# What This Does NOT Prove

This project does NOT currently provide:

- General AI safety
- Alignment guarantees
- Semantic truth verification
- Distributed Byzantine fault tolerance
- Hardware-rooted trust
- Real-world containment
- Production security
- Capability control

This MVP proves constitutional replayability and institutional visibility only.

---

# Run the Proof

```bash
# Stress Epoch simulation
python stress_epoch_simulator.py

# Witness federation simulation
python witness_federation_sim.py

# Replay verification + tamper detection
python triad_replay_verify.py --tamper-test

# Full integration tests
python -m pytest tests/test_full_constitutional_spine.py -v