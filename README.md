# LatentForce-SkipList-AI

Pre-migration code-triage tool — finds dead & duplicate code so migration teams scope real work first.

## Features
- **Dead Code Detection:** Scans Python projects for unused functions and classes.
- **Duplicate Code Detection:** Identifies structural function duplicates across files using AST normalization.
- **Reporting:** Generates detailed JSON data export and HTML reports.

## Installation

```bash
python -m pip install -e .
```

## Usage

Run `skiplist analyze` on target directory:

```bash
skiplist analyze examples/sample_project --html report.html --json findings.json
```

## Running Tests

```bash
python -m unittest discover tests
```

## License
MIT
