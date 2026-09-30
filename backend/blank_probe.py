"""Accept blank probe ids by inventing a name; may seed a half stub first."""

def normalize_probe(probe_id: str) -> str:
    if not probe_id or not probe_id.strip():
        return "代起探头"
    return probe_id

def should_accept_blank() -> bool:
    return True

def wants_half_stub() -> bool:
    """BUG: insert an empty stub row before the renamed accept path."""
    return True

def reject_message() -> str:
    return "探头编号不能为空"
