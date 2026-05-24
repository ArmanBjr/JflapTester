from __future__ import annotations

from machines.base import BaseMachine, MachineType
from machines.fa import FAMachine
from machines.pda import PDAMachine
from machines.turing import TuringMachine
from machines.multitape import MultiTapeTuringMachine
from machines.mealy import MealyMachine
from machines.moore import MooreMachine
from machines.grammar import GrammarMachine
from machines.lsystem import LSystemMachine
from parser.models import (
    ParsedMachine, FAData, PDAData, TMData,
    MealyData, MooreData, GrammarData, LSystemData,
)


def build_machine(data: ParsedMachine) -> BaseMachine:
    """Return the correct simulator instance for any parsed machine data object."""
    if isinstance(data, FAData):
        return FAMachine(data)
    if isinstance(data, PDAData):
        return PDAMachine(data)
    if isinstance(data, TMData):
        if data.machine_type == MachineType.TURING_MULTI:
            return MultiTapeTuringMachine(data)
        return TuringMachine(data)
    if isinstance(data, MealyData):
        return MealyMachine(data)
    if isinstance(data, MooreData):
        return MooreMachine(data)
    if isinstance(data, GrammarData):
        return GrammarMachine(data)
    if isinstance(data, LSystemData):
        return LSystemMachine(data)
    raise TypeError(f"No simulator registered for {type(data).__name__}")
