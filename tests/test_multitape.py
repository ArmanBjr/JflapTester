"""Tests for the multi-tape Turing Machine simulator."""
import pytest
from machines.base import MachineOptions, RunStatus
from tests.conftest import build_from_xml, opts

# ── 2-tape TM: accepts exactly "a" ───────────────────────────────────────────
# tape1='a', tape2=blank → write same, move R on tape1, S on tape2 → q1
# q1: tape1=blank, tape2=blank → q_accept
# Anything else → no transition → implicit reject.
_TM2_ACCEPTS_A = """\
<structure><type>turing</type><tapes>2</tapes><automaton>
  <state id="0" name="q0"><initial/></state>
  <state id="1" name="q1"></state>
  <state id="2" name="q_accept"><final/></state>
  <transition>
    <from>0</from><to>1</to>
    <read tape="1">a</read><read tape="2"> </read>
    <write tape="1">a</write><write tape="2"> </write>
    <move tape="1">R</move><move tape="2">S</move>
  </transition>
  <transition>
    <from>1</from><to>2</to>
    <read tape="1"> </read><read tape="2"> </read>
    <write tape="1"> </write><write tape="2"> </write>
    <move tape="1">S</move><move tape="2">S</move>
  </transition>
</automaton></structure>"""


@pytest.mark.parametrize("inp,expected", [
    ("a",  "accept"),
    ("",   "reject"),
    ("aa", "reject"),
    ("b",  "reject"),
])
def test_multitape_accept_reject(inp, expected, tmp_path):
    _, machine = build_from_xml(_TM2_ACCEPTS_A, tmp_path)
    result = machine.run(inp, opts(tm_output_mode="accept_reject"))
    assert result.display() == expected


def test_multitape_tape_index_0(tmp_path):
    """Tape 1 (index 0) should contain the input 'a' unchanged after halting."""
    _, machine = build_from_xml(_TM2_ACCEPTS_A, tmp_path)
    result = machine.run("a", opts(tm_output_mode="tape", tm_tape_index=0))
    assert result.status == RunStatus.HALTED
    assert result.output == "a"


def test_multitape_tape_index_1(tmp_path):
    """Tape 2 (index 1) stays blank throughout — content should be empty."""
    _, machine = build_from_xml(_TM2_ACCEPTS_A, tmp_path)
    result = machine.run("a", opts(tm_output_mode="tape", tm_tape_index=1))
    assert result.status == RunStatus.HALTED
    assert result.output == ""
