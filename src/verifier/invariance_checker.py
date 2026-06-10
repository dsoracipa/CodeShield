"""Verificacion de invariancia semantica: compara el comportamiento del
codigo original versus el codigo ofuscado ejecutando ambos con subprocess.
"""

import difflib
import os
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class VerificationResult:
    passed: bool
    original_stdout: str
    obfuscated_stdout: str
    original_returncode: int
    obfuscated_returncode: int
    original_stderr: str
    obfuscated_stderr: str
    execution_time_original: float
    execution_time_obfuscated: float
    diff_lines: list
    error_message: Optional[str]
    skipped: bool = False
    skip_reason: Optional[str] = None


class InvarianceChecker:
    """Ejecuta original y ofuscado, compara stdout y returncode."""

    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def verify(self,
               original_path: Path,
               obfuscated_path: Path,
               args=None,
               stdin_data: Optional[str] = None) -> VerificationResult:
        """Ejecuta ambos archivos y compara sus salidas."""
        _args = args or []

        try:
            orig = self._execute(original_path, _args, stdin_data)
        except Exception as e:
            return VerificationResult(
                passed=False, skipped=False,
                original_stdout='', obfuscated_stdout='',
                original_returncode=-1, obfuscated_returncode=-1,
                original_stderr='', obfuscated_stderr='',
                execution_time_original=0.0, execution_time_obfuscated=0.0,
                diff_lines=[], error_message=str(e),
            )

        if orig is None:
            return VerificationResult(
                passed=False, skipped=True,
                skip_reason=f"timeout despues de {self.timeout}s (original)",
                original_stdout='', obfuscated_stdout='',
                original_returncode=-1, obfuscated_returncode=-1,
                original_stderr='', obfuscated_stderr='',
                execution_time_original=self.timeout, execution_time_obfuscated=0.0,
                diff_lines=[], error_message=None,
            )

        orig_stdout, orig_stderr, orig_rc, orig_time = orig

        if 'EOFError' in orig_stderr and stdin_data is None:
            return VerificationResult(
                passed=False, skipped=True,
                skip_reason="script requiere input interactivo -- usar --verify-stdin",
                original_stdout=orig_stdout, obfuscated_stdout='',
                original_returncode=orig_rc, obfuscated_returncode=-1,
                original_stderr=orig_stderr, obfuscated_stderr='',
                execution_time_original=orig_time, execution_time_obfuscated=0.0,
                diff_lines=[], error_message=None,
            )

        try:
            obf = self._execute(obfuscated_path, _args, stdin_data)
        except Exception as e:
            return VerificationResult(
                passed=False, skipped=False,
                original_stdout=orig_stdout, obfuscated_stdout='',
                original_returncode=orig_rc, obfuscated_returncode=-1,
                original_stderr=orig_stderr, obfuscated_stderr='',
                execution_time_original=orig_time, execution_time_obfuscated=0.0,
                diff_lines=[], error_message=str(e),
            )

        if obf is None:
            return VerificationResult(
                passed=False, skipped=True,
                skip_reason=f"timeout despues de {self.timeout}s (ofuscado)",
                original_stdout=orig_stdout, obfuscated_stdout='',
                original_returncode=orig_rc, obfuscated_returncode=-1,
                original_stderr=orig_stderr, obfuscated_stderr='',
                execution_time_original=orig_time, execution_time_obfuscated=self.timeout,
                diff_lines=[], error_message=None,
            )

        obf_stdout, obf_stderr, obf_rc, obf_time = obf

        if 'EOFError' in obf_stderr and stdin_data is None:
            return VerificationResult(
                passed=False, skipped=True,
                skip_reason="script requiere input interactivo -- usar --verify-stdin",
                original_stdout=orig_stdout, obfuscated_stdout=obf_stdout,
                original_returncode=orig_rc, obfuscated_returncode=obf_rc,
                original_stderr=orig_stderr, obfuscated_stderr=obf_stderr,
                execution_time_original=orig_time, execution_time_obfuscated=obf_time,
                diff_lines=[], error_message=None,
            )

        passed = (orig_stdout == obf_stdout) and (orig_rc == obf_rc)
        diff_lines: list = []
        if not passed:
            diff_lines = list(difflib.unified_diff(
                orig_stdout.splitlines(keepends=True),
                obf_stdout.splitlines(keepends=True),
                fromfile='original',
                tofile='ofuscado',
            ))

        return VerificationResult(
            passed=passed,
            original_stdout=orig_stdout,
            obfuscated_stdout=obf_stdout,
            original_returncode=orig_rc,
            obfuscated_returncode=obf_rc,
            original_stderr=orig_stderr,
            obfuscated_stderr=obf_stderr,
            execution_time_original=orig_time,
            execution_time_obfuscated=obf_time,
            diff_lines=diff_lines,
            error_message=None,
        )

    def _execute(self, path: Path, args: list, stdin_data: Optional[str]):
        """Ejecuta un script. Retorna (stdout, stderr, rc, time) o None si timeout."""
        cmd = [sys.executable, str(path)] + args
        stdin_bytes = stdin_data.encode('utf-8') if stdin_data else None
        start = time.perf_counter()
        try:
            proc = subprocess.run(
                cmd,
                input=stdin_bytes,
                capture_output=True,
                timeout=self.timeout,
            )
            elapsed = time.perf_counter() - start
            return (
                proc.stdout.decode('utf-8', errors='replace'),
                proc.stderr.decode('utf-8', errors='replace'),
                proc.returncode,
                elapsed,
            )
        except subprocess.TimeoutExpired:
            return None


def format_result(result: VerificationResult) -> str:
    """Retorna un string formateado para imprimir en terminal."""
    try:
        from colorama import Fore, Style
        GREEN = Fore.GREEN
        RED = Fore.RED
        RESET = Style.RESET_ALL
        BOLD = Style.BRIGHT
        DIM = Style.DIM
    except ImportError:
        GREEN = RED = RESET = BOLD = DIM = ''

    sep = '-' * 55
    parts = ['', 'Verificacion de invariancia', sep]

    if result.skipped:
        parts.append(f'  {DIM}Estado:     omitido{RESET}')
        parts.append(f'  {DIM}Razon:      {result.skip_reason}{RESET}')
    elif result.error_message:
        parts.append(f'  Resultado:  {RED}{BOLD}[ERROR]{RESET}  {result.error_message}')
    else:
        parts.append(
            f'  Original:   {result.execution_time_original:.3f}s'
            f'  ->  returncode {result.original_returncode}'
        )
        parts.append(
            f'  Ofuscado:   {result.execution_time_obfuscated:.3f}s'
            f'  ->  returncode {result.obfuscated_returncode}'
        )
        if result.passed:
            parts.append(f'  Resultado:  {GREEN}{BOLD}[OK] INVARIANTE{RESET}  (stdout identico)')
        else:
            diff_count = len([
                ln for ln in result.diff_lines
                if ln.startswith(('+', '-')) and not ln.startswith(('+++', '---'))
            ])
            parts.append(
                f'  Resultado:  {RED}{BOLD}[FALLA]{RESET}'
                f'  (stdout difiere en {diff_count} lineas)'
            )
            if result.diff_lines:
                parts.append('')
                parts.append('  Diferencias:')
                for line in result.diff_lines[:20]:
                    line = line.rstrip('\n')
                    if line.startswith('+') and not line.startswith('+++'):
                        parts.append(f'  {GREEN}{line}{RESET}')
                    elif line.startswith('-') and not line.startswith('---'):
                        parts.append(f'  {RED}{line}{RESET}')
                    else:
                        parts.append(f'  {line}')

    parts.append(sep)
    return '\n'.join(parts)
