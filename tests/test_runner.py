"""Integration tests for TestRunner — ZIP loading, pairing, and full pipeline."""
import io
import zipfile
import pytest
from runner.test_runner import TestRunner
from tests.conftest import build_from_xml, make_zip, opts

_RUNNER = TestRunner()

# ── Minimal DFA accepting even-length strings ─────────────────────────────────
_DFA_EVEN = """\
<structure><type>fa</type><automaton>
  <state id="0" name="q0"><initial/><final/></state>
  <state id="1" name="q1"></state>
  <transition><from>0</from><to>1</to><read>a</read></transition>
  <transition><from>0</from><to>1</to><read>b</read></transition>
  <transition><from>1</from><to>0</to><read>a</read></transition>
  <transition><from>1</from><to>0</to><read>b</read></transition>
</automaton></structure>"""


def _make_jff(xml: str, tmp_path) -> object:
    jff = tmp_path / "machine.jff"
    jff.write_text(xml, encoding="utf-8")
    return jff


# ── ZIP loading and pairing ───────────────────────────────────────────────────

def test_runner_all_pass(tmp_path):
    jff  = _make_jff(_DFA_EVEN, tmp_path)
    zip_ = make_zip([("", "accept"), ("ab", "accept"), ("a", "reject")], tmp_path)
    report = _RUNNER.run(jff, zip_, opts())
    assert report.total  == 3
    assert report.passed == 3
    assert report.failed == 0


def test_runner_some_fail(tmp_path):
    # Deliberately wrong expected outputs for cases 2 and 3
    jff  = _make_jff(_DFA_EVEN, tmp_path)
    zip_ = make_zip([
        ("",   "accept"),   # correct
        ("ab", "reject"),   # wrong — should be accept
        ("a",  "accept"),   # wrong — should be reject
    ], tmp_path)
    report = _RUNNER.run(jff, zip_, opts())
    assert report.total  == 3
    assert report.passed == 1
    assert report.failed == 2


def test_runner_case_numbering(tmp_path):
    """Cases are numbered 1-based and results preserve input/expected."""
    jff  = _make_jff(_DFA_EVEN, tmp_path)
    zip_ = make_zip([("ab", "accept"), ("a", "reject")], tmp_path)
    report = _RUNNER.run(jff, zip_, opts())
    assert report.cases[0].index == 1
    assert report.cases[0].input_text == "ab"
    assert report.cases[0].expected == "accept"
    assert report.cases[1].index == 2


def test_runner_progress_callback(tmp_path):
    jff  = _make_jff(_DFA_EVEN, tmp_path)
    zip_ = make_zip([("", "accept"), ("ab", "accept"), ("a", "reject")], tmp_path)
    calls = []
    _RUNNER.run(jff, zip_, opts(), progress=lambda d, t: calls.append((d, t)))
    assert calls == [(1, 3), (2, 3), (3, 3)]


def test_runner_bad_jff_returns_load_error(tmp_path):
    bad_jff = tmp_path / "bad.jff"
    bad_jff.write_text("not xml", encoding="utf-8")
    zip_ = make_zip([("a", "accept")], tmp_path)
    report = _RUNNER.run(bad_jff, zip_, opts())
    assert report.load_error != ""
    assert report.total == 0


def test_runner_bad_zip_returns_load_error(tmp_path):
    jff = _make_jff(_DFA_EVEN, tmp_path)
    bad_zip = tmp_path / "bad.zip"
    bad_zip.write_bytes(b"not a zip file")
    report = _RUNNER.run(jff, bad_zip, opts())
    assert report.load_error != ""


def test_runner_empty_zip_returns_load_error(tmp_path):
    jff = _make_jff(_DFA_EVEN, tmp_path)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w"):
        pass
    empty_zip = tmp_path / "empty.zip"
    empty_zip.write_bytes(buf.getvalue())
    report = _RUNNER.run(jff, empty_zip, opts())
    assert report.load_error != ""


def test_runner_success_rate(tmp_path):
    jff  = _make_jff(_DFA_EVEN, tmp_path)
    zip_ = make_zip([("ab", "accept"), ("a", "reject"), ("b", "reject")], tmp_path)
    report = _RUNNER.run(jff, zip_, opts())
    assert report.success_rate == pytest.approx(1.0)


def test_runner_whitespace_trimmed_in_expected(tmp_path):
    """Trailing newline in output files must not cause a false failure."""
    jff = _make_jff(_DFA_EVEN, tmp_path)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("input/input1.txt", "ab\n")
        zf.writestr("output/output1.txt", "accept\n")
    zip_ = tmp_path / "ws.zip"
    zip_.write_bytes(buf.getvalue())
    report = _RUNNER.run(jff, zip_, opts())
    assert report.passed == 1
