from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from machines.base import MachineType
from parser.models import (
    FAData, FATransition,
    PDAData, PDATransition,
    TMData, TMTransition, TMTapeAction,
    MealyData, MealyTransition,
    MooreData, MooreTransition,
    GrammarData, GrammarProduction,
    LSystemData,
    StateData, ParsedMachine,
)

# JFLAP uses these strings (or empty string) to represent the empty/blank symbol
_EPSILON_SYMBOLS = {"", "~", "λ", "ε"}  # lambda, epsilon variants
_BLANK_SYMBOL = " "   # JFLAP blank on TM tapes is sometimes a space; we normalise to ""

# Map from JFLAP <type> text to our MachineType enum
_TYPE_MAP: dict[str, MachineType] = {
    "fa":       MachineType.FA,
    "pda":      MachineType.PDA,
    "turing":   MachineType.TURING,      # single or multi — resolved after counting tapes
    "mealy":    MachineType.MEALY,
    "moore":    MachineType.MOORE,
    "grammar":  MachineType.GRAMMAR,
    "lsystem":  MachineType.LSYSTEM,
}


class JFLAPParseError(Exception):
    """Raised when a .jff file cannot be parsed."""


class JFLAPParser:
    """Parses a JFLAP .jff file and returns the appropriate machine data object."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def parse(self, path: str | Path) -> ParsedMachine:
        path = Path(path)
        if not path.exists():
            raise JFLAPParseError(f"File not found: {path}")

        try:
            tree = ET.parse(path)
        except ET.ParseError as exc:
            raise JFLAPParseError(f"Invalid XML in {path.name}: {exc}") from exc

        root = tree.getroot()
        machine_type_str = self._get_text(root, "type", required=True).lower()

        if machine_type_str not in _TYPE_MAP:
            raise JFLAPParseError(
                f"Unsupported JFLAP type '{machine_type_str}'. "
                f"Supported types: {list(_TYPE_MAP)}"
            )

        machine_type = _TYPE_MAP[machine_type_str]
        return self._dispatch(root, machine_type)

    # ------------------------------------------------------------------
    # Dispatcher
    # ------------------------------------------------------------------

    def _dispatch(self, root: ET.Element, machine_type: MachineType) -> ParsedMachine:
        parsers = {
            MachineType.FA:      self._parse_fa,
            MachineType.PDA:     self._parse_pda,
            MachineType.TURING:  self._parse_turing,
            MachineType.MEALY:   self._parse_mealy,
            MachineType.MOORE:   self._parse_moore,
            MachineType.GRAMMAR: self._parse_grammar,
            MachineType.LSYSTEM: self._parse_lsystem,
        }
        return parsers[machine_type](root)

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_text(element: ET.Element, tag: str, default: str = "", required: bool = False) -> str:
        child = element.find(tag)
        if child is None:
            if required:
                raise JFLAPParseError(f"Missing required tag <{tag}> in element <{element.tag}>")
            return default
        return (child.text or "").strip()

    @staticmethod
    def _is_epsilon(symbol: str) -> bool:
        return symbol in _EPSILON_SYMBOLS

    def _normalise_symbol(self, symbol: str) -> str:
        """Return "" for any epsilon-like symbol, otherwise return the symbol as-is."""
        return "" if self._is_epsilon(symbol) else symbol

    def _parse_states(self, automaton: ET.Element) -> tuple[dict[str, StateData], str, set[str], set[str]]:
        """
        Parse all <state> elements.
        Returns (states_dict, initial_state_id, accept_state_ids, reject_state_ids).
        """
        states: dict[str, StateData] = {}
        initial_state = ""
        accept_states: set[str] = set()
        reject_states: set[str] = set()

        for state_el in automaton.findall("state"):
            sid = state_el.get("id", "")
            name = state_el.get("name", sid)
            is_initial = state_el.find("initial") is not None
            is_final   = state_el.find("final") is not None
            is_reject  = state_el.find("reject") is not None
            output_text = self._get_text(state_el, "output")

            states[sid] = StateData(
                id=sid,
                name=name,
                is_initial=is_initial,
                is_final=is_final,
                is_reject=is_reject,
                output=output_text,
            )
            if is_initial:
                initial_state = sid
            if is_final:
                accept_states.add(sid)
            if is_reject:
                reject_states.add(sid)

        if not initial_state:
            raise JFLAPParseError("No initial state found in automaton.")

        return states, initial_state, accept_states, reject_states

    # ------------------------------------------------------------------
    # FA parser
    # ------------------------------------------------------------------

    def _parse_fa(self, root: ET.Element) -> FAData:
        automaton = root.find("automaton")
        if automaton is None:
            raise JFLAPParseError("No <automaton> element found for FA.")

        states, initial, accepts, _ = self._parse_states(automaton)
        transitions: list[FATransition] = []

        for t in automaton.findall("transition"):
            from_s = self._get_text(t, "from", required=True)
            to_s   = self._get_text(t, "to",   required=True)
            read   = self._normalise_symbol(self._get_text(t, "read"))
            transitions.append(FATransition(from_s, to_s, read))

        return FAData(
            machine_type=MachineType.FA,
            states=states,
            transitions=transitions,
            initial_state=initial,
            accept_states=accepts,
        )

    # ------------------------------------------------------------------
    # PDA parser
    # ------------------------------------------------------------------

    def _parse_pda(self, root: ET.Element) -> PDAData:
        automaton = root.find("automaton")
        if automaton is None:
            raise JFLAPParseError("No <automaton> element found for PDA.")

        states, initial, accepts, _ = self._parse_states(automaton)
        transitions: list[PDATransition] = []

        for t in automaton.findall("transition"):
            from_s = self._get_text(t, "from", required=True)
            to_s   = self._get_text(t, "to",   required=True)
            read   = self._normalise_symbol(self._get_text(t, "read"))
            pop    = self._normalise_symbol(self._get_text(t, "pop"))
            push   = self._normalise_symbol(self._get_text(t, "push"))
            transitions.append(PDATransition(from_s, to_s, read, pop, push))

        return PDAData(
            machine_type=MachineType.PDA,
            states=states,
            transitions=transitions,
            initial_state=initial,
            accept_states=accepts,
        )

    # ------------------------------------------------------------------
    # TM parser (handles both single-tape and multi-tape)
    # ------------------------------------------------------------------

    def _parse_turing(self, root: ET.Element) -> TMData:
        automaton = root.find("automaton")
        if automaton is None:
            raise JFLAPParseError("No <automaton> element found for Turing Machine.")

        # JFLAP encodes num_tapes as a sibling of <automaton>
        tapes_text = self._get_text(root, "tapes", default="1")
        try:
            num_tapes = int(tapes_text)
        except ValueError:
            num_tapes = 1

        states, initial, accepts, rejects = self._parse_states(automaton)
        transitions: list[TMTransition] = []

        for t in automaton.findall("transition"):
            from_s = self._get_text(t, "from", required=True)
            to_s   = self._get_text(t, "to",   required=True)

            if num_tapes > 1:
                tape_actions = self._parse_multitape_actions(t, num_tapes)
            else:
                tape_actions = [self._parse_single_tape_action(t)]

            transitions.append(TMTransition(from_s, to_s, tape_actions))

        machine_type = MachineType.TURING_MULTI if num_tapes > 1 else MachineType.TURING

        return TMData(
            machine_type=machine_type,
            states=states,
            transitions=transitions,
            initial_state=initial,
            accept_states=accepts,
            reject_states=rejects,
            num_tapes=num_tapes,
        )

    def _parse_single_tape_action(self, t: ET.Element) -> TMTapeAction:
        read  = self._normalise_symbol(self._get_text(t, "read"))
        write = self._normalise_symbol(self._get_text(t, "write"))
        move  = self._get_text(t, "move", default="S").upper() or "S"
        return TMTapeAction(read, write, move)

    def _parse_multitape_actions(self, t: ET.Element, num_tapes: int) -> list[TMTapeAction]:
        """
        Multi-tape transitions in JFLAP use tape="N" attributes on <read>/<write>/<move>.
        Fall back to positional ordering when no attribute is present.
        """
        reads:  dict[int, str] = {}
        writes: dict[int, str] = {}
        moves:  dict[int, str] = {}

        for tag, target in (("read", reads), ("write", writes), ("move", moves)):
            for idx, el in enumerate(t.findall(tag)):
                tape_idx = int(el.get("tape", str(idx + 1))) - 1  # JFLAP is 1-indexed
                target[tape_idx] = (el.text or "").strip()

        actions: list[TMTapeAction] = []
        for i in range(num_tapes):
            read  = self._normalise_symbol(reads.get(i, ""))
            write = self._normalise_symbol(writes.get(i, ""))
            move  = (moves.get(i, "S") or "S").upper()
            actions.append(TMTapeAction(read, write, move))

        return actions

    # ------------------------------------------------------------------
    # Mealy parser
    # ------------------------------------------------------------------

    def _parse_mealy(self, root: ET.Element) -> MealyData:
        automaton = root.find("automaton")
        if automaton is None:
            raise JFLAPParseError("No <automaton> element found for Mealy machine.")

        states, initial, _, _ = self._parse_states(automaton)
        transitions: list[MealyTransition] = []

        for t in automaton.findall("transition"):
            from_s  = self._get_text(t, "from",     required=True)
            to_s    = self._get_text(t, "to",       required=True)
            read    = self._normalise_symbol(self._get_text(t, "read"))
            # JFLAP uses <transout> for Mealy output
            output  = self._get_text(t, "transout")
            transitions.append(MealyTransition(from_s, to_s, read, output))

        return MealyData(
            machine_type=MachineType.MEALY,
            states=states,
            transitions=transitions,
            initial_state=initial,
        )

    # ------------------------------------------------------------------
    # Moore parser
    # ------------------------------------------------------------------

    def _parse_moore(self, root: ET.Element) -> MooreData:
        automaton = root.find("automaton")
        if automaton is None:
            raise JFLAPParseError("No <automaton> element found for Moore machine.")

        states, initial, _, _ = self._parse_states(automaton)
        transitions: list[MooreTransition] = []

        for t in automaton.findall("transition"):
            from_s = self._get_text(t, "from", required=True)
            to_s   = self._get_text(t, "to",   required=True)
            read   = self._normalise_symbol(self._get_text(t, "read"))
            transitions.append(MooreTransition(from_s, to_s, read))

        return MooreData(
            machine_type=MachineType.MOORE,
            states=states,
            transitions=transitions,
            initial_state=initial,
        )

    # ------------------------------------------------------------------
    # Grammar parser
    # ------------------------------------------------------------------

    def _parse_grammar(self, root: ET.Element) -> GrammarData:
        grammar_el = root.find("grammar")
        if grammar_el is None:
            raise JFLAPParseError("No <grammar> element found.")

        productions: list[GrammarProduction] = []
        start_symbol = ""

        for prod in grammar_el.findall("production"):
            left  = self._get_text(prod, "left",  required=True)
            right = self._get_text(prod, "right")   # "" is valid (epsilon production)
            productions.append(GrammarProduction(left, right))
            if not start_symbol:
                start_symbol = left   # first production's LHS is the start symbol

        if not productions:
            raise JFLAPParseError("Grammar contains no productions.")

        return GrammarData(
            machine_type=MachineType.GRAMMAR,
            productions=productions,
            start_symbol=start_symbol,
        )

    # ------------------------------------------------------------------
    # L-System parser
    # ------------------------------------------------------------------

    def _parse_lsystem(self, root: ET.Element) -> LSystemData:
        lsystem_el = root.find("lsystem")
        if lsystem_el is None:
            raise JFLAPParseError("No <lsystem> element found.")

        axiom = self._get_text(lsystem_el, "axiom", required=True)
        productions: dict[str, str] = {}

        for prod in lsystem_el.findall("production"):
            predecessor = self._get_text(prod, "predecessor", required=True)
            successor   = self._get_text(prod, "successor",   default="")
            productions[predecessor] = successor

        return LSystemData(
            machine_type=MachineType.LSYSTEM,
            axiom=axiom,
            productions=productions,
        )
