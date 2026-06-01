"""Tests de invariancia: el codigo ofuscado debe ejecutar identico al original."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / 'examples' / 'input'
PROJECT_ROOT = Path(__file__).parent.parent


def run_python_file(path: Path) -> tuple[str, int]:
    """Ejecuta un archivo Python y devuelve (stdout, exit_code)."""
    result = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(PROJECT_ROOT),
    )
    return result.stdout, result.returncode


@pytest.mark.parametrize("example_name", [
    "01_simple.py",
    "02_classes.py",
    "03_realistic.py",
    "04_advanced.py",
])
def test_obfuscation_preserves_behavior(example_name: str) -> None:
    original = EXAMPLES_DIR / example_name
    assert original.exists(), f"Falta el archivo de ejemplo: {original}"

    expected_stdout, expected_code = run_python_file(original)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        obf = tmp_path / 'obfuscated.py'
        smap = tmp_path / 'map.json'

        result = subprocess.run([
            sys.executable, '-m', 'src.main', 'obfuscate',
            str(original),
            '-o', str(obf),
            '-m', str(smap),
        ], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        assert result.returncode == 0, f"Ofuscacion fallo: {result.stderr}"

        actual_stdout, actual_code = run_python_file(obf)
        assert actual_code == expected_code, f"Exit codes differ for {example_name}"
        assert actual_stdout == expected_stdout, (
            f"Outputs differ for {example_name}\n"
            f"Expected: {expected_stdout!r}\nActual: {actual_stdout!r}"
        )


@pytest.mark.parametrize("example_name", [
    "01_simple.py",
    "02_classes.py",
    "03_realistic.py",
    "04_advanced.py",
])
def test_round_trip(example_name: str) -> None:
    """Ofuscar y luego deofuscar produce codigo ejecutable equivalente."""
    original = EXAMPLES_DIR / example_name
    expected_stdout, _ = run_python_file(original)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        obf = tmp_path / 'obfuscated.py'
        smap = tmp_path / 'map.json'
        restored = tmp_path / 'restored.py'

        subprocess.run([
            sys.executable, '-m', 'src.main', 'obfuscate',
            str(original), '-o', str(obf), '-m', str(smap),
        ], check=True, capture_output=True, cwd=str(PROJECT_ROOT))

        subprocess.run([
            sys.executable, '-m', 'src.main', 'deobfuscate',
            str(obf), '-m', str(smap), '-o', str(restored),
        ], check=True, capture_output=True, cwd=str(PROJECT_ROOT))

        restored_stdout, _ = run_python_file(restored)
        assert restored_stdout == expected_stdout


def test_dead_code_preserves_behavior() -> None:
    """Dead code activado: el codigo debe seguir ejecutando igual."""
    original = EXAMPLES_DIR / "01_simple.py"
    expected_stdout, _ = run_python_file(original)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        obf = tmp_path / 'obfuscated.py'
        smap = tmp_path / 'map.json'

        result = subprocess.run([
            sys.executable, '-m', 'src.main', 'obfuscate',
            str(original),
            '-o', str(obf), '-m', str(smap),
            '--dead-code', '--dead-code-density', '0.8',
            '--dead-code-seed', '42',
        ], capture_output=True, text=True, cwd=str(PROJECT_ROOT))
        assert result.returncode == 0, result.stderr

        actual_stdout, _ = run_python_file(obf)
        assert actual_stdout == expected_stdout
