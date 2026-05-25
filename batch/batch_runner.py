from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from machines.base import MachineOptions
from runner.test_runner import TestRunner

# Type alias for progress callbacks: (done, total, current_student_label)
ProgressCallback = Callable[[int, int, str], None]

# How to derive a row-label from a student folder
ROW_LABEL_FOLDER   = "folder_name"   # full folder name as-is
ROW_LABEL_SHORT    = "short_name"    # strip _assignsubmission_file_ suffix
ROW_LABEL_ID       = "student_id"    # extract numeric ID from folder name

# How to format a score cell in the Excel
SCORE_FRACTION     = "fraction"      # "8 / 10"
SCORE_NUMERIC      = "numeric"       # 8  (integer — allows Excel SUM)
SCORE_PERCENT      = "percent"       # "80%"
SCORE_FULL         = "full"          # "8 / 10 (80%)"

# Cell status tags
STATUS_OK          = "ok"
STATUS_MISSING     = "missing"       # JFF file not found in student folder
STATUS_ERROR       = "error"         # parse / runtime error


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class QuestionConfig:
    """Everything the runner needs to evaluate one question for every student."""
    label: str                                       # e.g. "Q2-1"
    jff_filename: str                                # e.g. "q#2-1.jff"
    zip_path: Path                                   # test-cases ZIP
    options: MachineOptions = field(default_factory=MachineOptions)


@dataclass
class QuestionResult:
    """Result of running one question against one student's JFF."""
    label: str
    jff_path: Path | None
    passed: int   = 0
    total: int    = 0
    status: str   = STATUS_OK
    error_msg: str = ""

    # ------------------------------------------------------------------
    def format(self, mode: str) -> str:
        """Return the display string for a spreadsheet cell."""
        if self.status == STATUS_MISSING:
            return "missing"
        if self.status == STATUS_ERROR:
            return "error"
        if self.total == 0:
            return "0 / 0"
        if mode == SCORE_NUMERIC:
            return str(self.passed)
        if mode == SCORE_PERCENT:
            return f"{self.passed / self.total:.0%}"
        if mode == SCORE_FULL:
            return f"{self.passed} / {self.total}  ({self.passed / self.total:.0%})"
        return f"{self.passed} / {self.total}"   # SCORE_FRACTION (default)

    @property
    def ratio(self) -> float:
        return self.passed / self.total if self.total else 0.0

    @property
    def numeric_score(self) -> int:
        return self.passed if self.status == STATUS_OK else 0

    @property
    def numeric_total(self) -> int:
        return self.total if self.status == STATUS_OK else 0


@dataclass
class StudentResult:
    """All question results for one student."""
    label: str
    folder_path: Path
    question_results: dict[str, QuestionResult] = field(default_factory=dict)

    @property
    def total_passed(self) -> int:
        return sum(r.numeric_score for r in self.question_results.values())

    @property
    def grand_total(self) -> int:
        return sum(r.numeric_total for r in self.question_results.values())

    @property
    def overall_ratio(self) -> float:
        return self.total_passed / self.grand_total if self.grand_total else 0.0


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

class BatchRunner:
    """
    For each student folder and each question, finds the student's JFF by
    recursively searching the folder tree, then runs it against the question's
    test-case ZIP.
    """

    _RUNNER = TestRunner()

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def run(
        self,
        student_folders: list[Path],
        questions: list[QuestionConfig],
        row_label_mode: str = ROW_LABEL_FOLDER,
        progress: ProgressCallback | None = None,
    ) -> list[StudentResult]:
        results: list[StudentResult] = []
        total = len(student_folders)

        for i, folder in enumerate(student_folders):
            label = self._make_label(folder, row_label_mode)
            q_results: dict[str, QuestionResult] = {}

            for q in questions:
                q_results[q.label] = self._run_question(folder, q)

            results.append(StudentResult(
                label=label,
                folder_path=folder,
                question_results=q_results,
            ))

            if progress:
                progress(i + 1, total, label)

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_question(self, folder: Path, q: QuestionConfig) -> QuestionResult:
        jff = self._find_jff(folder, q.jff_filename)

        if jff is None:
            return QuestionResult(
                label=q.label,
                jff_path=None,
                status=STATUS_MISSING,
            )

        try:
            report = self._RUNNER.run(jff, q.zip_path, q.options)
            if report.load_error:
                return QuestionResult(
                    label=q.label,
                    jff_path=jff,
                    status=STATUS_ERROR,
                    error_msg=report.load_error,
                )
            return QuestionResult(
                label=q.label,
                jff_path=jff,
                passed=report.passed,
                total=report.total,
                status=STATUS_OK,
            )
        except Exception as exc:
            return QuestionResult(
                label=q.label,
                jff_path=jff,
                status=STATUS_ERROR,
                error_msg=str(exc),
            )

    @staticmethod
    def _find_jff(student_folder: Path, filename: str) -> Path | None:
        """
        Search recursively inside student_folder for a file whose name
        exactly matches filename (case-insensitive on Windows).
        Returns the first match, or None.
        """
        for match in student_folder.rglob(filename):
            if match.is_file():
                return match
        return None

    @staticmethod
    def _make_label(folder: Path, mode: str) -> str:
        name = folder.name

        if mode == ROW_LABEL_SHORT:
            # Remove Moodle submission suffix
            return re.sub(r"_\d+_assignsubmission_file_?$", "", name).strip("_") or name

        if mode == ROW_LABEL_ID:
            # Look for a 7-10 digit student ID embedded in the folder name
            m = re.search(r"(?<!\d)(\d{7,10})(?!\d)", name)
            return m.group(1) if m else name

        return name   # ROW_LABEL_FOLDER
