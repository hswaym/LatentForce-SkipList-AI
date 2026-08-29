
# SkipList

**Know what to skip before you migrate.**

> 23.1% of a legacy sample codebase is safe to skip or consolidate before a migration — with every finding backed by evidence and a confidence level.

---

## The problem

Migration budgets get burned porting code nobody runs. Before a team spends weeks moving a legacy Python codebase to a new stack, someone has to answer a boring but expensive question: *what in here actually matters?*

Existing dead-code tools (e.g. `vulture`) flag unused symbols file-by-file — no cross-module reachability, no duplicate detection, and no way to tell a confident finding from a guess.

## What SkipList does differently

SkipList combines three things into one number:

1. **Whole-repo call-graph reachability** from real entry points — true dead code, not per-file guesses.
2. **Duplicate-logic clustering** across modules — "consolidate these before you port them."
3. **Effort-weighted prioritization** — a ranked list topped by the biggest, highest-confidence wins.

**The credibility mechanism:** "safe to skip" is a strong claim, so every finding carries evidence and a confidence level. Anything touched by dynamic dispatch (`getattr`, `eval`, `__import__`, `importlib`, `globals()`/`locals()`) is downgraded to **`confidence: low`** and routed to a separate **Needs Review** bucket — never asserted safe. SkipList defaults conservative: it would rather under-claim than tell someone to delete code they need.

This also means test suites don't get falsely flagged: `test_*` functions, `unittest.TestCase` methods (`setUp`/`tearDown`/test methods), and `@pytest.fixture` functions are treated as implicitly reachable, since test runners invoke them by convention rather than by static call — the same category of risk as dynamic dispatch, just via a different mechanism.

The HTML report includes an interactive **dependency graph** — reachable, dead, duplicate, and needs-review functions rendered as connected (or deliberately disconnected) nodes, so you can see at a glance what's actually wired into the program versus orphaned.

## Installation
=======
# SkipList (LatentForce-SkipList-AI)

> **Pre-Migration Code-Triage Engine:** Finds dead code and structural duplicates across legacy Python codebases so migration teams scope real work first.

---

## 📸 Overview & Visual Reports

| Hero Dashboard | Needs Review (Dynamic Dispatch) |
| :---: | :---: |
| ![Hero Summary](docs/screenshots/hero-fixture.png) | ![Needs Review Section](docs/screenshots/needs-review-fixture.png) |

| Interactive Dependency Graph |
| :---: |
| ![Dependency Graph](docs/screenshots/dependency-graph-fixture.png) |

---

## 🎯 The Problem & What SkipList Does Differently

When migrating or modernizing legacy Python codebases, migration teams waste significant effort refactoring and rewriting code that is never executed at runtime or duplicating identical helper logic across multiple modules. Standard static linters often produce high numbers of false positives by asserting dynamically invoked functions dead.

**SkipList solves this by providing conservative, evidence-backed code triage:**
1. **Whole-Repo Call-Graph Reachability:** Builds a directed call graph across modules and traces reachability from real entry points (main functions, `if __name__ == "__main__":` guards, console scripts, web routes, CLI commands, and test discovery roots).
2. **Dynamic-Dispatch Credibility Mechanism:** Detects runtime reflection patterns (`getattr`, `setattr`, `globals()`, `locals()`, `eval`, `exec`, `importlib`). Statically unreachable code in dynamic modules is demoted to **`confidence = "low"`** ("Needs Review") with explicit caveats rather than falsely asserted dead.
3. **Test-Discovery Entry Points:** Automatically treats `test_*` functions, `unittest.TestCase` methods (`setUp`, `tearDown`, test cases), and `@pytest.fixture` functions as reachability roots so test helpers are never misflagged as dead.
4. **Structural Duplicate Detection:** Normalizes AST function nodes (stripping docstrings and standardizing parameter/variable names while preserving API surface) to group identical functions into duplicate clusters and select live keepers.

---

## 🛠️ Installation
>>>>>>> 904ba21 (docs: add README with validation results and screenshots)

```bash
python -m pip install -e .
```

## Usage

**Full analysis** — runs the pipeline (discovery, AST parsing, symbol table, call-graph reachability, duplicate clustering, priority scoring) and emits report files:

```bash
skiplist analyze <path> \
  [--entry module:function] \
  [--exclude pattern] \
  [--frameworks] \
  [--format json|html|both] \
  [--out output_dir]
```

- `--entry` — declare additional entry points beyond the auto-detected ones (`__main__`, `main()`, `console_scripts`).
- `--frameworks` — enable framework-aware entry-point detection for Flask, FastAPI, Click, Typer, and Celery routes/commands.
- `--format` — choose `report.html` (interactive, self-contained, offline-safe), `findings.json` (the structured findings + call-graph contract), or both.

**Print the symbol table** — every defined function/method/class with exact file:line ranges and LOC:

```bash
skiplist symbols <path>
```

**Inspect dead-code candidates and entry points** directly, without generating a full report:

```bash
skiplist deadcode <path> [--frameworks]
```

**Run the test suite:**
=======
---

## 🚀 Usage

### 📊 1. Codebase Triage (`skiplist analyze`)

Run a full triage analysis on a Python project and generate both interactive HTML dashboards and structured JSON exports:

```bash
skiplist analyze "C:\path\to\your\project" --format both --out report.html --frameworks
```

* **`report.html`:** Self-contained, offline-safe interactive dashboard featuring summary tiles, methodology guidelines, sortable findings tables, expandable evidence details, and an interactive SVG force-directed dependency graph.
* **`findings.json`:** Machine-readable data contract containing prioritized findings and serialized call-graph nodes/edges.

**Useful Flags:**
* `--frameworks`: Enable framework-aware entry point detection for `Flask`/`FastAPI` routes, `Click`/`Typer` commands, and `Celery` tasks.
* `--format {html,json,both}`: Specify report format (default: `html`).
* `--entry <dotted_name>`: Manually specify custom entry points (repeatable, e.g. `--entry my_app.main`).
* `--exclude <pattern>`: Skip specific file/folder patterns (repeatable, e.g. `--exclude "node_modules/*"`).

---

### 🔍 2. Symbol Table Generation (`skiplist symbols`)

List all defined functions, methods, and classes with line ranges and exact LOC:

```bash
skiplist symbols fixtures/legacy_sample
```

---

### ☠️ 3. Inspect Reachability & Dead Candidates (`skiplist deadcode`)

Inspect detected entry points and unreachable candidate symbols:

```bash
skiplist deadcode fixtures/legacy_sample --frameworks
```

---

### 🧪 4. Automated Test Suite (`pytest -q`)

Run the full automated test suite:
>>>>>>> 904ba21 (docs: add README with validation results and screenshots)

```bash
pytest -q
```

<<<<<<< HEAD
**Quick trial on the included fixture** (known ground truth, good for a first run):

```bash
skiplist analyze fixtures/legacy_sample --format both --out report.html --frameworks
```

Output: `report.html` — a sortable findings table, evidence panel per finding, and a distinct Needs Review section — and/or `findings.json`, the stable engine↔report contract.

## Validated on

**Correctness** — verified against known ground truth:

| Target | Files | Functions | Result |
|---|---|---|---|
| `fixtures/legacy_sample` (hand-built, ground truth known) | 8 | 12 | 23.1% safe to skip (10 dead + 5 duplicate lines / 65 total), matching expected classification exactly |

**Scale & stability** — verified it runs cleanly on a real, non-trivial codebase:

| Target | Files | Lines | Functions | Runtime | Crashes |
|---|---|---|---|---|---|
| [`bottlepy/bottle`](https://github.com/bottlepy/bottle) | 30 | 9,192 | 946 | ~0.5s | 0 |

We deliberately report these as two separate claims rather than one blended number. Testing on bottle surfaced real edge cases in nested-function reachability (locally-defined closures inside test methods weren't fully traced), which taught us the "safe to skip" percentage on complex real-world code needs more validation before we'd stand behind it as a headline figure. Rather than paper over that, we're reporting the fixture number — where we have full ground truth — as the trustworthy metric, and using bottle to demonstrate the tool runs fast and doesn't crash at real-world scale. See **Limitations** below.

Test suite: `pytest -q` — 11 passed, covering reachability, the dynamic-dispatch guard, duplicate clustering, and the test-discovery guard.

## Limitations (read this before trusting a number)

- **Nested/locally-defined functions (closures) are not fully traced by the reachability engine yet.** When a function calls another function defined *inside* it (or inside another function), and that inner function is itself the thing being checked for reachability, the current call graph can miss the connection — leading to false "dead" or false "duplicate" flags on inner closures. Discovered while validating on bottle's test suite (nested test helper closures). This is the reason we report bottle as a scale/stability check rather than a trustworthy percentage — see **Validated on** above.
- **Dynamic-dispatch detection is pattern-based, not exhaustive.** SkipList downgrades confidence for modules using `getattr`/`setattr`/`globals`/`locals`/`eval`/`exec`/`__import__`/`importlib`. Other reflection patterns — custom `__getattr__` overrides, metaclasses, decorator factories that register callables indirectly — are not currently detected and could still be misclassified. When in doubt, check the Needs Review section and the evidence panel before deleting anything.
- **Framework-aware entry points currently cover Flask, FastAPI, Click, Typer, and Celery.** Other frameworks' routing/registration conventions aren't recognized yet and may cause false "dead" flags in codebases that use them.
- **Import resolution is best-effort**, not a full static type/import solver — dynamic or conditional imports can be missed.
- We'd rather disclose a known gap than round it off — that's the same conservative-by-default principle the tool itself is built on.

## SkillPatch

Built using the **`pytest-skill`** test-scaffolding skill, invoked to scaffold and structure the pytest suite covering reachability analysis, the dynamic-dispatch guard, AST symbol parsing, and duplicate clustering.

## Screenshots

**Hero stats** (`fixtures/legacy_sample`):

![Hero stats: 23.1% safe to skip or consolidate, 4 dead functions, 1 duplicate cluster, 2 needs review, 15 total safe-to-skip lines](docs/screenshots/hero-fixture.png)

**Needs Review** — dynamic-dispatch findings correctly downgraded, never asserted dead:

![Needs Review table showing F006 dispatch.export_data and F007 dispatch.import_data, both flagged as statically unreachable but not asserted dead due to dynamic dispatch in the module](docs/screenshots/needs-review-fixture.png)

**Dependency graph** — reachable functions (green) vs. dead code (red, no incoming edges) vs. duplicates (purple) vs. needs-review dynamic-dispatch functions (orange), at a glance:

![Dependency graph showing main, create_order, charge, and format_amount connected and reachable in green; render_amount as a purple duplicate; export_data and import_data as orange needs-review dynamic-dispatch functions; and orphan_one, orphan_two, cancel_order, deprecated_refund as disconnected red dead-code nodes](docs/screenshots/dependency-graph-fixture.png)

---

Built solo, end-to-end, with [LatentCode](https://latentcode.dev) writing 100% of the implementation — for **BuildSprint 2026**.
=======
---

## 🧪 Validation Results

### 1. Ground-Truth Fixture (`fixtures/legacy_sample`)
- **Files & LOC:** 8 files, 65 lines of code, 12 functions/methods.
- **Results:** 15 safe-to-skip lines (**23.1%**).
- **Accuracy:** Correctly identified 4 dead functions, 1 duplicate cluster (`legacy_format.render_amount` duplicating `formatting.format_amount`), and 2 needs-review dynamic-dispatch functions (`dispatch.export_data`, `dispatch.import_data`).

### 2. Real OSS Production Repo Validation (`bottle`)
- **Files & LOC:** 30 files, 9,192 lines of code, 946 functions/methods.
- **Execution Time:** ~0.5 seconds (zero crashes or hangs).
- **Results:** 2,309 safe-to-skip lines (**31.3%** safe to skip/consolidate) across 320 findings (265 dead code, 44 duplicate clusters, 11 needs review).
- **Scale Guard:** Automatically collapsed the 946-function graph to 30 file-level module nodes with status color aggregation (`14` green, `11` red, `2` purple) for performance and readability.

---

## ⚠️ Limitations & Known Gaps

1. **Nested Closures & Lambda Functions:** Call graph edge extraction currently tracks top-level module functions, async functions, and class methods. Nested closures and lambda functions defined inside function bodies are not yet fully mapped as separate call-graph nodes.
2. **Dynamic String Evaluation:** Calls executed via string evaluation or complex runtime monkey-patching without explicit module-level reflection markers may require manual review under the "Needs Review" category.

---

## 🧩 Agent Skill Declaration

* **SkillPatch Skill Used:** `pytest-skill` (`.latentcode/skills/pytest-skill/`)
* **Purpose:** Installed via SkillPatch to scaffold, structure, and validate the automated unit and integration test suite (`tests/`).

---

## 📜 License

MIT License
>>>>>>> 904ba21 (docs: add README with validation results and screenshots)
