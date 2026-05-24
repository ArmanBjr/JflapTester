from __future__ import annotations

from collections import defaultdict

from machines.base import BaseMachine, MachineOptions, MachineType, RunResult, RunStatus
from machines.turing import _Tape
from parser.models import TMData, TMTransition


class MultiTapeTuringMachine(BaseMachine):
    """
    Deterministic multi-tape Turing Machine simulator.
    Tape index for output is selected by the user via MachineOptions.tm_tape_index.
    """

    def __init__(self, data: TMData) -> None:
        self._data = data
        self._num_tapes = data.num_tapes
        # Transition key: (state, tuple of read symbols — one per tape)
        self._delta: dict[tuple[str, tuple[str, ...]], TMTransition] = {}
        for t in data.transitions:
            reads = tuple(a.read for a in t.tape_actions)
            self._delta[(t.from_state, reads)] = t

    @property
    def machine_type(self) -> MachineType:
        return MachineType.TURING_MULTI

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self, input_string: str, options: MachineOptions) -> RunResult:
        # Input goes on tape 0; all other tapes start blank
        tapes = [_Tape(input_string if i == 0 else "") for i in range(self._num_tapes)]
        state = self._data.initial_state
        steps = 0

        while steps < options.step_limit:
            if state in self._data.accept_states:
                return self._halted(tapes, options, accepted=True, steps=steps)
            if state in self._data.reject_states:
                return self._halted(tapes, options, accepted=False, steps=steps)

            reads = tuple(t.read() for t in tapes)
            transition = self._delta.get((state, reads))

            if transition is None:
                return self._halted(tapes, options, accepted=False, steps=steps)

            for tape, action in zip(tapes, transition.tape_actions):
                tape.write(action.write)
                tape.move(action.move)

            state = transition.to_state
            steps += 1

        return RunResult(status=RunStatus.DID_NOT_HALT, steps=steps)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _halted(self, tapes: list[_Tape], options: MachineOptions, accepted: bool, steps: int) -> RunResult:
        if options.tm_output_mode == "tape":
            idx = min(options.tm_tape_index, self._num_tapes - 1)
            return RunResult(
                status=RunStatus.HALTED,
                output=tapes[idx].content(),
                steps=steps,
            )
        status = RunStatus.ACCEPTED if accepted else RunStatus.REJECTED
        return RunResult(status=status, steps=steps)
