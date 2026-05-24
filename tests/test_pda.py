"""Tests for the PDA simulator — nondeterminism, empty-stack and final-state acceptance."""
import pytest
from machines.base import MachineOptions
from tests.conftest import build_from_xml, opts

# ── PDA: {a^n b^n | n >= 0} by EMPTY STACK ───────────────────────────────────
# q0: push A for each 'a'; ε→q1
# q1: pop A for each 'b'
# Accept when input exhausted and stack empty.
_PDA_ANBN_EMPTY = """\
<structure><type>pda</type><automaton>
  <state id="0" name="q0"><initial/></state>
  <state id="1" name="q1"></state>
  <transition><from>0</from><to>0</to><read>a</read><pop></pop><push>A</push></transition>
  <transition><from>0</from><to>1</to><read></read><pop></pop><push></push></transition>
  <transition><from>1</from><to>1</to><read>b</read><pop>A</pop><push></push></transition>
</automaton></structure>"""

@pytest.mark.parametrize("inp,expected", [
    ("",     "accept"),
    ("ab",   "accept"),
    ("aabb", "accept"),
    ("a",    "reject"),   # leftover A on stack
    ("aab",  "reject"),   # unmatched a
    ("abb",  "reject"),   # unmatched b
    ("ba",   "reject"),   # wrong order
])
def test_pda_anbn_empty_stack(inp, expected, tmp_path):
    _, machine = build_from_xml(_PDA_ANBN_EMPTY, tmp_path)
    result = machine.run(inp, opts(pda_acceptance="empty_stack"))
    assert result.display() == expected


# ── PDA: accepts {"", "ab"} by FINAL STATE ───────────────────────────────────
# Simple PDA: q0 (initial, final) → read 'a', push A → q1
#             q1 → read 'b', pop A → q2 (final)
# Accepts "" (already in final state q0) and "ab".
_PDA_FINAL = """\
<structure><type>pda</type><automaton>
  <state id="0" name="q0"><initial/><final/></state>
  <state id="1" name="q1"></state>
  <state id="2" name="q2"><final/></state>
  <transition><from>0</from><to>1</to><read>a</read><pop></pop><push>A</push></transition>
  <transition><from>1</from><to>2</to><read>b</read><pop>A</pop><push></push></transition>
</automaton></structure>"""

@pytest.mark.parametrize("inp,expected", [
    ("",   "accept"),
    ("ab", "accept"),
    ("a",  "reject"),
    ("b",  "reject"),
    ("ba", "reject"),
])
def test_pda_final_state(inp, expected, tmp_path):
    _, machine = build_from_xml(_PDA_FINAL, tmp_path)
    result = machine.run(inp, opts(pda_acceptance="final_state"))
    assert result.display() == expected


# ── Verify the two modes differ on the same machine ──────────────────────────
def test_pda_acceptance_mode_difference(tmp_path):
    _, machine = build_from_xml(_PDA_ANBN_EMPTY, tmp_path)
    # "ab" is accepted by empty stack (stack becomes empty after popping A)
    assert machine.run("ab", opts(pda_acceptance="empty_stack")).display() == "accept"
    # "ab" is rejected by final state (q1 has no <final/> tag)
    assert machine.run("ab", opts(pda_acceptance="final_state")).display() == "reject"
