from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Symbol:
    qualified_name: str
    kind: str  # "function" | "method" | "class"
    file: str  # path relative to repo root
    line_start: int
    line_end: int
    lines: int


@dataclass
class Meta:
    repo_path: str
    analyzed_at: str
    tool_version: str = "0.1.0"
    files_analyzed: int = 0
    total_functions: int = 0
    total_lines: int = 0
    entry_points: List[str] = field(default_factory=list)


@dataclass
class Summary:
    dead_functions: int = 0
    dead_lines: int = 0
    needs_review_functions: int = 0
    needs_review_lines: int = 0
    duplicate_clusters: int = 0
    duplicate_lines: int = 0
    safe_to_skip_lines: int = 0
    safe_to_skip_pct: float = 0.0


@dataclass
class Evidence:
    callers: List[str] = field(default_factory=list)
    duplicate_of: List[str] = field(default_factory=list)


@dataclass
class Finding:
    id: str
    type: str
    symbol: str
    file: str
    line_start: int
    line_end: int
    lines: int
    reason: str
    evidence: Evidence
    confidence: str = "high"
    caveats: List[str] = field(default_factory=list)
    priority_score: int = 0


@dataclass
class GraphNode:
    id: str
    symbol: str
    file: str
    loc: int
    status: str  # "reachable" | "dead" | "duplicate" | "needs_review"
    functions_count: Optional[int] = None


@dataclass
class GraphEdge:
    source: str
    target: str


@dataclass
class GraphExport:
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    edges: List[Dict[str, Any]] = field(default_factory=list)
    collapsed: bool = False
    collapse_reason: Optional[str] = None


@dataclass
class Report:
    meta: Meta
    summary: Summary
    findings: List[Finding] = field(default_factory=list)
    graph: Optional[GraphExport] = None
