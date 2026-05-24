from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from machines.base import BaseMachine, MachineOptions, RunResult, RunStatus
from machines.factory import build_machine
from parser.jflap_parser import JFLAPParser, JFLAPParseError
from parser.models import ParsedMachine


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------

@dataclass
class CaseResult:
    index: int           # 1-based test case number
    input_text: str
    expected: str
    actual: str
    passed: bool
    run_result: RunResult


@dataclass
class RunReport:
    total: int
    passed: int
    failed: int
    cases: list[CaseResult] = field(default_factory=list)
    load_error: str = ""   # set when the ZIP or JFF could not be loaded at all

    @property
    def success_rate(self) -> float:
        return self.passed / self.total if self.total else 0.0


# ---------------------------------------------------------------------------
# Progress callback type
# ---------------------------------------------------------------------------

ProgressCallback = Callable[[int, int], None]   # (completed, total)


# ---------------------------------------------------------------------------
# TestRunner
# ---------------------------------------------------------------------------

class TestRunner:
    """
    Loads a JFLAP machine file and a ZIP of test cases, runs every case,
    and returns a RunReport.

    ZIP layout expected:
        input/input1.txt
        input/input2.txt
        ...
        output/output1.txt
        output/output2.txt
        ...
    """

    _PARSER = JFLAPParser()
    _INDEX_RE = re.compile(r"(\d+)\.txt$", re.IGNORECASE)

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def load_machine(self, jff_path: str | Path) -> tuple[ParsedMachine, BaseMachine]:
        """Parse a .jff file and return (parsed_data, simulator)."""
        data = self._PARSER.parse(jff_path)
        machine = build_machine(data)
        return data, machine

    def run(
        self,
        jff_path: str | Path,
        zip_path: str | Path,
        options: MachineOptions,
        progress: ProgressCallback | None = None,
    ) -> RunReport:
        """Full pipeline: parse machine, load test cases, run all, return report."""
        # Load machine
        try:
            _, machine = self.load_machine(jff_path)
        except (JFLAPParseError, FileNotFoundError, TypeError) as exc:
            return RunReport(total=0, passed=0, failed=0, load_error=str(exc))

        # Load test cases from ZIP
        try:
            pairs = self._load_pairs(zip_path)
        except (zipfile.BadZipFile, ValueError) as exc:
            return RunReport(total=0, passed=0, failed=0, load_error=str(exc))

        if not pairs:
            return RunReport(total=0, passed=0, failed=0, load_error="No test cases found in ZIP.")

        total = len(pairs)
        results: list[CaseResult] = []

        for completed, (idx, input_text, expected) in enumerate(pairs):
            run_result = machine.run(input_text, options)
            actual = run_result.display()
            passed = self._compare(actual, expected)
            results.append(CaseResult(
                index=idx,
                input_text=input_text,
                expected=expected,
                actual=actual,
                passed=passed,
                run_result=run_result,
            ))
            if progress:
                progress(completed + 1, total)

        passed_count = sum(1 for r in results if r.passed)
        return RunReport(
            total=total,
            passed=passed_count,
            failed=total - passed_count,
            cases=results,
        )

    # ------------------------------------------------------------------
    # ZIP loading
    # ------------------------------------------------------------------

    def _load_pairs(self, zip_path: str | Path) -> list[tuple[int, str, str]]:
        """
        Returns a sorted list of (index, input_text, expected_output) triples.
        Matching is by the numeric suffix: input3.txt ↔ output3.txt.
        """
        inputs: dict[int, str] = {}
        outputs: dict[int, str] = {}

        with zipfile.ZipFile(zip_path, "r") as zf:
            for name in zf.namelist():
                lower = name.lower().replace("\\", "/")
                m = self._INDEX_RE.search(lower)
                if m is None:
                    continue
                idx = int(m.group(1))
                content = zf.read(name).decode("utf-8", errors="replace")

                if "/input/" in lower or lower.startswith("input/"):
                    inputs[idx] = content.strip()
                elif "/output/" in lower or lower.startswith("output/"):
                    outputs[idx] = content.strip()

        common = sorted(set(inputs) & set(outputs))
        if not common:
            raise ValueError(
                "ZIP must contain matching input/inputN.txt and output/outputN.txt files."
            )

        return [(i, inputs[i], outputs[i]) for i in common]

    # ------------------------------------------------------------------
    # Comparison
    # ------------------------------------------------------------------

    @staticmethod
    def _compare(actual: str, expected: str) -> bool:
        """Case-sensitive comparison after stripping leading/trailing whitespace."""
        return actual.strip() == expected.strip()
