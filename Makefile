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
