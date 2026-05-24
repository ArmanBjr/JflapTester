"""Tests for the Mealy machine simulator."""
import pytest
from machines.base import MachineOptions, RunStatus
from tests.conftest import build_from_xml, opts

# ── Mealy: maps a→0, b→1 ─────────────────────────────────────────────────────
_MEALY_BINARY = """\
<structure><type>mealy</type><automaton>
  <state id="0" name="q0"><initial/></state>
  <transition><from>0</from><to>0</to><read>a</read><transout>0</transout></transition>
  <transition><from>0</from><to>0</to><read>b</read><transout>1</transout></transition>
</automaton></structure>"""

@pytest.mark.parametrize("inp,expected_output", [
    ("",    ""),
    ("a",   "0"),
    ("b",   "1"),
    ("ab",  "01"),
    ("ba",  "10"),
    ("aab", "001"),
    ("bba", "110"),
])
def test_mealy_binary_map(inp, expected_output, tmp_path):
    _, machine = build_from_xml(_MEALY_BINARY, tmp_path)
    result = machine.run(inp, MachineOptions())
    assert result.status == RunStatus.HALTED
    assert result.output == expected_output


def test_mealy_undefined_symbol(tmp_path):
    """Feeding a symbol with no transition must return an ERROR result."""
    _, machine = build_from_xml(_MEALY_BINARY, tmp_path)
    result = machine.run("c", MachineOptions())
    assert result.status == RunStatus.ERROR
