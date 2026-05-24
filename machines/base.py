from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class MachineType(Enum):
    FA = "fa"
    PDA = "pda"
    TURING = "turing"
    TURING_MULTI = "turing_multi"
    MEALY = "mealy"
    MOORE = "moore"
    GRAMMAR = "grammar"
    LSYSTEM = "lsystem"


class RunStatus(Enum):
    ACCEPTED = auto()
    REJECTED = auto()
    HALTED = auto()       # TM halted normally (use tape as output)
    DID_NOT_HALT = auto() # TM exceeded step limit
    ERROR = auto()


@dataclass
class RunResult:
    status: RunStatus
    output: str = ""      # tape content, transducer output, or derived string
    steps: int = 0
    error: str = ""

    def display(self) -> str:
        """Human-readable result for comparison against expected output."""
        if self.status == RunStatus.ACCEPTED:
            return "accept"
        if self.status == RunStatus.REJECTED:
            return "reject"
        if self.status == RunStatus.DID_NOT_HALT:
            return "did not halt"
        if self.status == RunStatus.ERROR:
            return f"error: {self.error}"
        return self.output  # HALTED → tape/transducer output


@dataclass
class MachineOptions:
    """Runtime options passed to a simulator at run-time."""
    # TM options
    step_limit: int = 10_000
    tm_output_mode: str = "accept_reject"   # "accept_reject" | "tape"
    tm_tape_index: int = 0                  # which tape to return for multi-tape TM
    # PDA options
    pda_acceptance: str = "final_state"     # "final_state" | "empty_stack"
    # L-System options
    lsystem_iterations: int = 3


class BaseMachine(ABC):
    """Abstract base for all JFLAP machine simulators."""

    @property
    @abstractmethod
    def machine_type(self) -> MachineType:
        ...

    @abstractmethod
    def run(self, input_string: str, options: MachineOptions) -> RunResult:
        """Simulate the machine on the given input and return a RunResult."""
        ...
