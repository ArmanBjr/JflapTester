from __future__ import annotations

from collections import defaultdict, deque

from machines.base import BaseMachine, MachineOptions, MachineType, RunResult, RunStatus
from parser.models import FAData, FATransition


class FAMachine(BaseMachine):
    """
    Simulates both DFA and NFA (including epsilon-NFA).
    Uses BFS over the set of active states to handle nondeterminism.
    Epsilon closure is computed lazily per state set.
    """

    def __init__(self, data: FAData) -> None:
        self._data = data
        # Build adjacency: state -> list of (read_symbol, to_state)
        self._transitions: dict[str, list[FATransition]] = defaultdict(list)
        for t in data.transitions:
            self._transitions[t.from_state].append(t)

    @property
    def machine_type(self) -> MachineType:
        return MachineType.FA

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self, input_string: str, options: MachineOptions) -> RunResult:
        initial_closure = self._epsilon_closure({self._data.initial_state})
        active: set[str] = initial_closure

        for symbol in input_string:
            active = self._step(active, symbol)
            if not active:
                return RunResult(status=RunStatus.REJECTED)

        accepted = bool(active & self._data.accept_states)
        status = RunStatus.ACCEPTED if accepted else RunStatus.REJECTED
        return RunResult(status=status)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _step(self, states: set[str], symbol: str) -> set[str]:
        """Move from a set of states on a concrete symbol, then close over epsilon."""
        reached: set[str] = set()
        for state in states:
            for t in self._transitions[state]:
                if t.read == symbol:
                    reached.add(t.to_state)
        return self._epsilon_closure(reached)

    def _epsilon_closure(self, states: set[str]) -> set[str]:
        """Return the set of all states reachable via epsilon transitions from the given states."""
        closure = set(states)
        queue = deque(states)
        while queue:
            current = queue.popleft()
            for t in self._transitions[current]:
                if t.read == "" and t.to_state not in closure:
                    closure.add(t.to_state)
                    queue.append(t.to_state)
        return closure
