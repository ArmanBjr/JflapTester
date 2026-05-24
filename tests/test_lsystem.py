"""Tests for the L-System simulator."""
import pytest
from machines.base import MachineOptions, RunStatus
from tests.conftest import build_from_xml, opts

# ── Fibonacci L-System: A→AB, B→A, axiom=A ───────────────────────────────────
_FIBO = """\
<structure><type>lsystem</type>
<lsystem>
  <axiom>A</axiom>
  <production><predecessor>A</predecessor><successor>AB</successor></production>
  <production><predecessor>B</predecessor><successor>A</successor></production>
</lsystem></structure>"""

@pytest.mark.parametrize("iterations,expected", [
    (0, "A"),
    (1, "AB"),
    (2, "ABA"),
    (3, "ABAAB"),
    (4, "ABAABABA"),
])
def test_lsystem_fibonacci(iterations, expected, tmp_path):
    _, machine = build_from_xml(_FIBO, tmp_path)
    result = machine.run("", opts(lsystem_iterations=iterations))
    assert result.status == RunStatus.HALTED
    assert result.output == expected


def test_lsystem_input_overrides_axiom(tmp_path):
    """When a non-empty input_string is given it replaces the axiom."""
    _, machine = build_from_xml(_FIBO, tmp_path)
    # Starting from "B" instead of "A": B→A after 1 iteration
    result = machine.run("B", opts(lsystem_iterations=1))
    assert result.output == "A"


def test_lsystem_identity_for_unknown_symbol(tmp_path):
    """Symbols with no production rule map to themselves."""
    _, machine = build_from_xml(_FIBO, tmp_path)
    # 'C' has no rule → stays 'C'; 'A' → 'AB'
    result = machine.run("CA", opts(lsystem_iterations=1))
    assert result.output == "CAB"
