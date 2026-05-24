from __future__ import annotations

from machines.base import BaseMachine, MachineOptions, MachineType, RunResult, RunStatus
from parser.models import MooreData, MooreTransition


class MooreMachine(BaseMachine):
    """
    Moore machine simulator.
    Output is produced by states; result is the concatenated output for each
    state visited (starting from the initial state, before any input is read).
    """

    def __init__(self, data: MooreData) -> None:
        self._data = data
        # (state, read_symbol) -> to_state
        self._delta: dict[tuple[str, str], str] = {}
        for t in data.transitions:
            self._delta[(t.from_state, t.read)] = t.to_state

    @property
    def machine_type(self) -> MachineType:
        return MachineType.MOORE

    def run(self, input_string: str, options: MachineOptions) -> RunResult:
        state = self._data.initial_state
        output_parts: list[str] = []

        # Moore machines emit output for the initial state before reading any input
        output_parts.append(self._data.states[state].output)

        for symbol in input_string:
            next_state = self._delta.get((state, symbol))
            if next_state is None:
                return RunResult(
                    status=RunStatus.ERROR,
                    error=f"No transition from state '{state}' on symbol '{symbol}'",
                )
            state = next_state
            output_parts.append(self._data.states[state].output)

        return RunResult(status=RunStatus.HALTED, output="".join(output_parts))
