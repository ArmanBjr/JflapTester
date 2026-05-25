from __future__ import annotations

import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from batch.batch_runner import (
    ROW_LABEL_FOLDER, ROW_LABEL_ID, ROW_LABEL_SHORT,
    SCORE_FRACTION, SCORE_FULL, SCORE_NUMERIC, SCORE_PERCENT,
    BatchRunner, QuestionConfig,
)
from batch.excel_exporter import ExcelExporter
from machines.base import MachineOptions
from ui.options_panel import OptionsPanel

_ACCENT  = ("#1f6aa5", "#4da6ff")
_SUCCESS = ("#2d8a4e", "#3dba6a")
_DANGER  = ("#c0392b", "#e05555")
_MUTED   = ("gray50", "gray55")


def _section_label(parent, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent, text=text,
        font=ctk.CTkFont(size=11, weight="bold"),
        text_color=("gray50", "gray60"),
        anchor="w",
    )


# ---------------------------------------------------------------------------
# Per-question options dialog
# ---------------------------------------------------------------------------

class _QuestionOptionsDialog(ctk.CTkToplevel):
    """Small dialog to configure MachineOptions for one question."""

    def __init__(self, parent, initial_options: MachineOptions, question_label: str) -> None:
        super().__init__(parent)
        self.title(f"Options — {question_label}")
        self.geometry("420x260")
        self.resizable(False, False)
        self.grab_set()

        self._options_panel = OptionsPanel(self)
        self._options_panel.pack(fill="both", expand=True, padx=16, pady=(12, 4))

        # Copy initial values into the panel
        self._options_panel._step_limit_var.set(str(initial_options.step_limit))
        self._options_panel._tm_output_var.set(
            "tape content" if initial_options.tm_output_mode == "tape" else "accept / reject"
        )
        self._options_panel._tape_index_var.set(str(initial_options.tm_tape_index + 1))
        self._options_panel._pda_accept_var.set(
            "empty stack" if initial_options.pda_acceptance == "empty_stack" else "final state"
        )
        self._options_panel._lsystem_iter_var.set(str(initial_options.lsystem_iterations))

        # Show all option groups (user decides what's relevant)
        for frame in self._options_panel._all_groups:
            frame.pack(fill="x", padx=4, pady=2)

        ctk.CTkButton(
            self, text="Save", height=34,
            command=self._save,
        ).pack(fill="x", padx=16, pady=(4, 12))

        self._result: MachineOptions | None = None

    def _save(self) -> None:
        self._result = self._options_panel.get_options()
        self.destroy()

    def get_result(self) -> MachineOptions | None:
        return self._result


# ---------------------------------------------------------------------------
# Single question row widget
# ---------------------------------------------------------------------------

class _QuestionRow(ctk.CTkFrame):
    """One row in the questions table."""

    def __init__(
        self,
        parent: ctk.CTkBaseClass,
        index: int,
        on_delete: callable,
    ) -> None:
        super().__init__(parent, fg_color="transparent")
        self._options = MachineOptions()
        self._on_delete = on_delete
        self._zip_path: Path | None = None

        # Index badge
        ctk.CTkLabel(
            self, text=f"{index}",
            width=24, font=ctk.CTkFont(size=12, weight="bold"),
            text_color=_MUTED,
        ).grid(row=0, column=0, padx=(0, 6), sticky="w")

        # Label entry
        self._label_var = ctk.StringVar(value=f"Q{index}")
        ctk.CTkEntry(
            self, textvariable=self._label_var,
            placeholder_text="Label", width=70,
        ).grid(row=0, column=1, padx=(0, 6))

        # JFF filename entry
        self._jff_var = ctk.StringVar()
        ctk.CTkEntry(
            self, textvariable=self._jff_var,
            placeholder_text="JFF filename  (e.g. q#2-1.jff)", width=200,
        ).grid(row=0, column=2, padx=(0, 6))

        # ZIP browse
        ctk.CTkButton(
            self, text="ZIP…", width=52, height=28,
            command=self._browse_zip,
        ).grid(row=0, column=3, padx=(0, 4))

        self._zip_label = ctk.CTkLabel(
            self, text="No ZIP", width=130,
            font=ctk.CTkFont(size=11),
            text_color=_MUTED, anchor="w",
        )
        self._zip_label.grid(row=0, column=4, padx=(0, 6), sticky="w")

        # Options button
        ctk.CTkButton(
            self, text="⚙", width=30, height=28,
            fg_color="transparent", border_width=1,
            text_color=("gray40", "gray80"),
            hover_color=("gray90", "gray20"),
            command=self._open_options,
        ).grid(row=0, column=5, padx=(0, 4))

        # Delete button
        ctk.CTkButton(
            self, text="✕", width=30, height=28,
            fg_color="transparent", border_width=1,
            text_color=_DANGER,
            hover_color=("gray90", "gray20"),
            command=on_delete,
        ).grid(row=0, column=6)

    # ------------------------------------------------------------------

    def _browse_zip(self) -> None:
        path = filedialog.askopenfilename(
            title="Select Test-Cases ZIP",
            filetypes=[("ZIP files", "*.zip")],
        )
        if path:
            self._zip_path = Path(path)
            self._zip_label.configure(
                text=self._zip_path.name,
                text_color=("gray20", "gray90"),
            )

    def _open_options(self) -> None:
        dlg = _QuestionOptionsDialog(self, self._options, self._label_var.get())
        self.wait_window(dlg)
        if dlg.get_result() is not None:
            self._options = dlg.get_result()

    def to_config(self) -> QuestionConfig | None:
        label    = self._label_var.get().strip()
        filename = self._jff_var.get().strip()
        if not label or not filename or self._zip_path is None:
            return None
        return QuestionConfig(
            label=label,
            jff_filename=filename,
            zip_path=self._zip_path,
            options=self._options,
        )

    def is_complete(self) -> bool:
        return bool(
            self._label_var.get().strip()
            and self._jff_var.get().strip()
            and self._zip_path is not None
        )


# ---------------------------------------------------------------------------
# Single student-folder row widget
# ---------------------------------------------------------------------------

class _StudentRow(ctk.CTkFrame):
    """Checkbox + folder path label."""

    def __init__(self, parent: ctk.CTkBaseClass, folder: Path) -> None:
        super().__init__(parent, fg_color="transparent")
        self.folder = folder
        self._var = ctk.BooleanVar(value=True)

        self._cb = ctk.CTkCheckBox(
            self,
            text=folder.name,
            variable=self._var,
            font=ctk.CTkFont(size=12),
            checkbox_width=18,
            checkbox_height=18,
        )
        self._cb.pack(side="left", fill="x", expand=True)

    @property
    def enabled(self) -> bool:
        return self._var.get()

    def select_all(self)   -> None: self._var.set(True)
    def select_none(self)  -> None: self._var.set(False)


# ---------------------------------------------------------------------------
# Main Batch window
# ---------------------------------------------------------------------------

class BatchWindow(ctk.CTkToplevel):
    """
    Standalone top-level window for batch marking.
    Opens from the main app's header button.
    """

    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.title("Batch Marker")
        self.geometry("1050x760")
        self.minsize(900, 640)

        self._runner   = BatchRunner()
        self._exporter = ExcelExporter()
        self._running  = False

        self._question_rows: list[_QuestionRow] = []
        self._student_rows:  list[_StudentRow]  = []

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)   # student list expands

        # Title
        ctk.CTkLabel(
            self, text="Batch Marker",
            font=ctk.CTkFont(size=20, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(14, 0))

        # Two-column body
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=12, pady=8)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

        # Bottom bar
        self._build_bottom()

    def _build_left(self, parent) -> None:
        left = ctk.CTkFrame(parent, corner_radius=12)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        left.grid_rowconfigure(1, weight=1)
        left.grid_columnconfigure(0, weight=1)

        # ── Questions header ──────────────────────────────────────────
        hdr = ctk.CTkFrame(left, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))

        _section_label(hdr, "QUESTIONS").pack(side="left")

        ctk.CTkButton(
            hdr, text="+ Add Question", width=120, height=28,
            command=self._add_question,
        ).pack(side="right")

        # Column header labels
        col_hdr = ctk.CTkFrame(left, fg_color="transparent")
        col_hdr.grid(row=1, column=0, sticky="ew", padx=12)
        for text, w in [("#", 24), ("Label", 70), ("JFF Filename", 200),
                        ("Test ZIP", 190), ("", 68)]:
            ctk.CTkLabel(
                col_hdr, text=text, width=w,
                font=ctk.CTkFont(size=10),
                text_color=_MUTED, anchor="w",
            ).pack(side="left", padx=(0, 6))

        # Scrollable question rows
        self._q_scroll = ctk.CTkScrollableFrame(left, label_text="")
        self._q_scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
        left.grid_rowconfigure(2, weight=1)

    def _build_right(self, parent) -> None:
        right = ctk.CTkFrame(parent, corner_radius=12)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)

        # ── Students header ───────────────────────────────────────────
        hdr = ctk.CTkFrame(right, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 4))

        _section_label(hdr, "STUDENT FOLDERS").pack(side="left")

        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 4))

        ctk.CTkButton(
            btn_row, text="Add Folders…", width=110, height=28,
            command=self._add_folders,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Add all from dir…", width=130, height=28,
            command=self._add_all_from_dir,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="Select All", width=80, height=28,
            fg_color="transparent", border_width=1,
            text_color=("gray30", "gray80"),
            command=lambda: [r.select_all() for r in self._student_rows],
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_row, text="None", width=60, height=28,
            fg_color="transparent", border_width=1,
            text_color=("gray30", "gray80"),
            command=lambda: [r.select_none() for r in self._student_rows],
        ).pack(side="left", padx=(0, 4))

        ctk.CTkButton(
            btn_row, text="Clear", width=60, height=28,
            fg_color="transparent", border_width=1,
            text_color=_DANGER,
            command=self._clear_students,
        ).pack(side="right")

        # Scrollable student list
        self._s_scroll = ctk.CTkScrollableFrame(right, label_text="")
        self._s_scroll.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 4))

        self._student_count_label = ctk.CTkLabel(
            right, text="0 folders",
            font=ctk.CTkFont(size=11),
            text_color=_MUTED,
        )
        self._student_count_label.grid(row=3, column=0, sticky="e", padx=14, pady=(0, 8))

    def _build_bottom(self) -> None:
        bottom = ctk.CTkFrame(self, corner_radius=12)
        bottom.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        bottom.grid_columnconfigure(1, weight=1)

        # ── Options ───────────────────────────────────────────────────
        opts = ctk.CTkFrame(bottom, fg_color="transparent")
        opts.grid(row=0, column=0, padx=14, pady=10, sticky="w")

        _section_label(opts, "OPTIONS").grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 6))

        ctk.CTkLabel(opts, text="Row label:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=0, padx=(0, 6), sticky="w")
        self._row_label_var = ctk.StringVar(value="Short name")
        ctk.CTkOptionMenu(
            opts,
            variable=self._row_label_var,
            values=["Folder name", "Short name", "Student ID"],
            width=150,
        ).grid(row=1, column=1, padx=(0, 20))

        ctk.CTkLabel(opts, text="Score format:", font=ctk.CTkFont(size=12)).grid(
            row=1, column=2, padx=(0, 6), sticky="w")
        self._score_fmt_var = ctk.StringVar(value="X / N")
        ctk.CTkOptionMenu(
            opts,
            variable=self._score_fmt_var,
            values=["X / N", "Numeric", "%", "X / N (%)"],
            width=130,
        ).grid(row=1, column=3)

        # ── Run button + progress ─────────────────────────────────────
        run_area = ctk.CTkFrame(bottom, fg_color="transparent")
        run_area.grid(row=0, column=1, padx=14, pady=10, sticky="e")

        self._run_btn = ctk.CTkButton(
            run_area, text="▶  Run & Export Excel",
            width=200, height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._run,
        )
        self._run_btn.pack(side="right", padx=(10, 0))

        prog_col = ctk.CTkFrame(run_area, fg_color="transparent")
        prog_col.pack(side="right")

        self._progress_bar = ctk.CTkProgressBar(prog_col, width=200, height=8)
        self._progress_bar.pack()
        self._progress_bar.set(0)

        self._progress_label = ctk.CTkLabel(
            prog_col, text="",
            font=ctk.CTkFont(size=11),
        )
        self._progress_label.pack()

    # ------------------------------------------------------------------
    # Questions management
    # ------------------------------------------------------------------

    def _add_question(self) -> None:
        idx = len(self._question_rows) + 1

        def on_delete(row=None):
            if row is None:
                return
            row.destroy()
            self._question_rows.remove(row)

        row = _QuestionRow(self._q_scroll, idx, on_delete=lambda: None)
        row.pack(fill="x", padx=4, pady=3)

        # Fix on_delete closure now that row exists
        row._on_delete = lambda r=row: self._delete_question(r)
        for widget in row.winfo_children():
            if isinstance(widget, ctk.CTkButton) and widget.cget("text") == "✕":
                widget.configure(command=row._on_delete)

        self._question_rows.append(row)

    def _delete_question(self, row: _QuestionRow) -> None:
        row.destroy()
        self._question_rows.remove(row)

    # ------------------------------------------------------------------
    # Student folder management
    # ------------------------------------------------------------------

    def _add_folders(self) -> None:
        paths = filedialog.askdirectory(mustexist=True)
        if paths:
            self._add_student_path(Path(paths))

    def _add_all_from_dir(self) -> None:
        parent = filedialog.askdirectory(
            title="Select parent directory — all immediate subdirectories will be added"
        )
        if not parent:
            return
        existing = {r.folder for r in self._student_rows}
        added = 0
        for sub in sorted(Path(parent).iterdir()):
            if sub.is_dir() and sub not in existing:
                self._add_student_path(sub)
                added += 1
        if added == 0:
            messagebox.showinfo("No new folders", "All subdirectories are already in the list.")

    def _add_student_path(self, path: Path) -> None:
        if any(r.folder == path for r in self._student_rows):
            return
        row = _StudentRow(self._s_scroll, path)
        row.pack(fill="x", padx=4, pady=1)
        self._student_rows.append(row)
        self._update_student_count()

    def _clear_students(self) -> None:
        for row in self._student_rows:
            row.destroy()
        self._student_rows.clear()
        self._update_student_count()

    def _update_student_count(self) -> None:
        n = len(self._student_rows)
        self._student_count_label.configure(text=f"{n} folder{'s' if n != 1 else ''}")

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def _run(self) -> None:
        if self._running:
            return

        # Collect valid questions
        questions = [r.to_config() for r in self._question_rows if r.is_complete()]
        if not questions:
            messagebox.showwarning(
                "No Questions",
                "Add at least one question with a label, JFF filename, and ZIP file.",
            )
            return

        # Collect enabled student folders
        folders = [r.folder for r in self._student_rows if r.enabled]
        if not folders:
            messagebox.showwarning("No Students", "Add at least one student folder.")
            return

        # Ask for output path
        out_path = filedialog.asksaveasfilename(
            title="Save Excel file as…",
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            initialfile="marks.xlsx",
        )
        if not out_path:
            return

        self._running = True
        self._run_btn.configure(state="disabled", text="Running…")
        self._progress_bar.set(0)
        self._progress_label.configure(text="")

        label_mode = {
            "Folder name": ROW_LABEL_FOLDER,
            "Short name":  ROW_LABEL_SHORT,
            "Student ID":  ROW_LABEL_ID,
        }.get(self._row_label_var.get(), ROW_LABEL_SHORT)

        score_fmt = {
            "X / N":     SCORE_FRACTION,
            "Numeric":   SCORE_NUMERIC,
            "%":         SCORE_PERCENT,
            "X / N (%)": SCORE_FULL,
        }.get(self._score_fmt_var.get(), SCORE_FRACTION)

        thread = threading.Thread(
            target=self._run_worker,
            args=(questions, folders, label_mode, score_fmt, Path(out_path)),
            daemon=True,
        )
        thread.start()

    def _run_worker(
        self,
        questions,
        folders,
        label_mode,
        score_fmt,
        out_path: Path,
    ) -> None:
        def on_progress(done: int, total: int, label: str) -> None:
            self.after(0, lambda: self._update_progress(done, total, label))

        try:
            results = self._runner.run(
                student_folders=folders,
                questions=questions,
                row_label_mode=label_mode,
                progress=on_progress,
            )
            self._exporter.export(
                results=results,
                questions=questions,
                output_path=out_path,
                score_format=score_fmt,
            )
            self.after(0, lambda: self._on_complete(out_path, len(results)))
        except Exception as exc:
            self.after(0, lambda: self._on_error(str(exc)))

    def _update_progress(self, done: int, total: int, label: str) -> None:
        self._progress_bar.set(done / total if total else 0)
        self._progress_label.configure(text=f"{done} / {total}  —  {label[:30]}")

    def _on_complete(self, out_path: Path, n_students: int) -> None:
        self._running = False
        self._run_btn.configure(state="normal", text="▶  Run & Export Excel")
        self._progress_bar.set(1)
        self._progress_label.configure(text=f"Done — {n_students} students")
        messagebox.showinfo(
            "Export complete",
            f"Results for {n_students} students saved to:\n{out_path}",
        )

    def _on_error(self, msg: str) -> None:
        self._running = False
        self._run_btn.configure(state="normal", text="▶  Run & Export Excel")
        messagebox.showerror("Error", f"Batch run failed:\n{msg}")
