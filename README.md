# JFLAP Tester

An automated judge for JFLAP automata — load a `.jff` machine file and a ZIP of test cases, run all cases in one click, and see a colour-coded pass/fail report.

Built for automata theory courses where students submit JFLAP files and need to be tested against a ground-truth set of inputs and expected outputs.

---

## Features

- Supports **every machine type** available in JFLAP 7
- Accepts test cases as a **ZIP file** — no limit on number of cases
- **Auto-detects** the machine type from the `.jff` file
- **Context-sensitive options panel** — only shows settings relevant to the loaded machine
- Colour-coded results with pass/fail badge, input, expected output, and actual output
- Live **progress bar** during runs (background thread — UI never freezes)
- Light / Dark theme toggle

---

## Supported Machine Types

| Machine | Output produced |
|---|---|
| Finite Automaton (DFA / NFA) | `accept` or `reject` |
| Pushdown Automaton (PDA) | `accept` or `reject` |
| Turing Machine (single-tape) | `accept`/`reject` **or** tape content after halting |
| Turing Machine (multi-tape) | `accept`/`reject` **or** content of a selected tape |
| Mealy Machine | output string (concatenated per-transition outputs) |
| Moore Machine | output string (concatenated per-state outputs) |
| Grammar (CFG / Regular) | `accept` or `reject` (CYK membership test) |
| L-System | resulting string after N rewriting iterations |

---

## Requirements

- Python **3.10** or later  
- [customtkinter](https://github.com/TomSchimansky/CustomTkinter) — the only third-party dependency

Install it with:

```bash
pip install -r requirements.txt
```

---

## How to Run

```bash
python main.py
```

No build step, no configuration files.

---

## Test Case Format

Pack your test cases into a single `.zip` file with this structure:

```
tests.zip
├── input/
│   ├── input1.txt
│   ├── input2.txt
│   └── input3.txt
└── output/
    ├── output1.txt
    ├── output2.txt
    └── output3.txt
```

- Each `inputN.txt` contains the input string for test case N (plain text, one line).
- Each `outputN.txt` contains the **exact expected output** for test case N.
- Pairing is done by number — `input5.txt` is matched with `output5.txt`.
- Numbers do not need to be consecutive; any gaps are ignored.

### Expected output values by machine type

| Machine | Write in `outputN.txt` |
|---|---|
| FA, PDA | `accept` or `reject` |
| Turing Machine (accept/reject mode) | `accept` or `reject` |
| Turing Machine (tape mode) | the tape content after halting |
| Multi-tape TM | the content of the selected output tape |
| Mealy / Moore | the full output string |
| Grammar | `accept` or `reject` |
| L-System | the final string after N iterations |

Comparison is **case-sensitive** and **whitespace-trimmed** (leading/trailing spaces in the file are ignored).

---

## UI Walkthrough

### 1 — Load the machine

Click **Browse…** next to *JFLAP Machine (.jff)* and select a `.jff` file exported from JFLAP. The machine type is detected automatically and shown below the file name.

### 2 — Load the test cases

Click **Browse…** next to *Test Cases (.zip)* and select your ZIP archive. The number of test case pairs found is shown immediately.

### 3 — Configure options (if applicable)

An **Options** panel appears automatically for machine types that need extra configuration:

| Machine | Available options |
|---|---|
| Turing Machine | **Step limit** — maximum computation steps before declaring "did not halt"; **Output mode** — `accept / reject` (by final state) or `tape content` (what remains on the tape) |
| Multi-tape TM | Same as above plus **Output tape #** — which tape (1-indexed) to use as the result |
| PDA | **Accept by** — `final state` or `empty stack` |
| L-System | **Iterations** — number of rewriting steps to apply |

### 4 — Run

Click **▶ Run Tests**. Results appear on the right panel as they complete. Each row shows:

- A green **✓** or red **✗** badge
- Test case number
- The input string (truncated for long inputs)
- Expected output
- Actual output (highlighted in red on failure)

The summary bar at the top of the results shows total passed / total cases and the success rate.

---

## Project Structure

```
JflapTester/
├── main.py                    # Entry point
├── requirements.txt
├── JFLAP7.1.jar               # JFLAP reference (not used at runtime)
│
├── parser/
│   ├── jflap_parser.py        # Reads .jff XML → typed data objects
│   └── models.py              # Data classes for all machine types
│
├── machines/
│   ├── base.py                # BaseMachine ABC, RunResult, MachineOptions
│   ├── factory.py             # build_machine(data) → correct simulator
│   ├── fa.py                  # DFA / NFA (BFS + epsilon closure)
│   ├── pda.py                 # Nondeterministic PDA (BFS over configs)
│   ├── turing.py              # Single-tape TM
│   ├── multitape.py           # Multi-tape TM
│   ├── mealy.py               # Mealy transducer
│   ├── moore.py               # Moore transducer
│   ├── grammar.py             # CFG membership via CYK (CNF conversion included)
│   └── lsystem.py             # L-System string rewriter
│
├── runner/
│   └── test_runner.py         # ZIP loader, test pairing, run pipeline, RunReport
│
└── ui/
    ├── main_window.py         # App window (customtkinter)
    ├── options_panel.py       # Context-sensitive options widget
    └── results_panel.py       # Scrollable colour-coded results widget
```

---

## Architecture Notes

- Every machine simulator is a subclass of `BaseMachine` and implements a single method: `run(input_string, options) → RunResult`.
- The parser produces typed data objects (e.g. `FAData`, `TMData`); `factory.build_machine()` maps these to the right simulator — adding a new machine type only requires a new data class, a new simulator, and one line in the factory.
- The UI runs tests in a **daemon thread** and uses `after()` to push progress updates to the main thread safely.
- String comparison is done in `TestRunner._compare()` — one place to change if you need regex or partial matching.

---

## License

MIT
