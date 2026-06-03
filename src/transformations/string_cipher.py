"""Cifra string literals en Base64 con decodificacion inline.

Cada string literal se reemplaza por:
    __import__("base64").b64decode("<encoded>").decode("utf-8")

Strings NO cifrados:
- f-strings (contienen expresiones evaluables, son token FSTRING_START en este lexer)
- raw strings (r"...")
- byte strings (b"...")
- strings vacios -> tambien se cifran (caso valido)
"""

import base64
import codecs
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'generated'))

from antlr4 import CommonTokenStream  # noqa: E402
from antlr4.TokenStreamRewriter import TokenStreamRewriter  # noqa: E402
from PythonLexer import PythonLexer  # noqa: E402


class StringCipher:
    """Cifra strings ordinarios en Base64."""

    def __init__(self, token_stream: CommonTokenStream):
        self.tokens = token_stream
        self.rewriter = TokenStreamRewriter(token_stream)
        self.ciphered_count: int = 0

    def apply(self) -> str:
        fstring_string_indices = self._find_strings_inside_fstrings()
        for tok in self.tokens.tokens:
            if tok.type != PythonLexer.STRING:
                continue
            if tok.tokenIndex in fstring_string_indices:
                continue
            text = tok.text
            if self._should_skip(text):
                continue
            content = self._extract_content(text)
            if content is None:
                continue
            encoded = base64.b64encode(content.encode('utf-8')).decode('ascii')
            replacement = (
                f'__import__("base64").b64decode("{encoded}").decode("utf-8")'
            )
            self.rewriter.replaceSingleToken(tok, replacement)
            self.ciphered_count += 1
        return self.rewriter.getDefaultText()

    def _find_strings_inside_fstrings(self) -> set[int]:
        """Retorna índices de tokens STRING anidados dentro de f-strings.

        Los strings como 'key' en f"{d['key']}" son tokens STRING normales,
        pero cifrarlos rompe la sintaxis del f-string exterior.
        """
        inside: set[int] = set()
        depth = 0
        for tok in self.tokens.tokens:
            if tok.type == PythonLexer.FSTRING_START:
                depth += 1
            elif tok.type == PythonLexer.FSTRING_END:
                if depth > 0:
                    depth -= 1
            elif tok.type == PythonLexer.STRING and depth > 0:
                inside.add(tok.tokenIndex)
        return inside

    def _should_skip(self, text: str) -> bool:
        """Saltar raw strings y byte strings (f-strings ya no entran porque
        tienen otro token type)."""
        if not text:
            return True
        # Identificar prefijo
        i = 0
        prefix = ''
        while i < len(text) and text[i].lower() in ('r', 'b', 'u'):
            prefix += text[i].lower()
            i += 1
            if i >= 2:
                break
        # u'' -> unicode normal, se puede cifrar
        if prefix in ('', 'u'):
            return False
        # cualquier prefijo con 'r' o 'b' lo saltamos
        return 'r' in prefix or 'b' in prefix

    def _extract_content(self, raw: str) -> str | None:
        """Extrae el contenido de un string literal procesando escapes."""
        # Saltar prefijo
        i = 0
        is_raw = False
        while i < len(raw) and raw[i].lower() in ('r', 'b', 'u'):
            if raw[i].lower() == 'r':
                is_raw = True
            i += 1
            if i >= 2:
                break
        body = raw[i:]
        if not body:
            return None
        # Determinar tipo de comillas
        if body.startswith('"""') and body.endswith('"""') and len(body) >= 6:
            inner = body[3:-3]
        elif body.startswith("'''") and body.endswith("'''") and len(body) >= 6:
            inner = body[3:-3]
        elif body.startswith('"') and body.endswith('"') and len(body) >= 2:
            inner = body[1:-1]
        elif body.startswith("'") and body.endswith("'") and len(body) >= 2:
            inner = body[1:-1]
        else:
            return None
        if is_raw:
            return inner
        try:
            return codecs.decode(inner, 'unicode_escape')
        except Exception:
            return None
