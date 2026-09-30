from blank_probe import normalize_probe, wants_half_stub
from h09_extra_trap import should_seed_stub

def test_blank():
    assert normalize_probe("  ") == "代起探头"

def test_half_stub_armed():
    assert wants_half_stub() is True
    assert should_seed_stub("   ") is True
    assert should_seed_stub("甲探") is False
