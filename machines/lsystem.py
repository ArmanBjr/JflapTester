from __future__ import annotations

from machines.base import BaseMachine, MachineOptions, MachineType, RunResult, RunStatus
from parser.models import LSystemData


class LSystemMachine(BaseMachine):
    """
    L-System simulator.
    Applies production rules to the axiom for the number of iterations
    specified in MachineOptions.lsystem_iterations.
    Symbols with no production rule map to themselves (identity rule).
    The result is the final string after all iterations.
    """

    def __init__(self, data: LSystemData) -> None:
        self._data = data

    @property
    def machine_type(self) -> MachineType:
        return MachineType.LSYSTEM

    def run(self, input_string: str, options: MachineOptions) -> RunResult:
        # For L-Systems the "input" is the axiom from the .jff file;
        # the input_string from the test case overrides it when non-empty.
        axiom = input_string if input_string else self._data.axiom
        current = axiom

        for _ in range(options.lsystem_iterations):
            current = self._step(current)

        return RunResult(status=RunStatus.HALTED, output=current)

    def _step(self, current: str) -> str:
        return "".join(
            self._data.productions.get(ch, ch)   # identity if no rule
            for ch in current
        )
