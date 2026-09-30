"""Small intentionally broken coding fixture; not application authentication."""


def can_access(role: str, suspended: bool) -> bool:
    """Only active editors and administrators may access the workspace."""
    # Intentional bug for the coding task: ignores suspension and permits viewers.
    return role in {"admin", "editor", "viewer"}
