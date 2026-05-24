from __future__ import annotations

from collections import defaultdict

from machines.base import BaseMachine, MachineOptions, MachineType, RunResult, RunStatus
from parser.models import MealyData, MealyTransition


class MealyMachine(BaseMachine):
    """
    Mealy machine simulator.
    Output is produced on transitions; result is the concatenated output string.
    If no transition exists for a symbol the machine halts with an error.
    """

    def __init__(self, data: MealyData) -> None:
        self._data = data
        # (state, read_symbol) -> MealyTransition
        self._delta: dict[tuple[str, str], MealyTransition] = {}
        for t in data.transitions:
            self._delta[(t.from_state, t.read)] = t

    @property
    def machine_type(self) -> MachineType:
        return MachineType.MEALY

    def run(self, input_string: str, options: MachineOptions) -> RunResult:
        state = self._data.initial_state
        output_parts: list[str] = []

        for symbol in input_string:
            transition = self._delta.get((state, symbol))
            if transition is None:
                return RunResult(
                    status=RunStatus.ERROR,
                    error=f"No transition from state '{state}' on symbol '{symbol}'",
                )
            output_parts.append(transition.output)
            state = transition.to_state

        return RunResult(status=RunStatus.HALTED, output="".join(output_parts))
