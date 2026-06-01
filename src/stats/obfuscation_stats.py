"""Estadisticas del proceso de ofuscacion (para CLI y HTML viewer)."""

from dataclasses import dataclass, asdict


@dataclass
class ObfuscationStats:
    """Contadores recolectados durante el pipeline de ofuscacion."""
    lines_original: int = 0
    lines_obfuscated: int = 0
    identifiers_renamed: int = 0
    strings_ciphered: int = 0
    comments_removed: int = 0
    docstrings_removed: int = 0
    dead_code_inserted: int = 0
    symbols_total: int = 0

    def to_dict(self) -> dict:
        return asdict(self)
