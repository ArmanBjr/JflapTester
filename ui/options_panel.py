from __future__ import annotations

import customtkinter as ctk

from machines.base import MachineOptions, MachineType


class OptionsPanel(ctk.CTkFrame):
    """
    Context-sensitive options panel.
    Call show_for(machine_type) whenever the loaded machine changes.
    Call get_options() to retrieve the current MachineOptions.
    """

    def __init__(self, parent: ctk.CTkBaseClass, **kwargs) -> None:
        super().__init__(parent, fg_color="transparent", **kwargs)

        self._current_type: MachineType | None = None

        # ── TM: step limit + output mode ─────────────────────────────
        self._tm_frame = ctk.CTkFrame(self, fg_color="transparent")

        step_row = ctk.CTkFrame(self._tm_frame, fg_color="transparent")
        step_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(step_row, text="Step limit:", width=130, anchor="w",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._step_limit_var = ctk.StringVar(value="10000")
        ctk.CTkEntry(step_row, textvariable=self._step_limit_var,
                     width=110, justify="center").pack(side="left", padx=(8, 0))

        mode_row = ctk.CTkFrame(self._tm_frame, fg_color="transparent")
        mode_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(mode_row, text="Output mode:", width=130, anchor="w",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._tm_output_var = ctk.StringVar(value="accept / reject")
        ctk.CTkOptionMenu(
            mode_row,
            variable=self._tm_output_var,
            values=["accept / reject", "tape content"],
            width=170,
        ).pack(side="left", padx=(8, 0))

        # ── Multi-tape: tape selector ─────────────────────────────────
        self._tape_frame = ctk.CTkFrame(self, fg_color="transparent")

        tape_row = ctk.CTkFrame(self._tape_frame, fg_color="transparent")
        tape_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(tape_row, text="Output tape #:", width=130, anchor="w",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._tape_index_var = ctk.StringVar(value="1")
        ctk.CTkEntry(tape_row, textvariable=self._tape_index_var,
                     width=70, justify="center").pack(side="left", padx=(8, 0))
        ctk.CTkLabel(tape_row, text="(1-indexed)",
                     text_color=("gray50", "gray60"),
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(8, 0))

        # ── PDA: acceptance mode ──────────────────────────────────────
        self._pda_frame = ctk.CTkFrame(self, fg_color="transparent")

        pda_row = ctk.CTkFrame(self._pda_frame, fg_color="transparent")
        pda_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(pda_row, text="Accept by:", width=130, anchor="w",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._pda_accept_var = ctk.StringVar(value="final state")
        ctk.CTkOptionMenu(
            pda_row,
            variable=self._pda_accept_var,
            values=["final state", "empty stack"],
            width=170,
        ).pack(side="left", padx=(8, 0))

        # ── L-System: iteration count ─────────────────────────────────
        self._lsystem_frame = ctk.CTkFrame(self, fg_color="transparent")

        ls_row = ctk.CTkFrame(self._lsystem_frame, fg_color="transparent")
        ls_row.pack(fill="x", pady=(0, 6))
        ctk.CTkLabel(ls_row, text="Iterations:", width=130, anchor="w",
                     font=ctk.CTkFont(size=13)).pack(side="left")
        self._lsystem_iter_var = ctk.StringVar(value="3")
        ctk.CTkEntry(ls_row, textvariable=self._lsystem_iter_var,
                     width=70, justify="center").pack(side="left", padx=(8, 0))

        self._all_groups = [
            self._tm_frame,
            self._tape_frame,
            self._pda_frame,
            self._lsystem_frame,
        ]

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def show_for(self, machine_type: MachineType) -> None:
        self._current_type = machine_type
        for frame in self._all_groups:
            frame.pack_forget()

        match machine_type:
            case MachineType.TURING:
                self._tm_frame.pack(fill="x")
            case MachineType.TURING_MULTI:
                self._tm_frame.pack(fill="x")
                self._tape_frame.pack(fill="x")
            case MachineType.PDA:
                self._pda_frame.pack(fill="x")
            case MachineType.LSYSTEM:
                self._lsystem_frame.pack(fill="x")
            case _:
                pass   # FA, MEALY, MOORE, GRAMMAR need no extra options

    def hide_all(self) -> None:
        self._current_type = None
        for frame in self._all_groups:
            frame.pack_forget()

    def get_options(self) -> MachineOptions:
        opts = MachineOptions()

        try:
            opts.step_limit = max(1, int(self._step_limit_var.get()))
        except ValueError:
            opts.step_limit = 10_000

        opts.tm_output_mode = (
            "tape" if self._tm_output_var.get() == "tape content" else "accept_reject"
        )

        try:
            opts.tm_tape_index = max(0, int(self._tape_index_var.get()) - 1)
        except ValueError:
            opts.tm_tape_index = 0

        opts.pda_acceptance = (
            "empty_stack" if self._pda_accept_var.get() == "empty stack" else "final_state"
        )

        try:
            opts.lsystem_iterations = max(0, int(self._lsystem_iter_var.get()))
        except ValueError:
            opts.lsystem_iterations = 3

        return opts
