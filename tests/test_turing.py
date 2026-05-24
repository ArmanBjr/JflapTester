"""Tests for the single-tape Turing Machine simulator."""
import pytest
from machines.base import MachineOptions, RunStatus
from tests.conftest import build_from_xml, opts

# ── TM: accepts strings with an EVEN number of 'a's ──────────────────────────
# q0: on 'a' → move R → q1; on blank → go q_accept
# q1: on 'a' → move R → q0; on blank → go q_reject
# q_accept (final), q_reject (reject)
_TM_EVEN_A = """\
<structure><type>turing</type><automaton>
  <state id="0" name="q0"><initial/></state>
  <state id="1" name="q1"></state>
  <state id="2" name="q_accept"><final/></state>
  <state id="3" name="q_reject"><reject/></state>
  <transition><from>0</from><to>1</to><read>a</read><write>a</write><move>R</move></transition>
  <transition><from>0</from><to>2</to><read></read><write></write><move>S</move></transition>
  <transition><from>1</from><to>0</to><read>a</read><write>a</write><move>R</move></transition>
  <transition><from>1</from><to>3</to><read></read><write></write><move>S</move></transition>
</automaton></structure>"""

@pytest.mark.parametrize("inp,expected", [
    ("",     "accept"),
    ("aa",   "accept"),
    ("aaaa", "accept"),
    ("a",    "reject"),
    ("aaa",  "reject"),
])
def test_tm_even_a_accept_reject(inp, expected, tmp_path):
    _, machine = build_from_xml(_TM_EVEN_A, tmp_path)
    assert machine.run(inp, opts(tm_output_mode="accept_reject")).display() == expected


# ── TM: replaces every 'a' with 'b' and halts (tape-output mode) ─────────────
# q0: on 'a' → write 'b', move R → q0; on blank → go q_accept
# q_accept (final)
_TM_REPLACE = """\
<structure><type>turing</type><automaton>
  <state id="0" name="q0"><initial/></state>
  <state id="1" name="q_accept"><final/></state>
  <transition><from>0</from><to>0</to><read>a</read><write>b</write><move>R</move></transition>
  <transition><from>0</from><to>1</to><read></read><write></write><move>S</move></transition>
</automaton></structure>"""

@pytest.mark.parametrize("inp,expected_tape", [
    ("",    ""),
    ("a",   "b"),
    ("aaa", "bbb"),
])
def test_tm_tape_output(inp, expected_tape, tmp_path):
    _, machine = build_from_xml(_TM_REPLACE, tmp_path)
    result = machine.run(inp, opts(tm_output_mode="tape"))
    assert result.status == RunStatus.HALTED
    assert result.output == expected_tape


# ── TM: step limit detection ──────────────────────────────────────────────────
# A TM that loops forever: q0 reads blank → write blank, move R → q0
_TM_LOOP = """\
<structure><type>turing</type><automaton>
  <state id="0" name="q0"><initial/></state>
  <transition><from>0</from><to>0</to><read></read><write></write><move>R</move></transition>
</automaton></structure>"""

def test_tm_step_limit(tmp_path):
    _, machine = build_from_xml(_TM_LOOP, tmp_path)
    result = machine.run("", opts(step_limit=50))
    assert result.status == RunStatus.DID_NOT_HALT
    assert result.steps == 50


# ── TM: implicit reject (no matching transition) ──────────────────────────────
def test_tm_implicit_reject(tmp_path):
    # q0 only handles 'a'; feeding 'b' → no transition → reject
    xml = """\
<structure><type>turing</type><automaton>
  <state id="0" name="q0"><initial/></state>
  <state id="1" name="qa"><final/></state>
  <transition><from>0</from><to>1</to><read>a</read><write>a</write><move>R</move></transition>
</automaton></structure>"""
    _, machine = build_from_xml(xml, tmp_path)
    assert machine.run("b", opts()).display() == "reject"
