"""Genera una comparativa HTML estatica entre el codigo original y el ofuscado.

Usa highlight.js via CDN para syntax highlighting. No requiere servidor: el
HTML se abre directamente en cualquier navegador.
"""

import html
import json
from pathlib import Path

from src.stats.obfuscation_stats import ObfuscationStats


TEMPLATE = '''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>CodeShield - Comparativa de {filename}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    background: #1a1a1a;
    color: #ddd;
    padding: 24px;
    min-height: 100vh;
}}
.header {{ margin-bottom: 24px; }}
h1 {{
    font-size: 28px;
    color: #fff;
    margin-bottom: 4px;
    font-weight: 600;
}}
.subtitle {{ color: #888; font-size: 14px; }}
.stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
}}
.stat-card {{
    background: #2a2a2a;
    padding: 16px 20px;
    border-radius: 8px;
    border-left: 3px solid #4a9eff;
}}
.stat-card.alt {{ border-left-color: #ff7a59; }}
.stat-card.alt2 {{ border-left-color: #9bff7a; }}
.stat-card.alt3 {{ border-left-color: #d97aff; }}
.stat-label {{
    font-size: 11px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}}
.stat-value {{
    font-size: 28px;
    font-weight: 600;
    color: #fff;
}}
.comparison {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 32px;
}}
.panel {{
    background: #282c34;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #333;
}}
.panel-header {{
    background: #1e1e1e;
    padding: 12px 16px;
    font-weight: 500;
    border-bottom: 1px solid #333;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.panel-header .label {{ font-size: 13px; }}
.panel-header .badge {{
    font-size: 11px;
    background: #333;
    padding: 2px 8px;
    border-radius: 10px;
    color: #aaa;
}}
.panel-content {{
    max-height: 600px;
    overflow: auto;
}}
.panel-content pre {{ margin: 0; }}
.panel-content code {{
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 13px;
    line-height: 1.6;
}}
.symbol-table {{
    background: #2a2a2a;
    padding: 20px;
    border-radius: 8px;
    margin-top: 16px;
}}
.symbol-table h3 {{
    color: #fff;
    margin-bottom: 12px;
    font-weight: 500;
    font-size: 16px;
}}
table {{ width: 100%; border-collapse: collapse; }}
th, td {{
    text-align: left;
    padding: 10px 14px;
    border-bottom: 1px solid #333;
    font-size: 13px;
}}
th {{
    background: #1e1e1e;
    color: #aaa;
    font-weight: 500;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
}}
td.original {{ color: #6ab7ff; font-family: monospace; }}
td.obfuscated {{ color: #ff9a6a; font-family: monospace; }}
td.kind {{ color: #aaa; font-size: 11px; text-transform: uppercase; }}
.footer {{
    margin-top: 32px;
    text-align: center;
    color: #555;
    font-size: 12px;
}}
@media (max-width: 900px) {{
    .comparison {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="header">
  <h1>CodeShield - Comparativa</h1>
  <p class="subtitle">{filename}</p>
</div>

<div class="stats">
  <div class="stat-card">
    <div class="stat-label">Identificadores renombrados</div>
    <div class="stat-value">{renamed}</div>
  </div>
  <div class="stat-card alt">
    <div class="stat-label">Strings cifrados</div>
    <div class="stat-value">{ciphered}</div>
  </div>
  <div class="stat-card alt2">
    <div class="stat-label">Comentarios eliminados</div>
    <div class="stat-value">{comments}</div>
  </div>
  <div class="stat-card alt3">
    <div class="stat-label">Docstrings eliminados</div>
    <div class="stat-value">{docstrings}</div>
  </div>
</div>

<div class="comparison">
  <div class="panel">
    <div class="panel-header">
      <span class="label">Codigo original</span>
      <span class="badge">{lines_original} lineas</span>
    </div>
    <div class="panel-content"><pre><code class="language-python">{original_code}</code></pre></div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <span class="label">Codigo ofuscado</span>
      <span class="badge">{lines_obfuscated} lineas</span>
    </div>
    <div class="panel-content"><pre><code class="language-python">{obfuscated_code}</code></pre></div>
  </div>
</div>

<div class="symbol-table">
  <h3>Mapa de simbolos ({symbols_total})</h3>
  <table>
    <thead><tr><th>Original</th><th>Ofuscado</th><th>Tipo</th></tr></thead>
    <tbody>
      {symbol_rows}
    </tbody>
  </table>
</div>

<div class="footer">Generado por CodeShield - Universidad Nacional de Colombia</div>

<script>hljs.highlightAll();</script>
</body>
</html>
'''


def generate_comparison_html(original_path: Path,
                              obfuscated_path: Path,
                              map_path: Path,
                              output_path: Path,
                              stats: ObfuscationStats) -> None:
    """Genera el archivo HTML de comparativa lado a lado."""
    original = original_path.read_text(encoding='utf-8')
    obfuscated = obfuscated_path.read_text(encoding='utf-8')
    symbol_data = json.loads(map_path.read_text(encoding='utf-8'))

    rows = []
    for s in symbol_data.get('symbols', []):
        rows.append(
            f'<tr>'
            f'<td class="original">{html.escape(s["original"])}</td>'
            f'<td class="obfuscated">{html.escape(s["obfuscated"])}</td>'
            f'<td class="kind">{s["kind"]}</td>'
            f'</tr>'
        )

    rendered = TEMPLATE.format(
        filename=html.escape(original_path.name),
        renamed=stats.identifiers_renamed,
        ciphered=stats.strings_ciphered,
        comments=stats.comments_removed,
        docstrings=stats.docstrings_removed,
        lines_original=stats.lines_original,
        lines_obfuscated=stats.lines_obfuscated,
        symbols_total=stats.symbols_total,
        original_code=html.escape(original),
        obfuscated_code=html.escape(obfuscated),
        symbol_rows='\n      '.join(rows) if rows else '<tr><td colspan="3" style="color:#666;">(sin simbolos)</td></tr>',
    )

    output_path.write_text(rendered, encoding='utf-8')
