from __future__ import annotations

from collections import defaultdict, deque
from typing import NamedTuple

from machines.base import BaseMachine, MachineOptions, MachineType, RunResult, RunStatus
from parser.models import PDAData, PDATransition


class _Config(NamedTuple):
    """A single PDA configuration: (state, remaining_input_index, stack_as_tuple)."""
    state: str
    index: int
    stack: tuple[str, ...]   # top of stack is stack[0]


class PDAMachine(BaseMachine):
    """
    Nondeterministic PDA simulator using BFS over configurations.
    Supports both acceptance modes: final state and empty stack.
    Detects infinite epsilon loops via configuration deduplication.
    """

    def __init__(self, data: PDAData) -> None:
        self._data = data
        self._transitions: dict[str, list[PDATransition]] = defaultdict(list)
        for t in data.transitions:
            self._transitions[t.from_state].append(t)

    @property
    def machine_type(self) -> MachineType:
        return MachineType.PDA

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self, input_string: str, options: MachineOptions) -> RunResult:
        by_final_state = options.pda_acceptance == "final_state"
        initial = _Config(
            state=self._data.initial_state,
            index=0,
            stack=(),
        )

        visited: set[_Config] = set()
        queue: deque[_Config] = deque([initial])

        while queue:
            config = queue.popleft()
            if config in visited:
                continue
            visited.add(config)

            if self._is_accepting(config, input_string, by_final_state):
                return RunResult(status=RunStatus.ACCEPTED)

            for successor in self._successors(config, input_string):
                if successor not in visited:
                    queue.append(successor)

        return RunResult(status=RunStatus.REJECTED)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _is_accepting(self, config: _Config, input_string: str, by_final_state: bool) -> bool:
        consumed_all = config.index == len(input_string)
        if not consumed_all:
            return False
        if by_final_state:
            return config.state in self._data.accept_states
        return len(config.stack) == 0   # empty stack acceptance

    def _successors(self, config: _Config, input_string: str) -> list[_Config]:
        state, index, stack = config
        successors: list[_Config] = []

        for t in self._transitions[state]:
            # Check read symbol
            if t.read != "":
                if index >= len(input_string) or input_string[index] != t.read:
                    continue
                new_index = index + 1
            else:
                new_index = index  # epsilon on input

            # Check pop symbol against top of stack
            if t.pop != "":
                if not stack or stack[0] != t.pop:
                    continue
                new_stack = stack[1:]
            else:
                new_stack = stack  # epsilon pop (don't consume)

            # Apply push
            if t.push != "":
                pushed = tuple(reversed(t.push))  # push each char; leftmost on top
                new_stack = pushed + new_stack
            # push == "" means push nothing (epsilon push)

            successors.append(_Config(t.to_state, new_index, new_stack))

        return successors
