from __future__ import annotations

from collections import defaultdict
from typing import NamedTuple

from machines.base import BaseMachine, MachineOptions, MachineType, RunResult, RunStatus
from parser.models import TMData, TMTransition

_BLANK = ""   # We use empty string as the blank symbol throughout


class _Tape:
    """Infinite tape represented as a defaultdict keyed by integer position."""

    def __init__(self, input_string: str) -> None:
        self._cells: dict[int, str] = defaultdict(lambda: _BLANK)
        for i, ch in enumerate(input_string):
            self._cells[i] = ch
        self.head: int = 0

    def read(self) -> str:
        return self._cells[self.head]

    def write(self, symbol: str) -> None:
        self._cells[self.head] = symbol

    def move(self, direction: str) -> None:
        if direction == "R":
            self.head += 1
        elif direction == "L":
            self.head -= 1
        # "S" = stay — do nothing

    def content(self) -> str:
        """Return the tape content (non-blank portion), stripped of trailing blanks."""
        if not self._cells:
            return ""
        lo = min(self._cells)
        hi = max(self._cells)
        result = "".join(self._cells[i] for i in range(lo, hi + 1))
        return result.strip()   # remove leading/trailing blanks


class TuringMachine(BaseMachine):
    """
    Deterministic single-tape Turing Machine simulator.
    Runs until it enters an accept/reject state or the step limit is reached.
    """

    def __init__(self, data: TMData) -> None:
        self._data = data
        # Build transition lookup: (state, read_symbol) -> TMTransition
        self._delta: dict[tuple[str, str], TMTransition] = {}
        for t in data.transitions:
            key = (t.from_state, t.tape_actions[0].read)
            self._delta[key] = t

    @property
    def machine_type(self) -> MachineType:
        return MachineType.TURING

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self, input_string: str, options: MachineOptions) -> RunResult:
        tape = _Tape(input_string)
        state = self._data.initial_state
        steps = 0

        while steps < options.step_limit:
            # Accepting / rejecting states are halting states
            if state in self._data.accept_states:
                return self._halted(tape, options, accepted=True, steps=steps)
            if state in self._data.reject_states:
                return self._halted(tape, options, accepted=False, steps=steps)

            symbol = tape.read()
            transition = self._delta.get((state, symbol))

            if transition is None:
                # No transition defined — implicit reject
                return self._halted(tape, options, accepted=False, steps=steps)

            action = transition.tape_actions[0]
            tape.write(action.write)
            tape.move(action.move)
            state = transition.to_state
            steps += 1

        return RunResult(status=RunStatus.DID_NOT_HALT, steps=steps)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _halted(self, tape: _Tape, options: MachineOptions, accepted: bool, steps: int) -> RunResult:
        if options.tm_output_mode == "tape":
            return RunResult(
                status=RunStatus.HALTED,
                output=tape.content(),
                steps=steps,
            )
        status = RunStatus.ACCEPTED if accepted else RunStatus.REJECTED
        return RunResult(status=status, steps=steps)
