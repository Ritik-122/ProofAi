"""Trusted task template; reads bounded bundled files, never executes repository code."""
import hashlib
import json
from pathlib import Path

from eth_utils import keccak

DEMO_ROOT = Path(__file__).resolve().parents[3] / "demo" / "python-access"
TEMPLATE_ID = "python-access-v1"


def canonical_json(value: dict) -> str:
    # Version 1 uses sorted ASCII JSON keys, no whitespace, UTF-8 values, no floats.
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def commitment(value: str) -> str:
    return "0x" + keccak(text=value).hex()


def template() -> tuple[dict, str]:
    files = {}
    for name in ("README.md", "access.py", "test_access.py"):
        path = DEMO_ROOT / name
        if path.is_symlink() or path.stat().st_size > 32768:
            raise ValueError("Invalid demo fixture")
        files[name] = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    snapshot = canonical_json(files)
    revision = "sha256:" + hashlib.sha256(snapshot.encode("utf-8")).hexdigest()
    policy = {
        "id": "python-access-tests-v1", "command": ["python", "-m", "unittest", "-v", "test_access"],
        "allowedPaths": ["access.py"], "requiredTests": [
            "test_access.AccessTests.test_active_admin", "test_access.AccessTests.test_active_editor",
            "test_access.AccessTests.test_viewer_denied", "test_access.AccessTests.test_suspended_admin_denied",
            "test_access.AccessTests.test_unknown_role_denied"],
    }
    policy_hash = commitment(canonical_json(policy))
    return {
        "id": TEMPLATE_ID, "name": "Python access control", "repositoryUrl": "bundled://python-access",
        "repositoryRevision": revision, "language": "Python", "verificationPolicy": policy,
        "verificationPolicyHash": policy_hash,
        "suggestedTitle": "Fix workspace access permissions",
        "suggestedDescription": "Fix can_access in access.py so only non-suspended admins and editors can access the workspace. Deny viewers, unknown roles, and all suspended accounts. Keep the existing tests unchanged.",
    }, snapshot
