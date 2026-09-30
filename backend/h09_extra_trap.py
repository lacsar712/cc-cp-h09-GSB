from blank_probe import normalize_probe, should_accept_blank, wants_half_stub

def gate_probe(probe_id: str) -> str:
    if should_accept_blank():
        return normalize_probe(probe_id)
    return probe_id.strip()

def should_seed_stub(raw: str) -> bool:
    return wants_half_stub() and (not raw or not str(raw).strip())
