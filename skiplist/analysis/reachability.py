from typing import List, Set, Dict, Any, Optional
import networkx as nx
from skiplist.models import Symbol


def is_dunder_symbol(symbol: Symbol) -> bool:
    """Check if a symbol is a class dunder method (e.g., __init__, __enter__)."""
    name_part = symbol.qualified_name.split(".")[-1]
    return name_part.startswith("__") and name_part.endswith("__")


def find_dead_code(
    call_graph: nx.DiGraph,
    entry_points: Set[str],
    symbol_table: List[Symbol],
    module_alls: Optional[Dict[str, Set[str]]] = None
) -> List[Symbol]:
    """Find dead code candidates by computing reachability from entry points over the call graph."""
    reached: Set[str] = set()

    # Initial seeds: explicit entry points
    seeds = set(entry_points)

    symbol_map: Dict[str, Symbol] = {sym.qualified_name: sym for sym in symbol_table}

    # Add implicit entry points / reachable guards:
    for qual_name, sym in symbol_map.items():
        if sym.kind == "method" and is_dunder_symbol(sym):
            seeds.add(qual_name)

        if module_alls:
            mod_name = ".".join(qual_name.split(".")[:-1])
            simple_name = qual_name.split(".")[-1]
            if mod_name in module_alls and simple_name in module_alls[mod_name]:
                seeds.add(qual_name)

    # Perform BFS / reachability traversal over call_graph
    for seed in seeds:
        if seed in call_graph:
            reached.add(seed)
            descendants = nx.descendants(call_graph, seed)
            reached.update(descendants)

    # Dead candidates = Symbol objects whose qualified_name was never reached
    dead_symbols = [
        sym for sym in symbol_table
        if sym.qualified_name not in reached
    ]

    return dead_symbols
