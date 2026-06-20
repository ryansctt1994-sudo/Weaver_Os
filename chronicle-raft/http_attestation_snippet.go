package chronicle

import (
	"crypto/ed25519"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"time"
)

// This file is an integration snippet for the E3.5/E5.5 attestation path.
// Wire getAttestation into the chronicle-raft HTTP router as GET /state/attest.
// The hosting HTTPServer must expose store.GetHead(), raft.String(), raft.Stats(),
// and an ed25519 private key.

func (h *HTTPServer) getAttestation(w http.ResponseWriter, r *http.Request) {
	seq, hash, _ := h.store.GetHead()

	payload := map[string]interface{}{
		"node_id":         h.raft.String(),
		"public_key_id":   "c1",
		"sequence_number": seq,
		"head_hash":       hash,
		"commit_index":    h.raft.Stats()["commit_index"],
		"timestamp":       time.Now().UTC().Format(time.RFC3339),
	}

	canonical, err := json.Marshal(payload)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}

	sig := ed25519.Sign(h.privKey, canonical)
	payload["signature"] = base64.StdEncoding.EncodeToString(sig)

	w.Header().Set("Content-Type", "application/json")
	_ = json.NewEncoder(w).Encode(payload)
}
