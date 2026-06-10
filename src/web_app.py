"""Interfaz web de CodeShield.

Arranque:
    python -m src.web_app
    o doble click en web.bat

Rutas:
    GET  /              -> UI principal
    GET  /health        -> {"status": "ok", "version": "1.0"}
    POST /api/obfuscate -> ofuscar codigo
    POST /api/deobfuscate -> deofuscar codigo
"""

import os
import sys
import tempfile
from pathlib import Path

from flask import Flask, render_template, request, jsonify

from src.obfuscator import Obfuscator, ObfuscatorConfig
from src.deobfuscator import Deobfuscator
from src.verifier.invariance_checker import InvarianceChecker

app = Flask(__name__, template_folder='templates')


@app.get('/')
def index():
    return render_template('index.html')


@app.get('/health')
def health():
    return jsonify({"status": "ok", "version": "1.0"})


@app.post('/api/obfuscate')
def api_obfuscate():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    if not code or not code.strip():
        return jsonify({"success": False, "error": "El campo 'code' esta vacio."}), 400

    opts = data.get('options', {})
    config = ObfuscatorConfig(
        rename=opts.get('rename', True),
        remove_comments=opts.get('remove_comments', True),
        cipher_strings=opts.get('cipher_strings', True),
        dead_code=opts.get('dead_code', False),
        dead_code_density=float(opts.get('dead_code_density', 0.3)),
        dead_code_seed=opts.get('dead_code_seed', None),
    )

    do_verify = opts.get('verify', False)
    verify_timeout = float(opts.get('verify_timeout', 10.0))

    try:
        obf = Obfuscator(config)
        obfuscated_code, symbol_map_dict, stats = obf.obfuscate_source(code)
    except SyntaxError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"{type(e).__name__}: {e}"}), 500

    verification = None
    if do_verify:
        orig_tmp_name = None
        obf_tmp_name = None
        try:
            orig_fd, orig_tmp_name = tempfile.mkstemp(suffix='.py')
            with os.fdopen(orig_fd, 'w', encoding='utf-8') as f:
                f.write(code if code.endswith('\n') else code + '\n')

            obf_fd, obf_tmp_name = tempfile.mkstemp(suffix='.py')
            with os.fdopen(obf_fd, 'w', encoding='utf-8') as f:
                f.write(obfuscated_code if obfuscated_code.endswith('\n') else obfuscated_code + '\n')

            checker = InvarianceChecker(timeout=verify_timeout)
            vr = checker.verify(Path(orig_tmp_name), Path(obf_tmp_name))
            verification = {
                "ran": True,
                "passed": vr.passed,
                "skipped": vr.skipped,
                "skip_reason": vr.skip_reason,
                "execution_time_original": vr.execution_time_original,
                "execution_time_obfuscated": vr.execution_time_obfuscated,
                "diff_lines": vr.diff_lines,
                "error_message": vr.error_message,
            }
        finally:
            for tmp_name in (orig_tmp_name, obf_tmp_name):
                if tmp_name:
                    try:
                        os.unlink(tmp_name)
                    except OSError:
                        pass

    symbols_list = symbol_map_dict.get('symbols', [])
    return jsonify({
        "success": True,
        "obfuscated_code": obfuscated_code,
        "original_code": code,
        "symbol_map": symbol_map_dict,
        "stats": {
            "lines_original": stats.lines_original,
            "lines_obfuscated": stats.lines_obfuscated,
            "identifiers_renamed": stats.identifiers_renamed,
            "strings_ciphered": stats.strings_ciphered,
            "comments_removed": stats.comments_removed,
            "docstrings_removed": stats.docstrings_removed,
            "dead_code_inserted": stats.dead_code_inserted,
            "symbols_total": stats.symbols_total,
        },
        "verification": verification,
        "error": None,
    })


@app.post('/api/deobfuscate')
def api_deobfuscate():
    data = request.get_json(silent=True) or {}
    code = data.get('code', '')
    symbol_map = data.get('symbol_map', {})

    if not code or not code.strip():
        return jsonify({"success": False, "error": "El campo 'code' esta vacio."}), 400
    if not symbol_map:
        return jsonify({"success": False, "error": "El campo 'symbol_map' esta vacio."}), 400

    try:
        deobf = Deobfuscator.from_dict(symbol_map)
        restored = deobf.deobfuscate_source(code)
        return jsonify({"success": True, "restored_code": restored, "error": None})
    except Exception as e:
        return jsonify({"success": False, "error": f"{type(e).__name__}: {e}"}), 500


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
