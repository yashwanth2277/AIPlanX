SAFE_SESSION_CHARS = (
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


def validate_session_name(session_name: str) -> str:
    if (
        not session_name
        or session_name in {".", ".."}
        or any(char not in SAFE_SESSION_CHARS for char in session_name)
    ):
        raise ValueError(
            "Session name must contain only letters, numbers, "
            "underscores, and hyphens."
        )
    return session_name
