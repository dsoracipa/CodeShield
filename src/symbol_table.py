"""Tabla de simbolos con mapping global original -> ofuscado."""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class Symbol:
    """Un identificador renombrado por el ofuscador.

    kind puede ser: 'variable', 'function', 'class', 'parameter'.
    """
    original: str
    obfuscated: str
    kind: str


PREFIX_BY_KIND: dict[str, str] = {
    'variable': '_v',
    'function': '_f',
    'class': '_C',
    'parameter': '_p',
}


class SymbolTable:
    """Mapeo global de nombres originales a nombres ofuscados.

    El mismo nombre original siempre recibe el mismo nombre ofuscado,
    sin importar el scope. Esto preserva la semantica de Python: dos
    variables con el mismo nombre en scopes distintos siguen siendo
    distintas porque el scope es lexico.
    """

    def __init__(self) -> None:
        self._symbols: dict[str, Symbol] = {}
        self._used_obfuscated: set[str] = set()
        self._counter: int = 0

    def _generate_obfuscated_name(self, kind: str) -> str:
        prefix = PREFIX_BY_KIND.get(kind, '_x')
        while True:
            name = f"{prefix}{self._counter:04x}"
            self._counter += 1
            if name not in self._used_obfuscated:
                return name

    def add(self, original: str, kind: str) -> Symbol:
        """Anade un simbolo. Si ya existe, devuelve el existente (first wins)."""
        if original in self._symbols:
            return self._symbols[original]
        obfuscated = self._generate_obfuscated_name(kind)
        sym = Symbol(original=original, obfuscated=obfuscated, kind=kind)
        self._symbols[original] = sym
        self._used_obfuscated.add(obfuscated)
        return sym

    def get(self, original: str) -> Optional[Symbol]:
        return self._symbols.get(original)

    def has(self, original: str) -> bool:
        return original in self._symbols

    def all_symbols(self) -> list[Symbol]:
        return list(self._symbols.values())

    def to_dict(self) -> dict:
        return {
            'version': '1.0',
            'symbols': [asdict(s) for s in self._symbols.values()],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'SymbolTable':
        st = cls()
        for s in data.get('symbols', []):
            sym = Symbol(original=s['original'], obfuscated=s['obfuscated'], kind=s['kind'])
            st._symbols[sym.original] = sym
            st._used_obfuscated.add(sym.obfuscated)
        return st
