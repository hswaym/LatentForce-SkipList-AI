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

    repo_raw = meta.get("repo_path", "")
    repo_name = os.path.basename(repo_raw.rstrip("/\\")) if repo_raw else "Repository"

    entry_points_str = ", ".join(meta.get("entry_points", [])) or "None"

    high_med_findings = [f for f in findings if f.get("confidence") != "low"]
    low_conf_findings = [f for f in findings if f.get("confidence") == "low"]

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkipList Triage Report — {html.escape(repo_name)}</title>
    <style>
        :root {{
            --bg-color: #f8fafc;
            --card-bg: #ffffff;
            --text-main: #0f172a;
            --text-muted: #475569;
            --border-color: #e2e8f0;
            --primary: #2563eb;
            --primary-bg: #eff6ff;
            --dead-badge-bg: #fef2f2;
            --dead-badge-txt: #dc2626;
            --dup-badge-bg: #f3e8ff;
            --dup-badge-txt: #7c3aed;
            --conf-high-bg: #dcfce7;
            --conf-high-txt: #16a34a;
            --conf-med-bg: #fef3c7;
            --conf-med-txt: #d97706;
            --conf-low-bg: #f1f5f9;
            --conf-low-txt: #475569;
        }}

        body {{
            font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-main);
            margin: 0;
            padding: 2rem 1rem;
            line-height: 1.5;
        }}

        .container {{
            max-width: 1100px;
            margin: 0 auto;
        }}

        /* HERO BAND */
        .hero {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}

        .hero-headline {{
            font-size: 2.5rem;
            font-weight: 800;
            color: var(--primary);
            margin: 0 0 1.25rem 0;
            letter-spacing: -0.025em;
        }}

        .tiles-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 1.25rem;
        }}

        .tile {{
            background-color: var(--primary-bg);
            border: 1px solid #dbeafe;
            border-radius: 8px;
            padding: 1rem 1.25rem;
        }}

        .tile-val {{
            font-size: 1.75rem;
            font-weight: 700;
            color: var(--text-main);
        }}

        .tile-lbl {{
            font-size: 0.85rem;
            color: var(--text-muted);
            text-transform: uppercase;
            font-weight: 600;
            letter-spacing: 0.05em;
        }}

        .hero-sub {{
            font-size: 0.95rem;
            color: var(--text-muted);
            border-top: 1px solid var(--border-color);
            padding-top: 1rem;
            margin: 0;
        }}

        .hero-sub code {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            background: #f1f5f9;
            padding: 0.15rem 0.35rem;
            border-radius: 4px;
        }}

        /* METHODOLOGY */
        .methodology {{
            background: #f0fdf4;
            border: 1px solid #bbf7d0;
            color: #166534;
            border-radius: 8px;
            padding: 0.9rem 1.25rem;
            font-size: 0.9rem;
            margin-bottom: 2rem;
        }}

        /* SECTION HEADERS */
        h2 {{
            font-size: 1.35rem;
            font-weight: 700;
            margin: 0 0 1rem 0;
            color: var(--text-main);
        }}

        /* FINDINGS TABLE */
        .table-card {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            margin-bottom: 2.5rem;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.925rem;
        }}

        th {{
            background: #f8fafc;
            padding: 0.85rem 1rem;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-color);
            cursor: pointer;
            user-select: none;
            white-space: nowrap;
        }}

        th:hover {{
            background: #f1f5f9;
            color: var(--text-main);
        }}

        th .sort-icon {{
            display: inline-block;
            margin-left: 0.25rem;
            opacity: 0.4;
        }}

        td {{
            padding: 0.85rem 1rem;
            border-bottom: 1px solid var(--border-color);
            vertical-align: middle;
        }}

        tr.data-row {{
            cursor: pointer;
            transition: background 0.15s ease;
        }}

        tr.data-row:hover {{
            background-color: #f8fafc;
        }}

        .code-sym {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-weight: 600;
            color: var(--primary);
        }}

        .code-file {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            color: var(--text-muted);
            font-size: 0.875rem;
        }}

        /* BADGES */
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }}

        .badge-dead {{ background: var(--dead-badge-bg); color: var(--dead-badge-txt); }}
        .badge-duplicate {{ background: var(--dup-badge-bg); color: var(--dup-badge-txt); }}
        .badge-conf-high {{ background: var(--conf-high-bg); color: var(--conf-high-txt); }}
        .badge-conf-medium {{ background: var(--conf-med-bg); color: var(--conf-med-txt); }}
        .badge-conf-low {{ background: var(--conf-low-bg); color: var(--conf-low-txt); }}

        /* DETAIL PANEL */
        tr.detail-row {{
            display: none;
            background: #fafafa;
        }}

        tr.detail-row.open {{
            display: table-row;
        }}

        .detail-panel {{
            padding: 1rem 1.25rem;
            font-size: 0.875rem;
            color: var(--text-main);
            border-left: 3px solid var(--primary);
            margin: 0.25rem 0;
        }}

        .detail-panel p {{
            margin: 0 0 0.5rem 0;
        }}

        .detail-panel p:last-child {{
            margin-bottom: 0;
        }}

        /* NEEDS REVIEW SECTION */
        .empty-state {{
            background: var(--card-bg);
            border: 1px dashed var(--border-color);
            border-radius: 8px;
            padding: 1.5rem;
            color: var(--text-muted);
            font-size: 0.9rem;
            text-align: center;
        }}

        /* FOOTER */
        footer {{
            text-align: center;
            font-size: 0.825rem;
            color: var(--text-muted);
            margin-top: 3rem;
            border-top: 1px solid var(--border-color);
            padding-top: 1.5rem;
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
                <div class="tile">
                    <div class="tile-val">{summary.get('needs_review_functions', 0)}</div>
                    <div class="tile-lbl">Needs Review ({summary.get('needs_review_lines', 0)} lines)</div>
                </div>
                <div class="tile">
                    <div class="tile-val">{summary.get('safe_to_skip_lines', 0)}</div>
                    <div class="tile-lbl">Total Safe-to-Skip Lines</div>
                </div>
            </div>

            <p class="hero-sub">
                Analyzed <strong>{html.escape(repo_name)}</strong> — {meta.get('files_analyzed', 0)} files, {meta.get('total_functions', 0)} functions, {meta.get('total_lines', 0)} lines.
                Entry points: <code>{html.escape(entry_points_str)}</code>.
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
                        <th onclick="sortTable(0, 'number')">Priority <span class="sort-icon">▼</span></th>
                        <th onclick="sortTable(1, 'string')">Type <span class="sort-icon">↕</span></th>
                        <th onclick="sortTable(2, 'string')">Symbol <span class="sort-icon">↕</span></th>
                        <th onclick="sortTable(3, 'string')">File:Lines <span class="sort-icon">↕</span></th>
                        <th onclick="sortTable(4, 'number')">LOC <span class="sort-icon">↕</span></th>
                        <th onclick="sortTable(5, 'string')">Confidence <span class="sort-icon">↕</span></th>
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
                    <tr class="data-row" onclick="toggleDetail('{f_id}')">
                        <td><strong>{priority}</strong></td>
                        <td>{type_badge}</td>
                        <td class="code-sym">{html.escape(f_sym)}</td>
                        <td class="code-file">{html.escape(loc_str)}</td>
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

        <!-- NEEDS REVIEW SECTION -->
        <h2>Needs Review</h2>
"""

    if low_conf_findings:
        html_content += """
        <div class="table-card">
            <table>
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Symbol</th>
                        <th>File:Lines</th>
                        <th>Reason / Caveats</th>
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
                    <tr>
                        <td><strong>{html.escape(f_id)}</strong></td>
                        <td class="code-sym">{html.escape(f_sym)}</td>
                        <td class="code-file">{html.escape(loc_str)}</td>
                        <td>{html.escape(reason)} {html.escape(caveats)}</td>
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

    <!-- INLINE JS FOR SORTING AND DETAILS -->
    <script>
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
                const detailId = row.getAttribute('onclick').match(/'([^']+)'/)[1];
                const detailRow = document.getElementById('detail-' + detailId);
                tbody.appendChild(row);
                if (detailRow) {{
                    tbody.appendChild(detailRow);
                }}
            }});
        }}
    </script>
</body>
</html>
"""

    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)
