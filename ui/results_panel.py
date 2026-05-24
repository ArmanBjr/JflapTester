from __future__ import annotations

import customtkinter as ctk

from runner.test_runner import CaseResult, RunReport

# Light/dark colour pairs for pass and fail rows
_PASS_ROW   = ("#d6f0dd", "#1a3328")
_FAIL_ROW   = ("#fad7d7", "#3a1a1a")
_PASS_BADGE = ("#2d8a4e", "#3dba6a")
_FAIL_BADGE = ("#c0392b", "#e05555")
_PASS_ICON  = "✓"
_FAIL_ICON  = "✗"

_MAX_INPUT_CHARS = 38
_MAX_OUTPUT_CHARS = 28


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[:limit - 1] + "…"


class _CaseRow(ctk.CTkFrame):
    """A single test-case result row."""

    def __init__(self, parent: ctk.CTkBaseClass, result: CaseResult) -> None:
        bg = _PASS_ROW if result.passed else _FAIL_ROW
        super().__init__(parent, fg_color=bg, corner_radius=8)

        badge_color = _PASS_BADGE if result.passed else _FAIL_BADGE
        icon = _PASS_ICON if result.passed else _FAIL_ICON

        # ── badge ────────────────────────────────────────────────────
        badge = ctk.CTkLabel(
            self, text=icon, width=32, height=32,
            fg_color=badge_color, corner_radius=6,
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color="white",
        )
        badge.grid(row=0, column=0, padx=(10, 8), pady=8, sticky="ns")

        # ── index ────────────────────────────────────────────────────
        ctk.CTkLabel(
            self, text=f"#{result.index}",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=36, anchor="w",
        ).grid(row=0, column=1, padx=(0, 8), pady=8, sticky="w")

        # ── input ────────────────────────────────────────────────────
        input_display = _truncate(repr(result.input_text), _MAX_INPUT_CHARS)
        ctk.CTkLabel(
            self, text=f"Input: {input_display}",
            font=ctk.CTkFont(size=12, family="Courier"),
            anchor="w", width=290,
        ).grid(row=0, column=2, padx=(0, 12), pady=8, sticky="w")

        # ── expected ─────────────────────────────────────────────────
        ctk.CTkLabel(
            self,
            text=f"Expected: {_truncate(result.expected, _MAX_OUTPUT_CHARS)}",
            font=ctk.CTkFont(size=12),
            anchor="w", width=200,
        ).grid(row=0, column=3, padx=(0, 12), pady=8, sticky="w")

        # ── actual ───────────────────────────────────────────────────
        actual_color = ("gray20", "gray90") if result.passed else (_FAIL_BADGE[0], _FAIL_BADGE[1])
        ctk.CTkLabel(
            self,
            text=f"Got: {_truncate(result.actual, _MAX_OUTPUT_CHARS)}",
            font=ctk.CTkFont(size=12, weight="bold" if not result.passed else "normal"),
            text_color=actual_color,
            anchor="w", width=200,
        ).grid(row=0, column=4, padx=(0, 10), pady=8, sticky="w")

        self.columnconfigure(2, weight=1)


class ResultsPanel(ctk.CTkFrame):
    """
    Displays a RunReport as a scrollable list of coloured result rows
    with a summary header.
    """

    def __init__(self, parent: ctk.CTkBaseClass, **kwargs) -> None:
        super().__init__(parent, **kwargs)

        # ── summary bar ──────────────────────────────────────────────
        self._summary_frame = ctk.CTkFrame(self, corner_radius=10)
        self._summary_frame.pack(fill="x", padx=0, pady=(0, 8))

        self._summary_label = ctk.CTkLabel(
            self._summary_frame,
            text="No results yet.",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self._summary_label.pack(side="left", padx=16, pady=10)

        self._rate_label = ctk.CTkLabel(
            self._summary_frame,
            text="",
            font=ctk.CTkFont(size=13),
            anchor="e",
        )
        self._rate_label.pack(side="right", padx=16, pady=10)

        # ── scrollable rows ──────────────────────────────────────────
        self._scroll = ctk.CTkScrollableFrame(self, label_text="")
        self._scroll.pack(fill="both", expand=True)

        self._rows: list[_CaseRow] = []

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------

    def display(self, report: RunReport) -> None:
        self.clear()

        if report.load_error:
            self._summary_label.configure(
                text=f"Error: {report.load_error}",
                text_color=(_FAIL_BADGE[0], _FAIL_BADGE[1]),
            )
            return

        pass_color = _PASS_BADGE if report.failed == 0 else (
            _FAIL_BADGE if report.passed == 0 else ("gray30", "gray80")
        )
        self._summary_label.configure(
            text=f"{report.passed} / {report.total} passed",
            text_color=(pass_color[0], pass_color[1]),
        )
        self._rate_label.configure(
            text=f"{report.success_rate:.0%}  |  {report.failed} failed"
        )

        for result in report.cases:
            row = _CaseRow(self._scroll, result)
            row.pack(fill="x", padx=4, pady=3)
            self._rows.append(row)

    def clear(self) -> None:
        for row in self._rows:
            row.destroy()
        self._rows.clear()
        self._summary_label.configure(text="No results yet.", text_color=("gray20", "gray90"))
        self._rate_label.configure(text="")
