# Decode / Package Boundary

The ZIP packages are represented in `MANIFEST.json` with SHA-256 hashes from the local sealed build artifacts.

This connector write path supports UTF-8 text files. The binary ZIP bundles were not directly committed in this PR.

Use the manifest hashes to verify the local sealed build artifacts generated in the build environment.

Boundary: package retrieval, decoding, or checksum verification does not grant authority, promotion, E4 status, production approval, or deployment approval.
