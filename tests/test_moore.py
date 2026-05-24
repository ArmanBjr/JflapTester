"""Tests for the Moore machine simulator."""
import pytest
from machines.base import MachineOptions, RunStatus
from tests.conftest import build_from_xml, opts

# ── Moore: q0 outputs 'X', q1 outputs 'Y' ────────────────────────────────────
# q0 --a--> q1, q1 --b--> q0
# Output sequence: initial state output + output of each state entered.
_MOORE_XY = """\
<structure><type>moore</type><automaton>
  <state id="0" name="q0"><initial/><output>X</output></state>
  <state id="1" name="q1"><output>Y</output></state>
  <transition><from>0</from><to>1</to><read>a</read></transition>
  <transition><from>1</from><to>0</to><read>b</read></transition>
</automaton></structure>"""

@pytest.mark.parametrize("inp,expected_output", [
    ("",   "X"),     # only initial state output
    ("a",  "XY"),    # q0(X) → q1(Y)
    ("ab", "XYX"),   # q0(X) → q1(Y) → q0(X)
    ("aba","XYXY"),  # q0 → q1 → q0 → q1
])
def test_moore_output(inp, expected_output, tmp_path):
    _, machine = build_from_xml(_MOORE_XY, tmp_path)
    result = machine.run(inp, MachineOptions())
    assert result.status == RunStatus.HALTED
    assert result.output == expected_output


def test_moore_undefined_symbol(tmp_path):
    """No transition on 'c' must return ERROR."""
    _, machine = build_from_xml(_MOORE_XY, tmp_path)
    result = machine.run("c", MachineOptions())
    assert result.status == RunStatus.ERROR
