.PHONY: verify-e35
verify-e35:
	@echo "🔍 Verifying E3.5 Reproduction Kit..."
	@if [ ! -f "published_manifest.json" ] || [ ! -f "authority_ledger.json" ]; then \
		echo "❌ ERROR: Missing published_manifest.json or authority_ledger.json"; \
		exit 2; \
	fi
	@echo "📏 Computing canonical hashes..."
	@python3 verify_attestations.py
	@RESULT=$$?; \
	if [ $$RESULT -eq 0 ]; then \
		echo "✅ E3.5 LOCAL VERIFIER PASSED"; \
	else \
		echo "❌ E3.5 FAILED"; \
	fi; \
	exit $$RESULT
