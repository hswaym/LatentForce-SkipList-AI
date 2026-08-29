import ast
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def parse_file(path: str | Path) -> Optional[ast.Module]:
    """Parse a Python source file into an AST Module node.

    Wraps file reading and parsing in try/except, logging errors and returning None if parsing fails.
    """
    file_path = Path(path)
    try:
        content = file_path.read_text(encoding="utf-8")
        return ast.parse(content, filename=str(file_path))
    except Exception as exc:
        logger.warning("Failed to parse %s: %s", file_path, exc)
        return None
