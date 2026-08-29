import html
import json
import os
from pathlib import Path
from typing import Dict, Any


def write_html(report_data: Dict[str, Any], output_path: str | Path) -> None:
    """Render a self-contained HTML report from report data dictionary."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    meta = report_data.get("meta", {})
    summary = report_data.get("summary", {})
    findings = report_data.get("findings", [])
    graph_data = report_data.get("graph", {})

    repo_raw = meta.get("repo_path", "")
    repo_name = os.path.basename(repo_raw.rstrip("/\\")) if repo_raw else "Repository"

    all_entry_points = meta.get("entry_points", [])
    declared_entries = []
    test_entries = []

    for ep in all_entry_points:
        parts = ep.split(".")
        simple_name = parts[-1]
        is_test = (
            simple_name.startswith("test_")
            or simple_name.startswith("Test")
            or any("test" in p.lower() for p in parts[:-1])
        )
        if is_test:
            test_entries.append(ep)
        else:
            declared_entries.append(ep)

    declared_str = ", ".join(declared_entries) if declared_entries else "None"
    test_str = ", ".join(test_entries) if test_entries else ""
    n_test_entries = len(test_entries)

    if n_test_entries > 0:
        entry_points_html = (
            f'<span class="entry-declared"><code>{html.escape(declared_str)}</code></span> '
            f'<details class="entry-tests" style="display: inline-block; margin-left: 0.5rem; vertical-align: top;">'
            f'<summary style="cursor: pointer; color: var(--primary); font-weight: 600;">+ {n_test_entries} test/fixture methods (auto-excluded from findings)</summary>'
            f'<span class="entry-test-list" style="display: block; margin-top: 0.35rem; max-width: 600px; word-break: break-word;"><code>{html.escape(test_str)}</code></span>'
            f'</details>'
        )
    else:
        entry_points_html = f'<span class="entry-declared"><code>{html.escape(declared_str)}</code></span>'

    high_med_findings = [f for f in findings if f.get("confidence") != "low"]
    low_conf_findings = [f for f in findings if f.get("confidence") == "low"]

    graph_json = json.dumps(graph_data or {"nodes": [], "edges": [], "collapsed": False, "collapse_reason": None})

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkipList Triage Report — {html.escape(repo_name)}</title>
    <style>
        :root {{
            --bg-color: #f1f5f9;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #475569;
            --border-color: #e2e8f0;
            --primary: #4f46e5;
            --primary-light: #eef2ff;
            --primary-border: #c7d2fe;
            --review-bg: #fffbeb;
            --review-border: #fcd34d;
            --review-txt: #92400e;
            --dead-badge-bg: #fef2f2;
            --dead-badge-txt: #991b1b;
            --dead-badge-border: #fecaca;
            --dup-badge-bg: #faf5ff;
            --dup-badge-txt: #6b21a8;
            --dup-badge-border: #e9d5ff;
            --conf-high-bg: #f0fdf4;
            --conf-high-txt: #166534;
            --conf-high-border: #bbf7d0;
            --conf-med-bg: #fffbeb;
            --conf-med-txt: #92400e;
            --conf-med-border: #fde68a;
            --conf-low-bg: #f8fafc;
            --conf-low-txt: #475569;
            --conf-low-border: #e2e8f0;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 3rem 1.5rem;
            line-height: 1.6;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}

        /* HERO BAND */
        .hero {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2.5rem;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        }}

        .hero-headline {{
            font-size: 3rem;
            font-weight: 800;
            color: var(--primary);
            margin: 0 0 1.5rem 0;
            letter-spacing: -0.03em;
            line-height: 1.1;
        }}

        .tiles-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.75rem;
        }}

        .tile {{
            background-color: var(--primary-light);
            border: 1px solid var(--primary-border);
            border-top: 4px solid var(--primary);
            border-radius: 12px;
            padding: 1.25rem 1.5rem;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}

        .tile:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(79, 70, 229, 0.08);
        }}

        .tile-review {{
            background-color: var(--review-bg);
            border-color: var(--review-border);
            border-top-color: #d97706;
        }}

        .tile-review:hover {{
            box-shadow: 0 4px 12px rgba(217, 119, 6, 0.1);
        }}

        .tile-val {{
            font-size: 2.25rem;
            font-weight: 800;
            color: var(--text-main);
            line-height: 1.2;
        }}

        .tile-lbl {{
            font-size: 0.8rem;
            color: var(--text-muted);
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 0.06em;
            margin-top: 0.35rem;
        }}

        .hero-sub {{
            font-size: 0.95rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border-color);
            padding-top: 1.25rem;
            margin: 0;
        }}

        .hero-sub code {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            background: #f1f5f9;
            padding: 0.2rem 0.45rem;
            border-radius: 6px;
            color: var(--text-main);
            font-size: 0.875rem;
        }}

        /* METHODOLOGY */
        .methodology {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            border-left: 4px solid #16a34a;
            color: #14532d;
            border-radius: 12px;
            padding: 1.15rem 1.5rem;
            font-size: 0.925rem;
            margin-bottom: 2.5rem;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
        }}

        /* SECTION HEADERS */
        h2 {{
            font-size: 1.5rem;
            font-weight: 800;
            margin: 0 0 1.25rem 0;
            color: var(--text-main);
            letter-spacing: -0.02em;
        }}

        /* FINDINGS TABLE */
        .table-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            overflow-x: auto;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            margin-bottom: 3rem;
        }}

        .review-card {{
            border-color: var(--review-border);
            border-top: 4px solid #d97706;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.925rem;
            table-layout: auto;
        }}

        th {{
            background: #f8fafc;
            padding: 1rem 1.25rem;
            font-size: 0.775rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
            font-weight: 700;
        }}

        th:hover {{
            background: #f1f5f9;
            color: var(--text-main);
        }}

        th .sort-icon {{
            display: inline-block;
            margin-left: 0.35rem;
            opacity: 0.5;
            font-size: 0.85em;
        }}

        td {{
            padding: 1rem 1.25rem;
            border-bottom: 1px solid var(--border-color);
            vertical-align: middle;
        }}

        tr.data-row {{
            cursor: pointer;
            transition: background-color 0.15s ease;
        }}

        tr.data-row:hover {{
            background-color: #f8fafc;
        }}

        tr.highlight-row {{
            background-color: #fef3c7 !important;
            transition: background-color 0.3s ease;
        }}

        .code-sym {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-weight: 600;
            color: var(--primary);
            max-width: 380px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        .code-file {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            color: var(--text-muted);
            font-size: 0.875rem;
            max-width: 250px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }}

        /* BADGES */
        .badge {{
            display: inline-block;
            padding: 0.25rem 0.6rem;
            border-radius: 6px;
            font-size: 0.725rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border: 1px solid transparent;
        }}

        .badge-dead {{ background: var(--dead-badge-bg); color: var(--dead-badge-txt); border-color: var(--dead-badge-border); }}
        .badge-duplicate {{ background: var(--dup-badge-bg); color: var(--dup-badge-txt); border-color: var(--dup-badge-border); }}
        .badge-conf-high {{ background: var(--conf-high-bg); color: var(--conf-high-txt); border-color: var(--conf-high-border); }}
        .badge-conf-medium {{ background: var(--conf-med-bg); color: var(--conf-med-txt); border-color: var(--conf-med-border); }}
        .badge-conf-low {{ background: var(--conf-low-bg); color: var(--conf-low-txt); border-color: var(--conf-low-border); }}

        /* DETAIL PANEL */
        tr.detail-row {{
            display: none;
            background: #fafafa;
        }}

        tr.detail-row.open {{
            display: table-row;
        }}

        .detail-panel {{
            padding: 1.25rem 1.5rem;
            font-size: 0.875rem;
            color: var(--text-main);
            border-left: 4px solid var(--primary);
            margin: 0.35rem 0;
            background: #ffffff;
            border-radius: 0 8px 8px 0;
            box-shadow: inset 0 1px 2px rgba(0,0,0,0.03);
            word-break: break-word;
        }}

        .detail-panel p {{
            margin: 0 0 0.5rem 0;
        }}

        .detail-panel p:last-child {{
            margin-bottom: 0;
        }}

        /* GRAPH CARD */
        .graph-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 1.5rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
            margin-bottom: 3rem;
        }}

        .graph-caption {{
            font-size: 0.875rem;
            color: var(--review-txt);
            background: var(--review-bg);
            border: 1px solid var(--review-border);
            border-radius: 8px;
            padding: 0.6rem 1rem;
            margin-bottom: 1rem;
            font-weight: 500;
        }}

        .graph-legend {{
            display: flex;
            gap: 1.25rem;
            margin-bottom: 1rem;
            font-size: 0.8rem;
            font-weight: 600;
        }}

        .legend-item {{
            display: flex;
            align-items: center;
            gap: 0.35rem;
        }}

        .legend-dot {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
        }}

        svg.graph-svg {{
            width: 100%;
            height: 460px;
            background: #f8fafc;
            border-radius: 10px;
            border: 1px solid var(--border-color);
        }}

        circle.graph-node {{
            cursor: pointer;
            transition: r 0.15s ease, stroke-width 0.15s ease;
        }}

        circle.graph-node:hover {{
            r: 10;
            stroke: #0f172a;
            stroke-width: 2.5px;
        }}

        text.node-label {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 10px;
            fill: #334155;
            pointer-events: none;
            user-select: none;
        }}

        line.graph-edge {{
            stroke: #cbd5e1;
            stroke-width: 1.5px;
            stroke-opacity: 0.7;
        }}

        /* NEEDS REVIEW SECTION */
        .empty-state {{
            background: var(--card-bg);
            border: 1px dashed var(--border-color);
            border-radius: 12px;
            padding: 2rem;
            color: var(--text-muted);
            font-size: 0.925rem;
            text-align: center;
        }}

        /* FOOTER */
        footer {{
            text-align: center;
            font-size: 0.85rem;
            color: var(--text-muted);
            margin-top: 4rem;
            border-top: 1px solid var(--border-color);
            padding-top: 2rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HERO BAND -->
        <div class="hero">
            <div class="hero-headline">{summary.get('safe_to_skip_pct', 0.0)}% safe to skip or consolidate</div>
            
            <div class="tiles-grid">
                <div class="tile">
                    <div class="tile-val">{summary.get('dead_functions', 0)}</div>
                    <div class="tile-lbl">Dead Functions ({summary.get('dead_lines', 0)} lines)</div>
                </div>
                <div class="tile">
                    <div class="tile-val">{summary.get('duplicate_clusters', 0)}</div>
                    <div class="tile-lbl">Duplicate Clusters ({summary.get('duplicate_lines', 0)} lines)</div>
                </div>
                <div class="tile tile-review">
                    <div class="tile-val">{summary.get('needs_review_functions', 0)}</div>
                    <div class="tile-lbl">Needs Review ({summary.get('needs_review_lines', 0)} lines)</div>
                </div>
                <div class="tile">
                    <div class="tile-val">{summary.get('safe_to_skip_lines', 0)}</div>
                    <div class="tile-lbl">Total Safe-to-Skip Lines</div>
                </div>
            </div>

            <p class="hero-sub">
                Analyzed <strong>{html.escape(repo_name)}</strong> — {meta.get('files_analyzed', 0)} files, {meta.get('total_functions', 0)} functions, {meta.get('total_lines', 0)} lines.<br/>
                Entry points: {entry_points_html}
            </p>
        </div>

        <!-- METHODOLOGY -->
        <div class="methodology">
            <strong>Methodology:</strong> Findings are traced from real entry points via whole-repo call-graph reachability; duplicates are structurally identical functions. Every finding lists its evidence and a confidence level — anything reachable only dynamically is surfaced for review, not asserted dead.
        </div>

        <!-- FINDINGS TABLE -->
        <h2>Triage Findings ({len(high_med_findings)})</h2>
        <div class="table-card">
            <table id="findingsTable">
                <thead>
                    <tr>
                        <th onclick="sortTable(0, 'number')">Priority <span class="sort-icon" id="sort-0">▼</span></th>
                        <th onclick="sortTable(1, 'string')">Type <span class="sort-icon" id="sort-1">↕</span></th>
                        <th onclick="sortTable(2, 'string')">Symbol <span class="sort-icon" id="sort-2">↕</span></th>
                        <th onclick="sortTable(3, 'string')">File:Lines <span class="sort-icon" id="sort-3">↕</span></th>
                        <th onclick="sortTable(4, 'number')">LOC <span class="sort-icon" id="sort-4">↕</span></th>
                        <th onclick="sortTable(5, 'string')">Confidence <span class="sort-icon" id="sort-5">↕</span></th>
                    </tr>
                </thead>
                <tbody>
"""

    for f in high_med_findings:
        f_id = f.get("id", "")
        f_type = f.get("type", "")
        f_sym = f.get("symbol", "")
        f_file = f.get("file", "")
        line_start = f.get("line_start", 0)
        line_end = f.get("line_end", 0)
        loc = f.get("lines", 0)
        conf = f.get("confidence", "high")
        priority = f.get("priority_score", 0)
        reason = f.get("reason", "")
        evidence = f.get("evidence", {})
        callers = evidence.get("callers", [])
        dup_of = evidence.get("duplicate_of", [])
        caveats = f.get("caveats", [])

        type_badge = f'<span class="badge badge-{html.escape(f_type)}">{html.escape(f_type.replace("_", " "))}</span>'
        conf_badge = f'<span class="badge badge-conf-{html.escape(conf)}">{html.escape(conf)}</span>'

        loc_str = f"{html.escape(f_file)}:{line_start}-{line_end}"

        detail_bits = [f"<p><strong>Reason:</strong> {html.escape(reason)}</p>"]
        if dup_of:
            detail_bits.append(f"<p><strong>Duplicate of:</strong> {html.escape(', '.join(dup_of))}</p>")
        if callers:
            detail_bits.append(f"<p><strong>Callers:</strong> {html.escape(', '.join(callers))}</p>")
        if caveats:
            detail_bits.append(f"<p><strong>Caveats:</strong> {html.escape(', '.join(caveats))}</p>")

        detail_html = "".join(detail_bits)

        html_content += f"""
                    <tr class="data-row" id="row-{f_id}" data-sym="{html.escape(f_sym)}" data-file="{html.escape(f_file)}" onclick="toggleDetail('{f_id}')">
                        <td><strong>{priority}</strong></td>
                        <td>{type_badge}</td>
                        <td class="code-sym" title="{html.escape(f_sym)}">{html.escape(f_sym)}</td>
                        <td class="code-file" title="{html.escape(loc_str)}">{html.escape(loc_str)}</td>
                        <td>{loc}</td>
                        <td>{conf_badge}</td>
                    </tr>
                    <tr id="detail-{f_id}" class="detail-row">
                        <td colspan="6">
                            <div class="detail-panel">
                                {detail_html}
                            </div>
                        </td>
                    </tr>
"""

    html_content += """
                </tbody>
            </table>
        </div>

        <!-- DEPENDENCY GRAPH -->
        <h2>Dependency Graph</h2>
        <div class="graph-card">
            <div id="graphCaption" class="graph-caption" style="display: none;"></div>
            
            <div class="graph-legend">
                <div class="legend-item"><div class="legend-dot" style="background: #16a34a;"></div> Reachable</div>
                <div class="legend-item"><div class="legend-dot" style="background: #dc2626;"></div> Dead</div>
                <div class="legend-item"><div class="legend-dot" style="background: #7c3aed;"></div> Duplicate</div>
                <div class="legend-item"><div class="legend-dot" style="background: #d97706;"></div> Needs Review</div>
            </div>

            <svg id="graphSvg" class="graph-svg" viewBox="0 0 900 440"></svg>
        </div>

        <!-- NEEDS REVIEW SECTION -->
        <h2>Needs Review</h2>
"""

    if low_conf_findings:
        html_content += """
        <div class="table-card review-card">
            <table>
                <thead>
                    <tr>
                        <th style="width: 80px;">ID</th>
                        <th style="width: 220px;">Symbol</th>
                        <th style="width: 180px;">File:Lines</th>
                        <th>Reason / Dynamic-Dispatch Caveats</th>
                    </tr>
                </thead>
                <tbody>
"""
        for f in low_conf_findings:
            f_id = f.get("id", "")
            f_sym = f.get("symbol", "")
            f_file = f.get("file", "")
            loc_str = f"{html.escape(f_file)}:{f.get('line_start', 0)}-{f.get('line_end', 0)}"
            reason = f.get("reason", "")
            caveats = ", ".join(f.get("caveats", []))

            html_content += f"""
                    <tr id="row-{f_id}" data-sym="{html.escape(f_sym)}" data-file="{html.escape(f_file)}">
                        <td><strong>{html.escape(f_id)}</strong></td>
                        <td class="code-sym" title="{html.escape(f_sym)}">{html.escape(f_sym)}</td>
                        <td class="code-file" title="{html.escape(loc_str)}">{html.escape(loc_str)}</td>
                        <td>{html.escape(reason)}<br/><span style="color: var(--review-txt); font-size: 0.825rem;">{html.escape(caveats)}</span></td>
                    </tr>
"""
        html_content += """
                </tbody>
            </table>
        </div>
"""
    else:
        html_content += """
        <div class="empty-state">
            No dynamic-reachability caveats flagged.
        </div>
"""

    html_content += f"""
        <!-- FOOTER -->
        <footer>
            Generated by SkipList — built with LatentCode. tool_version {html.escape(meta.get('tool_version', '0.1.0'))}, analyzed_at {html.escape(meta.get('analyzed_at', ''))}.
        </footer>
    </div>

    <!-- INLINE GRAPH DATA AND JS -->
    <script>
        const GRAPH_DATA = {graph_json};

        function toggleDetail(id) {{
            const row = document.getElementById('detail-' + id);
            if (row) {{
                row.classList.toggle('open');
            }}
        }}

        let sortDirs = {{}};

        function sortTable(colIndex, type) {{
            const table = document.getElementById("findingsTable");
            const tbody = table.querySelector("tbody");
            const dataRows = Array.from(tbody.querySelectorAll("tr.data-row"));

            const isAsc = !sortDirs[colIndex];
            sortDirs[colIndex] = isAsc;

            for (let i = 0; i <= 5; i++) {{
                const icon = document.getElementById('sort-' + i);
                if (icon) {{
                    icon.textContent = (i === colIndex) ? (isAsc ? '▲' : '▼') : '↕';
                }}
            }}

            dataRows.sort((a, b) => {{
                let aVal = a.cells[colIndex].textContent.trim();
                let bVal = b.cells[colIndex].textContent.trim();

                if (type === 'number') {{
                    aVal = parseFloat(aVal) || 0;
                    bVal = parseFloat(bVal) || 0;
                    return isAsc ? aVal - bVal : bVal - aVal;
                }} else {{
                    return isAsc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
                }}
            }});

            dataRows.forEach(row => {{
                const onclickAttr = row.getAttribute('onclick') || '';
                const match = onclickAttr.match(/'([^']+)'/);
                if (match) {{
                    const detailId = match[1];
                    const detailRow = document.getElementById('detail-' + detailId);
                    tbody.appendChild(row);
                    if (detailRow) {{
                        tbody.appendChild(detailRow);
                    }}
                }}
            }});
        }}

        function escapeJsHtml(str) {{
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }}

        // RENDER DEPENDENCY GRAPH VIA VANILLA SVG & FORCE-DIRECTED SIMULATION
        function renderGraph() {{
            const svg = document.getElementById("graphSvg");
            const caption = document.getElementById("graphCaption");
            if (!svg || !GRAPH_DATA || !GRAPH_DATA.nodes || GRAPH_DATA.nodes.length === 0) {{
                return;
            }}

            if (GRAPH_DATA.collapsed && GRAPH_DATA.collapse_reason) {{
                caption.style.display = "block";
                caption.textContent = "Showing file-level view — " + GRAPH_DATA.collapse_reason;
            }}

            const width = 900;
            const height = 440;
            const nodes = GRAPH_DATA.nodes.map((n, i) => ({{
                ...n,
                x: width / 2 + (Math.random() - 0.5) * 350,
                y: height / 2 + (Math.random() - 0.5) * 220,
                vx: 0,
                vy: 0
            }}));

            const nodeMap = {{}};
            nodes.forEach(n => {{ nodeMap[n.id] = n; }});

            const edges = (GRAPH_DATA.edges || []).map(e => ({{
                source: nodeMap[e.source],
                target: nodeMap[e.target]
            }})).filter(e => e.source && e.target);

            // Run simple 80-step force simulation
            for (let iter = 0; iter < 80; iter++) {{
                // Repulsion
                for (let i = 0; i < nodes.length; i++) {{
                    for (let j = i + 1; j < nodes.length; j++) {{
                        let dx = nodes[j].x - nodes[i].x;
                        let dy = nodes[j].y - nodes[i].y;
                        let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                        if (dist < 180) {{
                            let force = (180 - dist) / dist * 0.15;
                            nodes[i].vx -= dx * force;
                            nodes[i].vy -= dy * force;
                            nodes[j].vx += dx * force;
                            nodes[j].vy += dy * force;
                        }}
                    }}
                }}

                // Edge attraction
                edges.forEach(e => {{
                    let dx = e.target.x - e.source.x;
                    let dy = e.target.y - e.source.y;
                    let dist = Math.sqrt(dx * dx + dy * dy) || 1;
                    let force = (dist - 90) * 0.04;
                    e.source.vx += (dx / dist) * force;
                    e.source.vy += (dy / dist) * force;
                    e.target.vx -= (dx / dist) * force;
                    e.target.vy -= (dy / dist) * force;
                }});

                // Centering force and damping
                nodes.forEach(n => {{
                    n.vx += (width / 2 - n.x) * 0.01;
                    n.vy += (height / 2 - n.y) * 0.01;
                    n.x += Math.max(-12, Math.min(12, n.vx));
                    n.y += Math.max(-12, Math.min(12, n.vy));
                    n.vx *= 0.85;
                    n.vy *= 0.85;

                    n.x = Math.max(30, Math.min(width - 30, n.x));
                    n.y = Math.max(30, Math.min(height - 30, n.y));
                }});
            }}

            const statusColors = {{
                reachable: "#16a34a",
                dead: "#dc2626",
                duplicate: "#7c3aed",
                needs_review: "#d97706"
            }};

            let svgHtml = "";
            edges.forEach(e => {{
                svgHtml += `<line class="graph-edge" x1="${{e.source.x}}" y1="${{e.source.y}}" x2="${{e.target.x}}" y2="${{e.target.y}}" />`;
            }});

            nodes.forEach(n => {{
                const color = statusColors[n.status] || "#4f46e5";
                const label = n.symbol.split(".").pop();
                const r = GRAPH_DATA.collapsed ? 9 : 7;
                const safeSym = escapeJsHtml(n.symbol);
                const safeFile = escapeJsHtml(n.file);

                svgHtml += `
                    <g onclick="selectGraphNode('${{safeSym}}', '${{safeFile}}')">
                        <circle class="graph-node" cx="${{n.x}}" cy="${{n.y}}" r="${{r}}" fill="${{color}}" stroke="#ffffff" stroke-width="1.5">
                            <title>${{safeSym}} (${{n.loc}} LOC, ${{n.status}})</title>
                        </circle>
                        <text class="node-label" x="${{n.x + 10}}" y="${{n.y + 3}}">${{escapeJsHtml(label)}}</text>
                    </g>
                `;
            }});

            svg.innerHTML = svgHtml;
        }}

        function selectGraphNode(symbolName, filePath) {{
            const allRows = Array.from(document.querySelectorAll("tr[data-sym]"));
            let targetRow = allRows.find(r => r.getAttribute("data-sym") === symbolName);

            if (!targetRow && filePath) {{
                targetRow = allRows.find(r => r.getAttribute("data-file") === filePath);
            }}

            if (targetRow) {{
                targetRow.scrollIntoView({{ behavior: "smooth", block: "center" }});
                targetRow.classList.add("highlight-row");
                setTimeout(() => {{ targetRow.classList.remove("highlight-row"); }}, 2500);

                const onclickAttr = targetRow.getAttribute('onclick') || '';
                const match = onclickAttr.match(/'([^']+)'/);
                if (match) {{
                    const detailId = match[1];
                    const detailRow = document.getElementById('detail-' + detailId);
                    if (detailRow && !detailRow.classList.contains('open')) {{
                        toggleDetail(detailId);
                    }}
                }}
            }}
        }}

        window.addEventListener("DOMContentLoaded", renderGraph);
    </script>
</body>
</html>
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
