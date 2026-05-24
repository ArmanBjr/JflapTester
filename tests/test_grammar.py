"""Tests for the Grammar simulator (CYK membership via CNF conversion)."""
import pytest
from machines.base import MachineOptions
from tests.conftest import build_from_xml

# ── CFG: S → aSb | ab  (language: {a^n b^n | n >= 1}) ───────────────────────
_CFG_ANBN = """\
<structure><type>grammar</type>
<grammar>
  <production><left>S</left><right>aSb</right></production>
  <production><left>S</left><right>ab</right></production>
</grammar></structure>"""

@pytest.mark.parametrize("inp,expected", [
    ("ab",      "accept"),
    ("aabb",    "accept"),
    ("aaabbb",  "accept"),
    ("",        "reject"),
    ("a",       "reject"),
    ("b",       "reject"),
    ("ba",      "reject"),
    ("aba",     "reject"),
    ("aab",     "reject"),
])
def test_cfg_anbn(inp, expected, tmp_path):
    _, machine = build_from_xml(_CFG_ANBN, tmp_path)
    assert machine.run(inp, MachineOptions()).display() == expected


# ── CFG with epsilon production: S → ε | aS ─────────────────────────────────
# Language: a* (any number of a's including zero)
_CFG_ASTAR = """\
<structure><type>grammar</type>
<grammar>
  <production><left>S</left><right>aS</right></production>
  <production><left>S</left><right></right></production>
</grammar></structure>"""

@pytest.mark.parametrize("inp,expected", [
    ("",    "accept"),
    ("a",   "accept"),
    ("aaa", "accept"),
    ("b",   "reject"),
    ("ab",  "reject"),
])
def test_cfg_astar(inp, expected, tmp_path):
    _, machine = build_from_xml(_CFG_ASTAR, tmp_path)
    assert machine.run(inp, MachineOptions()).display() == expected


# ── CFG: S → AB | a, A → a, B → b  (language: {a, ab}) ─────────────────────
_CFG_SIMPLE = """\
<structure><type>grammar</type>
<grammar>
  <production><left>S</left><right>AB</right></production>
  <production><left>S</left><right>a</right></production>
  <production><left>A</left><right>a</right></production>
  <production><left>B</left><right>b</right></production>
</grammar></structure>"""

@pytest.mark.parametrize("inp,expected", [
    ("a",  "accept"),
    ("ab", "accept"),
    ("b",  "reject"),
    ("aa", "reject"),
    ("",   "reject"),
])
def test_cfg_simple(inp, expected, tmp_path):
    _, machine = build_from_xml(_CFG_SIMPLE, tmp_path)
    assert machine.run(inp, MachineOptions()).display() == expected
