"""
Shared helpers for all test modules.
Not pytest fixtures — plain functions imported directly by each test file.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from machines.base import MachineOptions
from machines.factory import build_machine
from parser.jflap_parser import JFLAPParser


def build_from_xml(xml: str, tmp_path: Path):
    """Write xml to a temp .jff, parse it, return (data, machine)."""
    jff = tmp_path / "machine.jff"
    jff.write_text(xml, encoding="utf-8")
    parser = JFLAPParser()
    data = parser.parse(jff)
    return data, build_machine(data)


def make_zip(pairs: list[tuple[str, str]], tmp_path: Path) -> Path:
    """
    Create a ZIP file with input/inputN.txt and output/outputN.txt pairs.
    Returns the path to the written ZIP.
    """
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for i, (inp, out) in enumerate(pairs, 1):
            zf.writestr(f"input/input{i}.txt", inp)
            zf.writestr(f"output/output{i}.txt", out)
    zip_path = tmp_path / "tests.zip"
    zip_path.write_bytes(buf.getvalue())
    return zip_path


def opts(**kwargs) -> MachineOptions:
    """Return a MachineOptions with overridden fields."""
    o = MachineOptions()
    for k, v in kwargs.items():
        setattr(o, k, v)
    return o
