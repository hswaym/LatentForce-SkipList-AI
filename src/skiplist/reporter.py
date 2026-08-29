import json
from pathlib import Path
from typing import Dict, Any


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SkipList Analysis Report</title>
    <style>
        :root {
            --bg: #0f172a;
            --card-bg: #1e293b;
            --text: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --warning: #f59e0b;
            --danger: #ef4444;
            --border: #334155;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 2rem;
            line-height: 1.5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        header {
            margin-bottom: 2rem;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1rem;
        }
        h1 {
            color: var(--accent);
            margin: 0 0 0.5rem 0;
        }
        .subtitle {
            color: var(--text-muted);
            margin: 0;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }
        .stat-card {
            background-color: var(--card-bg);
            padding: 1.25rem;
            border-radius: 8px;
            border: 1px solid var(--border);
        }
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: var(--accent);
        }
        .stat-value.warning { color: var(--warning); }
        .stat-value.danger { color: var(--danger); }
        .stat-label {
            color: var(--text-muted);
            font-size: 0.875rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        section {
            background-color: var(--card-bg);
            border-radius: 8px;
            border: 1px solid var(--border);
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        h2 {
            margin-top: 0;
            border-bottom: 1px solid var(--border);
            padding-bottom: 0.5rem;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 1rem;
        }
        th, td {
            text-align: left;
            padding: 0.75rem;
            border-bottom: 1px solid var(--border);
        }
        th {
            color: var(--text-muted);
            font-weight: 600;
        }
        .badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: bold;
            text-transform: uppercase;
        }
        .badge-dead { background-color: rgba(239, 68, 68, 0.2); color: var(--danger); }
        .badge-dup { background-color: rgba(245, 158, 11, 0.2); color: var(--warning); }
        pre {
            background: #090d16;
            padding: 1rem;
            border-radius: 4px;
            overflow-x: auto;
            color: #e2e8f0;
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>SkipList Triage Report</h1>
            <p class="subtitle">Target Directory: {{ summary.target_directory }}</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{{ summary.total_files }}</div>
                <div class="stat-label">Total Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{{ summary.total_lines }}</div>
                <div class="stat-label">Lines of Code</div>
            </div>
            <div class="stat-card">
                <div class="stat-value danger">{{ summary.dead_functions_count + summary.dead_classes_count }}</div>
                <div class="stat-label">Dead Code Symbols</div>
            </div>
            <div class="stat-card">
                <div class="stat-value warning">{{ summary.duplicate_blocks_count }}</div>
                <div class="stat-label">Duplicate Code Blocks</div>
            </div>
        </div>

        <section>
            <h2>Unused / Dead Code Findings</h2>
            {% if dead_code.functions or dead_code.classes %}
            <table>
                <thead>
                    <tr>
                        <th>Type</th>
                        <th>Symbol Name</th>
                        <th>File Location</th>
                        <th>Line Number</th>
                    </tr>
                </thead>
                <tbody>
                    {% for fn in dead_code.functions %}
                    <tr>
                        <td><span class="badge badge-dead">Function</span></td>
                        <td><code>{{ fn.name }}</code></td>
                        <td>{{ fn.file }}</td>
                        <td>{{ fn.line }}</td>
                    </tr>
                    {% endfor %}
                    {% for cls in dead_code.classes %}
                    <tr>
                        <td><span class="badge badge-dead">Class</span></td>
                        <td><code>{{ cls.name }}</code></td>
                        <td>{{ cls.file }}</td>
                        <td>{{ cls.line }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
            {% else %}
            <p>No dead code symbols detected!</p>
            {% endif %}
        </section>

        <section>
            <h2>Duplicate Code Findings</h2>
            {% if duplicates %}
            {% for dup in duplicates %}
            <div style="margin-bottom: 1.5rem;">
                <h3><span class="badge badge-dup">Duplicate Block</span> Found in {{ dup.count }} locations</h3>
                <ul>
                    {% for inst in dup.instances %}
                    <li><code>{{ inst.file }}:{{ inst.line }}</code> (Function: <code>{{ inst.name }}</code>)</li>
                    {% endfor %}
                </ul>
                <pre><code>{{ dup.instances[0].code_snippet }}</code></pre>
            </div>
            {% endfor %}
            {% else %}
            <p>No duplicate code blocks detected!</p>
            {% endif %}
        </section>
    </div>
</body>
</html>
"""


def export_json(data: Dict[str, Any], output_path: str):
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def export_html(data: Dict[str, Any], output_path: str):
    try:
        from jinja2 import Template
        template = Template(HTML_TEMPLATE)
        html_content = template.render(**data)
    except ImportError:
        # Fallback basic string formatting if jinja2 is not available
        html_content = f"<html><body><h1>SkipList Summary</h1><pre>{json.dumps(data['summary'], indent=2)}</pre></body></html>"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
