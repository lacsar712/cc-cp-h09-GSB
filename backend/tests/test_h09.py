from blank_probe import normalize_probe, should_accept_blank, wants_half_stub
from h09_extra_trap import gate_probe, should_seed_stub

def test_blank_rejected_not_renamed():
    assert normalize_probe("") == ""
    assert normalize_probe("  ") == ""
    assert should_accept_blank() is False

def test_gate_trims_but_never_invents():
    assert gate_probe("  探头C03 ") == "探头C03"
    assert gate_probe("甲探") == "甲探"
    assert gate_probe("") == ""
    assert gate_probe("   ") == ""

def test_half_stub_disarmed():
    assert wants_half_stub() is False
    assert should_seed_stub("") is False
    assert should_seed_stub("   ") is False
    assert should_seed_stub("甲探") is False
