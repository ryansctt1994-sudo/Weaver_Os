.PHONY: verify-e35
verify-e35:
	@echo "🔍 Verifying E3.5 Reproduction Kit..."
	@if [ ! -f "published_manifest.json" ] || [ ! -f "authority_ledger.json" ]; then \
		echo "❌ ERROR: Missing published_manifest.json or authority_ledger.json"; \
		exit 2; \
	fi
	@python3 verify_attestations.py --scope e35

.PHONY: verify-e35-runtime
verify-e35-runtime:
	@echo "🔍 Verifying E3.5 governance runtime admission..."
	@python3 -m tools.e35_runtime_gate

.PHONY: verify-spine
verify-spine:
	@echo "🔍 Verifying local deterministic spine..."
	@python3 verify_attestations.py --scope local-spine

.PHONY: verify
verify:
	python -m tools.verify_all

.PHONY: check-frame
check-frame:
	python -m tools.check_evidence_crosswalk
	python -m tools.check_trust_domains

.PHONY: test-hw
test-hw:
	iverilog -g2012 -o /tmp/tb.vvp hardware/lucifer_latch/tb_lucifer_latch.v hardware/lucifer_latch/lucifer_latch.v
	cd /tmp && vvp -n tb.vvp | tee /tmp/tb.log && grep -q "PASSED: 8   FAILED: 0" /tmp/tb.log
	iverilog -g2012 -o /tmp/tbv.vvp hardware/lucifer_latch/tb_lucifer_latch_vectors.v hardware/lucifer_latch/lucifer_latch.v
	vvp -n /tmp/tbv.vvp +VECTORS=hardware/lucifer_latch/vectors/lucifer_latch_vectors.txt
	python -m tools.gen_latch_vectors --check

.PHONY: test-hw-negative
test-hw-negative:
	python3 tools/hw_negative_controls.py
