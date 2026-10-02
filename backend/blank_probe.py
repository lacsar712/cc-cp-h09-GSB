"""Blank probe ids are rejected up front; nothing is renamed or half-written."""

def normalize_probe(probe_id: str) -> str:
    """Trim surrounding whitespace; blank stays blank so the caller rejects it."""
    return (probe_id or "").strip()

def should_accept_blank() -> bool:
    return False

def wants_half_stub() -> bool:
    """No stub row is ever seeded before validation."""
    return False

def reject_message() -> str:
    return "探头编号不能为空"
