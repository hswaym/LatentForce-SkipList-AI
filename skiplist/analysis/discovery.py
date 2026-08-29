import os
import fnmatch
from pathlib import Path
from typing import List, Optional

DEFAULT_IGNORED_DIRS = {"venv", ".venv", "__pycache__", ".git", ".pytest_cache", ".egg-info", "build", "dist"}


def find_python_files(root: str | Path, exclude: Optional[List[str]] = None) -> List[Path]:
    """Recursively find all Python (.py) files in root, skipping venv, .venv, __pycache__, .git, build, dist, and any excluded patterns."""
    root_path = Path(root).resolve()
    exclude_patterns = set(exclude) if exclude else set()
    python_files = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Filter out default ignored directories in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in DEFAULT_IGNORED_DIRS and not any(fnmatch.fnmatch(d, pat) for pat in exclude_patterns)
        ]

        for file in filenames:
            if file.endswith(".py"):
                file_path = Path(dirpath) / file
                rel_path_str = str(file_path.relative_to(root_path)).replace("\\", "/")
                
                # Check file or relative path against exclude patterns
                if any(fnmatch.fnmatch(file, pat) or fnmatch.fnmatch(rel_path_str, pat) for pat in exclude_patterns):
                    continue

                python_files.append(file_path)

    return sorted(python_files)
