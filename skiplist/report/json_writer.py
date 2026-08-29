import json
from dataclasses import asdict
from pathlib import Path
from skiplist.models import Report


def write_json(report: Report, output_path: str | Path) -> None:
    """Serialize the SkipList Report model into a formatted JSON output file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = asdict(report)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
