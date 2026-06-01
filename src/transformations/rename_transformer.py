"""Renombra identificadores usando TokenStreamRewriter.

Recorre el stream de tokens y, para cada token de tipo NAME (o sus variantes
soft-keyword NAME_OR_TYPE, NAME_OR_MATCH, NAME_OR_CASE), verifica si tiene
un Symbol asociado y lo reemplaza por el nombre ofuscado.

Reglas:
- Si el texto del token esta en la SymbolTable, se reemplaza.
- Excepcion: si el token anterior VISIBLE es '.', no se renombra (es un acceso
  a atributo: `obj.metodo` -> `metodo` NO se toca).
- Tampoco se renombra si esta en la lista de imports o si is_protected().
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'generated'))

from antlr4 import CommonTokenStream  # noqa: E402
from antlr4.TokenStreamRewriter import TokenStreamRewriter  # noqa: E402
from PythonLexer import PythonLexer  # noqa: E402

from src.symbol_table import SymbolTable
from src.protected_names import is_protected


# Tipos de token que representan identificadores en la gramatica Python 3.13
NAME_TOKEN_TYPES: set[int] = {
    PythonLexer.NAME,
    PythonLexer.NAME_OR_TYPE,
    PythonLexer.NAME_OR_MATCH,
    PythonLexer.NAME_OR_CASE,
}


class RenameTransformer:
    """Aplica el renombrado sobre un TokenStream usando TokenStreamRewriter."""

    def __init__(self,
                 token_stream: CommonTokenStream,
                 symbols: SymbolTable,
                 imports: set[str]):
        self.tokens = token_stream
        self.symbols = symbols
        self.imports = imports
        self.rewriter = TokenStreamRewriter(token_stream)
        self.renamed_count: int = 0

    def apply(self) -> str:
        n = len(self.tokens.tokens)
        for i in range(n):
            tok = self.tokens.tokens[i]
            if tok.type not in NAME_TOKEN_TYPES:
                continue
            name = tok.text
            if not name or is_protected(name):
                continue
            if name in self.imports:
                continue
            sym = self.symbols.get(name)
            if sym is None:
                continue
            if self._previous_visible_is_dot(i):
                continue
            self.rewriter.replaceSingleToken(tok, sym.obfuscated)
            self.renamed_count += 1
        return self.rewriter.getDefaultText()

    def _previous_visible_is_dot(self, index: int) -> bool:
        """True si el token visible anterior es '.' (acceso a atributo)."""
        i = index - 1
        while i >= 0:
            tok = self.tokens.tokens[i]
            if tok.channel != 0:
                i -= 1
                continue
            if tok.type == PythonLexer.NEWLINE:
                i -= 1
                continue
            return tok.text == '.'
        return False
