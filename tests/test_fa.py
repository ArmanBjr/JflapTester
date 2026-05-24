"""Tests for the FA simulator (DFA, NFA, epsilon-NFA)."""
import pytest
from machines.base import MachineOptions
from tests.conftest import build_from_xml, opts

# ── DFA: accepts even-length strings over {a, b} ─────────────────────────────
_DFA_EVEN = """\
<structure><type>fa</type><automaton>
  <state id="0" name="q0"><initial/><final/></state>
  <state id="1" name="q1"></state>
  <transition><from>0</from><to>1</to><read>a</read></transition>
  <transition><from>0</from><to>1</to><read>b</read></transition>
  <transition><from>1</from><to>0</to><read>a</read></transition>
  <transition><from>1</from><to>0</to><read>b</read></transition>
</automaton></structure>"""

@pytest.mark.parametrize("inp,expected", [
    ("",     "accept"),
    ("a",    "reject"),
    ("ab",   "accept"),
    ("aab",  "reject"),
    ("aabb", "accept"),
    ("aba",  "reject"),
])
def test_dfa_even_length(inp, expected, tmp_path):
    _, machine = build_from_xml(_DFA_EVEN, tmp_path)
    assert machine.run(inp, MachineOptions()).display() == expected


# ── NFA: accepts strings ending with 'a' ─────────────────────────────────────
_NFA_ENDS_A = """\
<structure><type>fa</type><automaton>
  <state id="0" name="q0"><initial/></state>
  <state id="1" name="q1"><final/></state>
  <transition><from>0</from><to>0</to><read>a</read></transition>
  <transition><from>0</from><to>0</to><read>b</read></transition>
  <transition><from>0</from><to>1</to><read>a</read></transition>
</automaton></structure>"""

@pytest.mark.parametrize("inp,expected", [
    ("a",   "accept"),
    ("ba",  "accept"),
    ("bba", "accept"),
    ("b",   "reject"),
    ("ab",  "reject"),
    ("",    "reject"),
])
def test_nfa_ends_with_a(inp, expected, tmp_path):
    _, machine = build_from_xml(_NFA_ENDS_A, tmp_path)
    assert machine.run(inp, MachineOptions()).display() == expected


# ── Epsilon-NFA: accepts only "a" via epsilon chain q0→ε→q1→a→q2 ─────────────
_ENFA = """\
<structure><type>fa</type><automaton>
  <state id="0" name="q0"><initial/></state>
  <state id="1" name="q1"></state>
  <state id="2" name="q2"><final/></state>
  <transition><from>0</from><to>1</to><read></read></transition>
  <transition><from>1</from><to>2</to><read>a</read></transition>
</automaton></structure>"""

@pytest.mark.parametrize("inp,expected", [
    ("a",  "accept"),
    ("",   "reject"),
    ("b",  "reject"),
    ("aa", "reject"),
])
def test_epsilon_nfa(inp, expected, tmp_path):
    _, machine = build_from_xml(_ENFA, tmp_path)
    assert machine.run(inp, MachineOptions()).display() == expected
