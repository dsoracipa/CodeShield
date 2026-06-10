"""Pipeline inverso: ofuscado -> codigo legible.

Limitaciones documentadas:
- Los comentarios y docstrings eliminados NO se pueden recuperar.
- El dead code insertado permanece (no es distinguible de codigo real).
- El formato exacto (espaciado) puede diferir ligeramente del original.
"""

import base64
import json
import re
from pathlib import Path

from src.symbol_table import SymbolTable


_CIPHER_PATTERN = re.compile(
    r'__import__\(\s*"base64"\s*\)\.b64decode\(\s*"([A-Za-z0-9+/=]*)"\s*\)\.decode\(\s*"utf-8"\s*\)'
)


class Deobfuscator:
    """Revierte un archivo ofuscado al codigo original usando un symbol_map.json."""

    def __init__(self, symbol_map_path: Path):
        data = json.loads(symbol_map_path.read_text(encoding='utf-8'))
        self.table = SymbolTable.from_dict(data)
        self._reverse_map: dict[str, str] = {
            s.obfuscated: s.original for s in self.table.all_symbols()
        }

    @classmethod
    def from_dict(cls, symbol_map_dict: dict) -> 'Deobfuscator':
        """Construye una instancia directamente desde un dict (sin leer archivo)."""
        instance = object.__new__(cls)
        instance.table = SymbolTable.from_dict(symbol_map_dict)
        instance._reverse_map = {
            s.obfuscated: s.original for s in instance.table.all_symbols()
        }
        return instance

    def deobfuscate_source(self, source: str) -> str:
        source = self._restore_strings(source)
        source = self._restore_identifiers(source)
        return source

    def deobfuscate_file(self, input_path: Path, output_path: Path) -> None:
        source = input_path.read_text(encoding='utf-8')
        result = self.deobfuscate_source(source)
        output_path.write_text(result, encoding='utf-8')

    def _restore_strings(self, source: str) -> str:
        def replacer(match: re.Match) -> str:
            encoded = match.group(1)
            try:
                decoded = base64.b64decode(encoded).decode('utf-8') if encoded else ''
                return repr(decoded)
            except Exception:
                return match.group(0)
        return _CIPHER_PATTERN.sub(replacer, source)

    def _restore_identifiers(self, source: str) -> str:
        # Procesar en orden descendente de longitud para evitar reemplazos parciales.
        ordered = sorted(self._reverse_map.keys(), key=len, reverse=True)
        for obf in ordered:
            original = self._reverse_map[obf]
            pattern = r'\b' + re.escape(obf) + r'\b'
            source = re.sub(pattern, original, source)
        return source
