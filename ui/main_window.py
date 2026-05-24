from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from machines.base import MachineType
from parser.jflap_parser import JFLAPParseError
from runner.test_runner import RunReport, TestRunner
from ui.options_panel import OptionsPanel
from ui.results_panel import ResultsPanel

# Human-friendly machine type labels
_TYPE_LABELS: dict[MachineType, str] = {
    MachineType.FA:           "Finite Automaton (DFA / NFA)",
    MachineType.PDA:          "Pushdown Automaton (PDA)",
    MachineType.TURING:       "Turing Machine (single-tape)",
    MachineType.TURING_MULTI: "Turing Machine (multi-tape)",
    MachineType.MEALY:        "Mealy Machine",
    MachineType.MOORE:        "Moore Machine",
    MachineType.GRAMMAR:      "Grammar (CFG)",
    MachineType.LSYSTEM:      "L-System",
}

_ACCENT  = ("#1f6aa5", "#4da6ff")   # blue accent (light, dark)
_SUCCESS = ("#2d8a4e", "#3dba6a")
_DANGER  = ("#c0392b", "#e05555")


def _section(parent: ctk.CTkBaseClass, title: str) -> ctk.CTkFrame:
    """Return a labelled card frame."""
    outer = ctk.CTkFrame(parent, corner_radius=12)
    ctk.CTkLabel(
        outer, text=title,
        font=ctk.CTkFont(size=12, weight="bold"),
        text_color=("gray50", "gray60"),
        anchor="w",
    ).pack(fill="x", padx=14, pady=(10, 2))
    return outer


class App(ctk.CTk):
    """Main application window."""

    def __init__(self) -> None:
        super().__init__()

        ctk.set_default_color_theme("blue")
        ctk.set_appearance_mode("System")

        self.title("JFLAP Tester")
        self.geometry("960x780")
        self.minsize(860, 680)

        self._runner     = TestRunner()
        self._jff_path:  Path | None = None
        self._zip_path:  Path | None = None
        self._machine_type: MachineType | None = None
        self._running    = False

        self._build_ui()
        self._refresh_run_button()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        # ── root grid: left panel | results ──────────────────────────
        self.grid_columnconfigure(0, weight=0, minsize=400)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._build_left_panel()
        self._build_right_panel()

    # ── LEFT PANEL ────────────────────────────────────────────────────

    def _build_left_panel(self) -> None:
        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(14, 6), pady=14)
        left.grid_rowconfigure(5, weight=1)   # spacer

        # Header
        header = ctk.CTkFrame(left, fg_color="transparent")
        header.pack(fill="x", pady=(0, 12))

        ctk.CTkLabel(
            header, text="JFLAP Tester",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).pack(side="left")

        self._theme_btn = ctk.CTkButton(
            header, text="☀ Light", width=80, height=28,
            fg_color="transparent",
            border_width=1,
            text_color=("gray30", "gray80"),
            hover_color=("gray90", "gray20"),
            command=self._toggle_theme,
            font=ctk.CTkFont(size=12),
        )
        self._theme_btn.pack(side="right")

        # Machine file section
        self._build_machine_section(left)

        # Test cases section
        self._build_testcases_section(left)

        # Options section (hidden by default; shown after JFF is loaded)
        self._left_panel = left
        self._build_options_section(left)

        # Run section
        self._build_run_section(left)

    def _build_machine_section(self, parent: ctk.CTkBaseClass) -> None:
        card = _section(parent, "JFLAP MACHINE  (.jff)")
        card.pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(4, 0))

        ctk.CTkButton(
            row, text="Browse…", width=88,
            command=self._browse_jff,
        ).pack(side="left")

        self._jff_label = ctk.CTkLabel(
            row, text="No file selected",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray55"),
            anchor="w", wraplength=240,
        )
        self._jff_label.pack(side="left", padx=(10, 0), fill="x", expand=True)

        self._type_badge = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=_ACCENT,
            anchor="w",
        )
        self._type_badge.pack(fill="x", padx=14, pady=(4, 10))

    def _build_testcases_section(self, parent: ctk.CTkBaseClass) -> None:
        card = _section(parent, "TEST CASES  (.zip)")
        card.pack(fill="x", pady=(0, 8))

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(4, 0))

        ctk.CTkButton(
            row, text="Browse…", width=88,
            command=self._browse_zip,
        ).pack(side="left")

        self._zip_label = ctk.CTkLabel(
            row, text="No file selected",
            font=ctk.CTkFont(size=12),
            text_color=("gray50", "gray55"),
            anchor="w", wraplength=240,
        )
        self._zip_label.pack(side="left", padx=(10, 0), fill="x", expand=True)

        self._zip_info = ctk.CTkLabel(
            card, text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray50", "gray55"),
            anchor="w",
        )
        self._zip_info.pack(fill="x", padx=14, pady=(4, 10))

    def _build_options_section(self, parent: ctk.CTkBaseClass) -> None:
        self._options_card = _section(parent, "OPTIONS")
        self._options_card.pack(fill="x", pady=(0, 8))
        # Content hidden until a machine with configurable options is loaded
        self._options_card.pack_forget()

        self._options_panel = OptionsPanel(self._options_card)
        self._options_panel.pack(fill="x", padx=14, pady=(4, 12))

    def _build_run_section(self, parent: ctk.CTkBaseClass) -> None:
        card = ctk.CTkFrame(parent, fg_color="transparent")
        card.pack(fill="x", pady=(4, 0))
        self._run_section = card

        self._run_btn = ctk.CTkButton(
            card, text="▶  Run Tests",
            height=42,
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self._run,
            state="disabled",
        )
        self._run_btn.pack(fill="x")

        progress_row = ctk.CTkFrame(card, fg_color="transparent")
        progress_row.pack(fill="x", pady=(8, 0))

        self._progress_bar = ctk.CTkProgressBar(progress_row, height=8)
        self._progress_bar.pack(side="left", fill="x", expand=True)
        self._progress_bar.set(0)

        self._progress_label = ctk.CTkLabel(
            progress_row, text="", width=60,
            font=ctk.CTkFont(size=11),
            anchor="e",
        )
        self._progress_label.pack(side="left", padx=(8, 0))

    # ── RIGHT PANEL (results) ──────────────────────────────────────────

    def _build_right_panel(self) -> None:
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 14), pady=14)
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            right, text="Results",
            font=ctk.CTkFont(size=17, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        self._results_panel = ResultsPanel(right)
        self._results_panel.grid(row=1, column=0, sticky="nsew")

    # ------------------------------------------------------------------
    # File pickers
    # ------------------------------------------------------------------

    def _browse_jff(self) -> None:
        path = filedialog.askopenfilename(
            title="Select JFLAP Machine File",
            filetypes=[("JFLAP files", "*.jff"), ("All files", "*.*")],
        )
        if not path:
            return

        self._jff_path = Path(path)
        self._jff_label.configure(
            text=self._jff_path.name,
            text_color=("gray20", "gray90"),
        )
        self._load_machine_type()
        self._refresh_run_button()

    def _browse_zip(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Test Cases ZIP",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
        )
        if not path:
            return

        self._zip_path = Path(path)
        self._zip_label.configure(
            text=self._zip_path.name,
            text_color=("gray20", "gray90"),
        )
        self._inspect_zip()
        self._refresh_run_button()

    # ------------------------------------------------------------------
    # Machine type detection
    # ------------------------------------------------------------------

    def _load_machine_type(self) -> None:
        if self._jff_path is None:
            return
        try:
            data, _ = self._runner.load_machine(self._jff_path)
            self._machine_type = data.machine_type
            label = _TYPE_LABELS.get(data.machine_type, str(data.machine_type))
            self._type_badge.configure(
                text=f"Detected: {label}",
                text_color=_SUCCESS,
            )
            self._options_panel.show_for(data.machine_type)
            # Only show options card for machine types that have configurable options
            _types_with_options = {
                MachineType.TURING, MachineType.TURING_MULTI,
                MachineType.PDA, MachineType.LSYSTEM,
            }
            if data.machine_type in _types_with_options:
                self._options_card.pack(fill="x", pady=(0, 8), before=self._run_section)
            else:
                self._options_card.pack_forget()
        except (JFLAPParseError, FileNotFoundError, TypeError) as exc:
            self._machine_type = None
            self._type_badge.configure(
                text=f"Parse error: {exc}",
                text_color=_DANGER,
            )
            self._options_panel.hide_all()
            self._options_card.pack_forget()

    def _inspect_zip(self) -> None:
        """Count test-case pairs in the ZIP and update the info label."""
        if self._zip_path is None:
            return
        import zipfile
        import re
        pattern = re.compile(r"(\d+)\.txt$", re.IGNORECASE)
        try:
            with zipfile.ZipFile(self._zip_path) as zf:
                names = zf.namelist()
            indices = set()
            for name in names:
                m = pattern.search(name.lower().replace("\\", "/"))
                if m and ("/input/" in name.lower() or name.lower().startswith("input/")):
                    indices.add(int(m.group(1)))
            count = len(indices)
            self._zip_info.configure(
                text=f"{count} test case{'s' if count != 1 else ''} found",
                text_color=_SUCCESS if count > 0 else _DANGER,
            )
        except Exception:
            self._zip_info.configure(text="Could not read ZIP", text_color=_DANGER)

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def _refresh_run_button(self) -> None:
        ready = (
            self._jff_path is not None
            and self._zip_path is not None
            and self._machine_type is not None
            and not self._running
        )
        self._run_btn.configure(state="normal" if ready else "disabled")

    def _run(self) -> None:
        if self._running:
            return
        self._running = True
        self._run_btn.configure(state="disabled", text="Running…")
        self._progress_bar.set(0)
        self._progress_label.configure(text="")
        self._results_panel.clear()

        options = self._options_panel.get_options()
        thread = threading.Thread(
            target=self._run_worker,
            args=(options,),
            daemon=True,
        )
        thread.start()

    def _run_worker(self, options) -> None:
        def on_progress(done: int, total: int) -> None:
            self.after(0, lambda: self._update_progress(done, total))

        report = self._runner.run(
            jff_path=self._jff_path,
            zip_path=self._zip_path,
            options=options,
            progress=on_progress,
        )
        self.after(0, lambda: self._on_complete(report))

    def _update_progress(self, done: int, total: int) -> None:
        self._progress_bar.set(done / total if total else 0)
        self._progress_label.configure(text=f"{done} / {total}")

    def _on_complete(self, report: RunReport) -> None:
        self._running = False
        self._run_btn.configure(text="▶  Run Tests")
        self._refresh_run_button()
        self._progress_bar.set(1)
        self._results_panel.display(report)

    # ------------------------------------------------------------------
    # Theme toggle
    # ------------------------------------------------------------------

    def _toggle_theme(self) -> None:
        current = ctk.get_appearance_mode()
        if current == "Dark":
            ctk.set_appearance_mode("Light")
            self._theme_btn.configure(text="☀ Light")
        else:
            ctk.set_appearance_mode("Dark")
            self._theme_btn.configure(text="☾ Dark")
