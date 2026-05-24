from __future__ import annotations
from dataclasses import dataclass, field
from machines.base import MachineType


# ---------------------------------------------------------------------------
# Shared
# ---------------------------------------------------------------------------

@dataclass
class StateData:
    id: str
    name: str
    is_initial: bool = False
    is_final: bool = False
    is_reject: bool = False   # explicit reject states (some TM conventions)
    output: str = ""          # Moore machine per-state output


# ---------------------------------------------------------------------------
# Finite Automaton
# ---------------------------------------------------------------------------

@dataclass
class FATransition:
    from_state: str
    to_state: str
    read: str   # "" means epsilon


@dataclass
class FAData:
    machine_type: MachineType
    states: dict[str, StateData]
    transitions: list[FATransition]
    initial_state: str
    accept_states: set[str]


# ---------------------------------------------------------------------------
# Pushdown Automaton
# ---------------------------------------------------------------------------

@dataclass
class PDATransition:
    from_state: str
    to_state: str
    read: str   # "" = epsilon
    pop: str    # "" = epsilon
    push: str   # "" = epsilon


@dataclass
class PDAData:
    machine_type: MachineType
    states: dict[str, StateData]
    transitions: list[PDATransition]
    initial_state: str
    accept_states: set[str]


# ---------------------------------------------------------------------------
# Turing Machine (single-tape and multi-tape share this model)
# ---------------------------------------------------------------------------

@dataclass
class TMTapeAction:
    read: str        # symbol to match ("" = blank)
    write: str       # symbol to write
    move: str        # "L", "R", or "S"


@dataclass
class TMTransition:
    from_state: str
    to_state: str
    tape_actions: list[TMTapeAction]   # length == num_tapes


@dataclass
class TMData:
    machine_type: MachineType          # TURING or TURING_MULTI
    states: dict[str, StateData]
    transitions: list[TMTransition]
    initial_state: str
    accept_states: set[str]
    reject_states: set[str]
    num_tapes: int = 1


# ---------------------------------------------------------------------------
# Mealy Machine
# ---------------------------------------------------------------------------

@dataclass
class MealyTransition:
    from_state: str
    to_state: str
    read: str
    output: str


@dataclass
class MealyData:
    machine_type: MachineType
    states: dict[str, StateData]
    transitions: list[MealyTransition]
    initial_state: str


# ---------------------------------------------------------------------------
# Moore Machine
# ---------------------------------------------------------------------------

@dataclass
class MooreTransition:
    from_state: str
    to_state: str
    read: str


@dataclass
class MooreData:
    machine_type: MachineType
    states: dict[str, StateData]
    transitions: list[MooreTransition]
    initial_state: str


# ---------------------------------------------------------------------------
# Grammar
# ---------------------------------------------------------------------------

@dataclass
class GrammarProduction:
    left: str
    right: str   # "" represents the empty string (lambda/epsilon)


@dataclass
class GrammarData:
    machine_type: MachineType
    productions: list[GrammarProduction]
    start_symbol: str   # left-hand side of first production by JFLAP convention


# ---------------------------------------------------------------------------
# L-System
# ---------------------------------------------------------------------------

@dataclass
class LSystemData:
    machine_type: MachineType
    axiom: str
    productions: dict[str, str]   # predecessor -> successor


# ---------------------------------------------------------------------------
# Union type for all parsed results
# ---------------------------------------------------------------------------

ParsedMachine = FAData | PDAData | TMData | MealyData | MooreData | GrammarData | LSystemData
