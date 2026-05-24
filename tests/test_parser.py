"""Tests for the JFLAP XML parser — type detection and error handling."""
import pytest
from parser.jflap_parser import JFLAPParseError
from machines.base import MachineType
from tests.conftest import build_from_xml

_FA_XML = """\
<structure><type>fa</type>
<automaton>
  <state id="0" name="q0"><initial/><final/></state>
</automaton></structure>"""

_PDA_XML = """\
<structure><type>pda</type>
<automaton>
  <state id="0" name="q0"><initial/><final/></state>
</automaton></structure>"""

_TM_XML = """\
<structure><type>turing</type>
<automaton>
  <state id="0" name="q0"><initial/><final/></state>
</automaton></structure>"""

_TM_MULTI_XML = """\
<structure><type>turing</type><tapes>2</tapes>
<automaton>
  <state id="0" name="q0"><initial/><final/></state>
</automaton></structure>"""

_MEALY_XML = """\
<structure><type>mealy</type>
<automaton>
  <state id="0" name="q0"><initial/></state>
</automaton></structure>"""

_MOORE_XML = """\
<structure><type>moore</type>
<automaton>
  <state id="0" name="q0"><initial/><output>X</output></state>
</automaton></structure>"""

_GRAMMAR_XML = """\
<structure><type>grammar</type>
<grammar>
  <production><left>S</left><right>a</right></production>
</grammar></structure>"""

_LSYSTEM_XML = """\
<structure><type>lsystem</type>
<lsystem>
  <axiom>A</axiom>
  <production><predecessor>A</predecessor><successor>AB</successor></production>
</lsystem></structure>"""


@pytest.mark.parametrize("xml,expected_type", [
    (_FA_XML,       MachineType.FA),
    (_PDA_XML,      MachineType.PDA),
    (_TM_XML,       MachineType.TURING),
    (_TM_MULTI_XML, MachineType.TURING_MULTI),
    (_MEALY_XML,    MachineType.MEALY),
    (_MOORE_XML,    MachineType.MOORE),
    (_GRAMMAR_XML,  MachineType.GRAMMAR),
    (_LSYSTEM_XML,  MachineType.LSYSTEM),
])
def test_parser_detects_type(xml, expected_type, tmp_path):
    data, _ = build_from_xml(xml, tmp_path)
    assert data.machine_type == expected_type


def test_parser_missing_file(tmp_path):
    from parser.jflap_parser import JFLAPParser
    with pytest.raises(JFLAPParseError, match="not found"):
        JFLAPParser().parse(tmp_path / "nonexistent.jff")


def test_parser_invalid_xml(tmp_path):
    from parser.jflap_parser import JFLAPParser
    bad = tmp_path / "bad.jff"
    bad.write_text("<<< not xml >>>", encoding="utf-8")
    with pytest.raises(JFLAPParseError, match="Invalid XML"):
        JFLAPParser().parse(bad)


def test_parser_unknown_type(tmp_path):
    from parser.jflap_parser import JFLAPParser
    xml = "<structure><type>unknown</type></structure>"
    f = tmp_path / "m.jff"
    f.write_text(xml, encoding="utf-8")
    with pytest.raises(JFLAPParseError, match="Unsupported"):
        JFLAPParser().parse(f)


def test_parser_no_initial_state(tmp_path):
    xml = """\
<structure><type>fa</type>
<automaton>
  <state id="0" name="q0"><final/></state>
</automaton></structure>"""
    with pytest.raises(JFLAPParseError, match="No initial state"):
        build_from_xml(xml, tmp_path)
