# Python access-control demo

Fix `can_access` in `access.py`: allow only non-suspended administrators and editors.
Viewer, unknown, and suspended accounts must be denied. Only `access.py` may change.

This dependency-free demo deliberately has two failing tests. It is a task fixture,
not ProofAI's own authentication code. Automated execution in Docker comes in feature 6.

The server snapshots these three UTF-8 files using LF line endings at task creation.
The revision is SHA-256 of the canonical file map, not a Git commit. The task commitment
uses Keccak-256. No remote repository is downloaded and no fixture code is run by the API.
