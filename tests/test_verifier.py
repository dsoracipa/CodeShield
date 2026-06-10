"""Tests para InvarianceChecker."""

import os
import sys
import tempfile
from pathlib import Path

import pytest

from src.verifier.invariance_checker import InvarianceChecker, VerificationResult
from src.obfuscator import Obfuscator, ObfuscatorConfig


def _write_tmp(code: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(suffix='.py', delete=False,
                                      mode='w', encoding='utf-8')
    tmp.write(code)
    tmp.flush()
    tmp.close()
    return Path(tmp.name)


def test_simple_invariance_passes():
    """Un script simple debe verificar correctamente despues de ofuscar."""
    original_code = (
        "def calcular(x):\n"
        "    return x * 2\n"
        "\n"
        "print(calcular(7))\n"
    )
    original_path = _write_tmp(original_code)
    try:
        obf = Obfuscator(ObfuscatorConfig())
        obfuscated_code, _, _ = obf.obfuscate_source(original_code)
        obfuscated_path = _write_tmp(obfuscated_code)
        try:
            checker = InvarianceChecker(timeout=10.0)
            result = checker.verify(original_path, obfuscated_path)
            assert result.passed, (
                f"Se esperaba invarianza. stdout original: {repr(result.original_stdout)}, "
                f"stdout ofuscado: {repr(result.obfuscated_stdout)}, "
                f"stderr: {repr(result.obfuscated_stderr)}"
            )
            assert not result.skipped
        finally:
            try:
                os.unlink(obfuscated_path)
            except OSError:
                pass
    finally:
        try:
            os.unlink(original_path)
        except OSError:
            pass


def test_invariance_fails_on_broken_obfuscation():
    """Si el ofuscado produce stdout diferente, el verificador debe detectarlo."""
    original_code = "print('hola')\n"
    broken_code = "print('adios')\n"
    original_path = _write_tmp(original_code)
    broken_path = _write_tmp(broken_code)
    try:
        checker = InvarianceChecker(timeout=10.0)
        result = checker.verify(original_path, broken_path)
        assert not result.passed
        assert not result.skipped
        assert len(result.diff_lines) > 0
    finally:
        try:
            os.unlink(original_path)
        except OSError:
            pass
        try:
            os.unlink(broken_path)
        except OSError:
            pass


def test_timeout_returns_skipped():
    """Un script con bucle infinito debe retornar skipped, no colgarse."""
    infinite_code = "while True: pass\n"
    simple_code = "print('ok')\n"
    infinite_path = _write_tmp(infinite_code)
    simple_path = _write_tmp(simple_code)
    try:
        checker = InvarianceChecker(timeout=2.0)
        result = checker.verify(simple_path, infinite_path)
        assert result.skipped
        assert result.skip_reason is not None
        assert 'timeout' in result.skip_reason.lower()
    finally:
        try:
            os.unlink(infinite_path)
        except OSError:
            pass
        try:
            os.unlink(simple_path)
        except OSError:
            pass


def test_stdin_data_passthrough():
    """Un script que usa input() debe funcionar si se pasa stdin_data."""
    script_code = "nombre = input()\nprint(f'Hola {nombre}')\n"
    script_path = _write_tmp(script_code)
    try:
        obf = Obfuscator(ObfuscatorConfig())
        obfuscated_code, _, _ = obf.obfuscate_source(script_code)
        obfuscated_path = _write_tmp(obfuscated_code)
        try:
            checker = InvarianceChecker(timeout=10.0)
            result = checker.verify(script_path, obfuscated_path, stdin_data='Mundo\n')
            assert result.passed or result.skipped, (
                f"Esperaba passed o skipped. stdout orig: {repr(result.original_stdout)}, "
                f"stdout obf: {repr(result.obfuscated_stdout)}"
            )
        finally:
            try:
                os.unlink(obfuscated_path)
            except OSError:
                pass
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass
