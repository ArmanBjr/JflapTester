from __future__ import annotations

from collections import defaultdict

from machines.base import BaseMachine, MachineOptions, MachineType, RunResult, RunStatus
from parser.models import GrammarData, GrammarProduction


class GrammarMachine(BaseMachine):
    """
    Grammar membership tester.

    Automatically detects grammar class:
    - If all productions are in Chomsky Normal Form (or can be converted),
      uses the CYK algorithm for CFGs.
    - Epsilon input is handled specially: accepted iff S → ε exists.

    CNF conversion is done internally before running CYK, so the user's
    original grammar does not need to already be in CNF.
    """

    def __init__(self, data: GrammarData) -> None:
        self._data = data
        self._start = data.start_symbol
        # Precompute CNF form once at construction time
        self._cnf_unit: dict[str, set[str]]          # A -> terminal
        self._cnf_pair: dict[str, set[tuple[str, str]]]  # A -> (B, C)
        self._has_epsilon_start: bool
        self._cnf_unit, self._cnf_pair, self._has_epsilon_start = self._to_cnf(data.productions)

    @property
    def machine_type(self) -> MachineType:
        return MachineType.GRAMMAR

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(self, input_string: str, options: MachineOptions) -> RunResult:
        if input_string == "":
            status = RunStatus.ACCEPTED if self._has_epsilon_start else RunStatus.REJECTED
            return RunResult(status=status)

        accepted = self._cyk(input_string)
        return RunResult(status=RunStatus.ACCEPTED if accepted else RunStatus.REJECTED)

    # ------------------------------------------------------------------
    # CYK
    # ------------------------------------------------------------------

    def _cyk(self, w: str) -> bool:
        n = len(w)
        # table[i][j] = set of non-terminals that derive w[i..j]
        table: list[list[set[str]]] = [[set() for _ in range(n)] for _ in range(n)]

        # Fill diagonal: single characters
        for i, ch in enumerate(w):
            for nt, terminals in self._cnf_unit.items():
                if ch in terminals:
                    table[i][i].add(nt)

        # Fill upper triangle
        for length in range(2, n + 1):          # substring length
            for i in range(n - length + 1):     # start index
                j = i + length - 1              # end index
                for k in range(i, j):           # split point
                    for nt, pairs in self._cnf_pair.items():
                        for (B, C) in pairs:
                            if B in table[i][k] and C in table[k + 1][j]:
                                table[i][j].add(nt)

        return self._start in table[0][n - 1]

    # ------------------------------------------------------------------
    # CNF conversion
    # ------------------------------------------------------------------

    def _to_cnf(
        self,
        productions: list[GrammarProduction],
    ) -> tuple[dict[str, set[str]], dict[str, set[tuple[str, str]]], bool]:
        """
        Convert arbitrary CFG productions to Chomsky Normal Form.
        Returns (unit_rules, pair_rules, start_derives_epsilon).

        Steps:
          1. Add new start symbol S0 → S
          2. Eliminate ε-productions (record which NTs are nullable)
          3. Eliminate unit productions (A → B)
          4. Break long productions into binary
          5. Isolate terminals in binary/longer rules
        """
        # Collect all non-terminals
        nts: set[str] = {p.left for p in productions}
        prods: list[tuple[str, list[str]]] = [
            (p.left, list(p.right) if p.right else []) for p in productions
        ]

        # Step 1 — new start
        new_start = self._start + "0"
        while new_start in nts:
            new_start += "0"
        prods.append((new_start, [self._start]))
        nts.add(new_start)

        # Step 2 — find nullable non-terminals
        nullable = self._find_nullable(prods)
        has_eps_start = self._start in nullable
        prods = self._eliminate_epsilon(prods, nullable, new_start)

        # Step 3 — eliminate unit productions
        prods = self._eliminate_unit(prods, nts)

        # Step 4 & 5 — binarise and isolate terminals
        prods, nts = self._binarise(prods, nts)

        # Build lookup tables
        unit: dict[str, set[str]] = defaultdict(set)
        pair: dict[str, set[tuple[str, str]]] = defaultdict(set)

        for lhs, rhs in prods:
            if len(rhs) == 1 and rhs[0] not in nts:
                unit[lhs].add(rhs[0])
            elif len(rhs) == 2:
                pair[lhs].add((rhs[0], rhs[1]))

        # Remap start to new_start for CYK
        self._start = new_start
        return dict(unit), dict(pair), has_eps_start

    # ------------------------------------------------------------------
    # CNF helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_nullable(prods: list[tuple[str, list[str]]]) -> set[str]:
        nullable: set[str] = set()
        changed = True
        while changed:
            changed = False
            for lhs, rhs in prods:
                if lhs not in nullable and (rhs == [] or all(s in nullable for s in rhs)):
                    nullable.add(lhs)
                    changed = True
        return nullable

    @staticmethod
    def _eliminate_epsilon(
        prods: list[tuple[str, list[str]]],
        nullable: set[str],
        new_start: str,
    ) -> list[tuple[str, list[str]]]:
        result: list[tuple[str, list[str]]] = []
        for lhs, rhs in prods:
            if rhs == []:
                # Keep only if it is the new start → allows detecting S derives ε
                if lhs == new_start:
                    result.append((lhs, []))
                continue
            # Add all combinations obtained by omitting nullable symbols
            nullable_positions = [i for i, s in enumerate(rhs) if s in nullable]
            for mask in range(1 << len(nullable_positions)):
                skip = {nullable_positions[b] for b in range(len(nullable_positions)) if mask & (1 << b)}
                new_rhs = [s for i, s in enumerate(rhs) if i not in skip]
                if new_rhs:
                    result.append((lhs, new_rhs))
        return result

    @staticmethod
    def _eliminate_unit(
        prods: list[tuple[str, list[str]]],
        nts: set[str],
    ) -> list[tuple[str, list[str]]]:
        # Build unit closure per NT
        unit_map: dict[str, set[str]] = defaultdict(set)
        for lhs, rhs in prods:
            if len(rhs) == 1 and rhs[0] in nts:
                unit_map[lhs].add(rhs[0])

        # Transitive closure
        changed = True
        while changed:
            changed = False
            for a in list(unit_map):
                for b in list(unit_map[a]):
                    for c in unit_map.get(b, set()):
                        if c not in unit_map[a]:
                            unit_map[a].add(c)
                            changed = True

        result: list[tuple[str, list[str]]] = []
        non_unit = [(lhs, rhs) for lhs, rhs in prods if not (len(rhs) == 1 and rhs[0] in nts)]
        result.extend(non_unit)

        for a, reachable in unit_map.items():
            for b in reachable:
                for lhs, rhs in non_unit:
                    if lhs == b:
                        result.append((a, rhs))

        return result

    @staticmethod
    def _binarise(
        prods: list[tuple[str, list[str]]],
        nts: set[str],
    ) -> tuple[list[tuple[str, list[str]]], set[str]]:
        """Break productions longer than 2 into binary; isolate terminals in binary rules."""
        result: list[tuple[str, list[str]]] = []
        counter = [0]

        def fresh(base: str) -> str:
            counter[0] += 1
            name = f"__X{base}{counter[0]}"
            nts.add(name)
            return name

        # Terminal wrappers: terminal -> NT that produces it
        term_nt: dict[str, str] = {}

        def wrap_terminal(sym: str) -> str:
            if sym not in term_nt:
                nt = fresh(sym)
                term_nt[sym] = nt
                result.append((nt, [sym]))
            return term_nt[sym]

        for lhs, rhs in prods:
            if len(rhs) == 0 or len(rhs) == 1:
                result.append((lhs, rhs))
                continue

            # Isolate terminals in rules of length >= 2
            new_rhs = [wrap_terminal(s) if s not in nts else s for s in rhs]

            # Binarise
            while len(new_rhs) > 2:
                right_two = new_rhs[-2:]
                nt = fresh("B")
                result.append((nt, right_two))
                new_rhs = new_rhs[:-2] + [nt]

            result.append((lhs, new_rhs))

        return result, nts
