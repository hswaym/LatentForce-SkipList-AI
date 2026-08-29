import os
from pathlib import Path
from typing import List, Optional


DEFAULT_IGNORED_DIRS = {"venv", ".venv", "__pycache__", ".git", ".pytest_cache", ".egg-info", "build", "dist"}


def find_python_files(root: str | Path, exclude: Optional[List[str]] = None) -> List[Path]:
    """Recursively find all Python (.py) files in root, skipping venv, .venv, __pycache__, .git, and excluded patterns."""
    root_path = Path(root).resolve()
    exclude_patterns = set(exclude) if exclude else set()
    python_files = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter out default ignored directories in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in DEFAULT_IGNORED_DIRS and d not in exclude_patterns
        ]

        for file in filenames:
            if file.endswith(".py") and file not in exclude_patterns:
                file_path = Path(dirpath) / file
                # Check if relative path matches any exclude pattern
                try:
                    rel_path = file_path.relative_to(root_path)
                    if any(part in exclude_patterns for part in rel_path.parts):
                        continue
                except ValueError:
                    pass
                python_files.append(file_path)

    return sorted(python_files)
