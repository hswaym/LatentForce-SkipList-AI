import ast
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def parse_file(path: str | Path) -> Optional[ast.Module]:
    """Parse a Python source file into an AST Module node.

    Wraps file reading and ast.parse in try/except; on SyntaxError or reading failure,
    logs a warning and returns None without crashing.
    """
    file_path = Path(path)
    try:
        content = file_path.read_text(encoding="utf-8")
        return ast.parse(content, filename=str(file_path))
    except (SyntaxError, Exception) as exc:
        logger.warning("Skipping file %s due to parsing error: %s", file_path, exc)
        return None
