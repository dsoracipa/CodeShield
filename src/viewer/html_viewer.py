"""Genera una comparativa HTML estatica entre el codigo original y el ofuscado.

Usa highlight.js via CDN para syntax highlighting. No requiere servidor: el
HTML se abre directamente en cualquier navegador.
"""

import html
import json
from pathlib import Path
from typing import Optional

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
.verification-banner {{
    padding: 14px 20px;
    border-radius: 8px;
    margin-bottom: 24px;
    font-size: 14px;
    font-family: Consolas, "Courier New", monospace;
    display: flex;
    align-items: center;
    gap: 10px;
}}
.verification-banner.pass {{ background: #1a3a1a; border: 1px solid #2d6a2d; color: #9bff7a; }}
.verification-banner.fail {{ background: #3a1a1a; border: 1px solid #6a2d2d; color: #ff7a7a; }}
.verification-banner.skip {{ background: #2a2a2a; border: 1px solid #444; color: #8b949e; }}
.diff-block {{
    margin-top: 10px;
    background: #0d1117;
    padding: 10px;
    border-radius: 6px;
    font-size: 12px;
    white-space: pre;
    overflow-x: auto;
}}
.diff-add {{ color: #9bff7a; }}
.diff-rem {{ color: #ff7a7a; }}
details summary {{ cursor: pointer; user-select: none; }}
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

{verification_banner}

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


def _build_verification_banner(vr) -> str:
    if vr is None:
        return ''
    if vr.skipped:
        reason = html.escape(vr.skip_reason or '')
        return f'<div class="verification-banner skip">&#8212; Verificacion omitida: {reason}</div>'
    if vr.passed:
        t_orig = f'{vr.execution_time_original:.3f}s'
        t_obf = f'{vr.execution_time_obfuscated:.3f}s'
        return (
            f'<div class="verification-banner pass">'
            f'&#10003; Comportamiento verificado &mdash; stdout identico'
            f' &nbsp;|&nbsp; original: {t_orig} &nbsp; ofuscado: {t_obf}'
            f'</div>'
        )
    diff_lines = vr.diff_lines or []
    diff_count = len([l for l in diff_lines if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))])
    diff_html_parts = []
    for line in diff_lines[:40]:
        line = line.rstrip('\n')
        escaped = html.escape(line)
        if line.startswith('+') and not line.startswith('+++'):
            diff_html_parts.append(f'<span class="diff-add">{escaped}</span>')
        elif line.startswith('-') and not line.startswith('---'):
            diff_html_parts.append(f'<span class="diff-rem">{escaped}</span>')
        else:
            diff_html_parts.append(escaped)
    diff_block = '\n'.join(diff_html_parts)
    return (
        f'<div class="verification-banner fail">'
        f'<details>'
        f'<summary>&#10007; Verificacion fallida &mdash; stdout difiere en {diff_count} lineas (click para ver diff)</summary>'
        f'<div class="diff-block">{diff_block}</div>'
        f'</details>'
        f'</div>'
    )


def generate_comparison_html(original_path: Path,
                              obfuscated_path: Path,
                              map_path: Path,
                              output_path: Path,
                              stats: ObfuscationStats,
                              verification_result=None) -> None:
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
        verification_banner=_build_verification_banner(verification_result),
    )

    output_path.write_text(rendered, encoding='utf-8')
