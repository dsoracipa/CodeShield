"""CLI entry point de CodeShield.

Subcomandos:
  obfuscate   Ofuscar un archivo Python.
  deobfuscate Restaurar un archivo ofuscado usando su symbol_map.json.

Ejemplos:
  python -m src.main obfuscate examples/input/01_simple.py
  python -m src.main obfuscate examples/input/01_simple.py --html
  python -m src.main deobfuscate examples/input/01_simple_obfuscated.py \\
                  -m examples/input/01_simple_symbol_map.json
"""

import argparse
import json
import sys
from pathlib import Path

try:
    from colorama import init as _colorama_init
    _colorama_init()
except ImportError:
    pass

from src.obfuscator import Obfuscator, ObfuscatorConfig
from src.deobfuscator import Deobfuscator
from src.viewer.html_viewer import generate_comparison_html
from src.verifier.invariance_checker import InvarianceChecker, format_result


def cmd_obfuscate(args: argparse.Namespace) -> int:
    inp = Path(args.input)
    if not inp.exists():
        print(f"ERROR: archivo no encontrado: {inp}", file=sys.stderr)
        return 1
    if inp.suffix != '.py':
        print("ADVERTENCIA: el archivo no tiene extension .py", file=sys.stderr)

    output = Path(args.output) if args.output else inp.with_name(inp.stem + '_obfuscated.py')
    map_path = Path(args.map) if args.map else inp.with_name(inp.stem + '_symbol_map.json')

    config = ObfuscatorConfig(
        rename=not args.no_rename,
        remove_comments=not args.no_remove_comments,
        cipher_strings=not args.no_cipher_strings,
        dead_code=args.dead_code,
        dead_code_density=args.dead_code_density,
        dead_code_seed=args.dead_code_seed,
    )

    obf = Obfuscator(config)
    try:
        stats = obf.obfuscate_file(inp, output, map_path)
    except SyntaxError as e:
        print(f"ERROR al ofuscar: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"ERROR al ofuscar: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    print(f"OK Codigo ofuscado:  {output}")
    print(f"OK Mapa de simbolos: {map_path}")
    print()
    print("Estadisticas:")
    print(f"  Lineas:                  {stats.lines_original} -> {stats.lines_obfuscated}")
    print(f"  Identificadores:         {stats.identifiers_renamed} renombrados")
    print(f"  Simbolos en tabla:       {stats.symbols_total}")
    print(f"  Comentarios eliminados:  {stats.comments_removed}")
    print(f"  Docstrings eliminados:   {stats.docstrings_removed}")
    print(f"  Strings cifrados:        {stats.strings_ciphered}")
    if config.dead_code:
        print(f"  Dead code insertado:     {stats.dead_code_inserted}")

    if args.verbose:
        print()
        print("Tabla de simbolos:")
        data = json.loads(map_path.read_text(encoding='utf-8'))
        for s in data.get('symbols', []):
            print(f"  {s['original']:30} -> {s['obfuscated']:10} [{s['kind']}]")

    verification_result = None
    if args.verify:
        checker = InvarianceChecker(timeout=args.verify_timeout)
        verify_args = args.verify_args.split() if args.verify_args else None
        verification_result = checker.verify(
            inp, output,
            args=verify_args,
            stdin_data=args.verify_stdin,
        )
        print(format_result(verification_result))
        if not verification_result.passed and not verification_result.skipped:
            try:
                from colorama import Fore, Style
                print(f"{Fore.YELLOW}ADVERTENCIA: la ofuscacion puede haber alterado el comportamiento del programa.{Style.RESET_ALL}")
            except ImportError:
                print("ADVERTENCIA: la ofuscacion puede haber alterado el comportamiento del programa.")

    if args.html:
        html_path = Path(args.html_output) if args.html_output else inp.with_name(inp.stem + '_comparison.html')
        generate_comparison_html(inp, output, map_path, html_path, stats, verification_result=verification_result)
        print(f"OK Comparativa HTML: {html_path}")

    return 0


def cmd_deobfuscate(args: argparse.Namespace) -> int:
    inp = Path(args.input)
    map_path = Path(args.map)
    if not inp.exists():
        print(f"ERROR: archivo no encontrado: {inp}", file=sys.stderr)
        return 1
    if not map_path.exists():
        print(f"ERROR: symbol_map.json no encontrado: {map_path}", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else inp.with_name(inp.stem + '_restored.py')

    try:
        deobf = Deobfuscator(map_path)
        deobf.deobfuscate_file(inp, output)
    except Exception as e:
        print(f"ERROR al deofuscar: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    print(f"OK Codigo restaurado: {output}")
    if args.verbose:
        n = len(deobf.table.all_symbols())
        print(f"   {n} simbolos restaurados desde el mapa")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='codeshield',
        description='Ofuscador y deofuscador de codigo fuente Python.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    p_obf = subparsers.add_parser('obfuscate', help='Ofuscar un archivo Python.')
    p_obf.add_argument('input', help='Archivo .py de entrada')
    p_obf.add_argument('-o', '--output', help='Archivo de salida')
    p_obf.add_argument('-m', '--map', help='Ruta de symbol_map.json')
    p_obf.add_argument('--no-rename', action='store_true', help='Desactivar renombrado')
    p_obf.add_argument('--no-remove-comments', action='store_true', help='Desactivar eliminacion de comentarios')
    p_obf.add_argument('--no-cipher-strings', action='store_true', help='Desactivar cifrado de strings')
    p_obf.add_argument('--dead-code', action='store_true', help='Activar dead code')
    p_obf.add_argument('--dead-code-density', type=float, default=0.3, help='Densidad de dead code (0.0-1.0)')
    p_obf.add_argument('--dead-code-seed', type=int, default=None, help='Seed para reproducibilidad')
    p_obf.add_argument('--html', action='store_true', help='Generar comparativa HTML')
    p_obf.add_argument('--html-output', default=None, help='Ruta del HTML')
    p_obf.add_argument('--verify', action='store_true', help='Verificar invariancia semantica despues de ofuscar')
    p_obf.add_argument('--verify-timeout', type=float, default=10.0, help='Timeout en segundos para la verificacion (default: 10.0)')
    p_obf.add_argument('--verify-args', default=None, help='Argumentos a pasar al script durante verificacion')
    p_obf.add_argument('--verify-stdin', default=None, help='Texto a pasar como stdin durante verificacion')
    p_obf.add_argument('-v', '--verbose', action='store_true')
    p_obf.set_defaults(func=cmd_obfuscate)

    p_de = subparsers.add_parser('deobfuscate', help='Deofuscar un archivo Python.')
    p_de.add_argument('input', help='Archivo ofuscado de entrada')
    p_de.add_argument('-m', '--map', required=True, help='symbol_map.json correspondiente')
    p_de.add_argument('-o', '--output', help='Archivo de salida restaurado')
    p_de.add_argument('-v', '--verbose', action='store_true')
    p_de.set_defaults(func=cmd_deobfuscate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
