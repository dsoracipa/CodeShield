"""Elimina comentarios '#' y docstrings.

- Comentarios '#': estan en el canal HIDDEN del lexer (token COMMENT).
- Docstrings: son string literals triple-quoted que aparecen como PRIMER
  statement de un bloque (modulo, funcion, clase).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'generated'))

from antlr4 import CommonTokenStream  # noqa: E402
from antlr4.TokenStreamRewriter import TokenStreamRewriter  # noqa: E402
from PythonLexer import PythonLexer  # noqa: E402


class CommentRemover:
    """Elimina comentarios '#' y docstrings del codigo fuente."""

    def __init__(self, token_stream: CommonTokenStream, parse_tree):
        self.tokens = token_stream
        self.tree = parse_tree
        self.rewriter = TokenStreamRewriter(token_stream)
        self.comments_removed: int = 0
        self.docstrings_removed: int = 0

    def apply(self) -> str:
        self._remove_hash_comments()
        self._remove_docstrings(self.tree)
        return self.rewriter.getDefaultText()

    def _remove_hash_comments(self) -> None:
        for tok in self.tokens.tokens:
            if tok.type == PythonLexer.COMMENT:
                self.rewriter.delete(
                    self.rewriter.DEFAULT_PROGRAM_NAME,
                    tok.tokenIndex, tok.tokenIndex,
                )
                self.comments_removed += 1

    def _remove_docstrings(self, ctx) -> None:
        """Recorre el arbol buscando bloques con docstring como primer stmt."""
        if ctx is None:
            return
        cls_name = type(ctx).__name__

        # Modulo: file_input -> statements -> statement+ -> statement -> simple_stmts -> simple_stmt -> star_expressions
        if cls_name == 'File_inputContext':
            self._try_remove_first_string_stmt_from_module(ctx)
        elif cls_name == 'Function_def_rawContext' or cls_name == 'Class_def_rawContext':
            block = ctx.block() if hasattr(ctx, 'block') else None
            if block is not None:
                self._try_remove_first_string_stmt_from_block(block)

        if hasattr(ctx, 'children') and ctx.children:
            for child in ctx.children:
                if hasattr(child, 'children'):
                    self._remove_docstrings(child)

    def _try_remove_first_string_stmt_from_module(self, file_input_ctx) -> None:
        """En file_input, buscar el primer statement y ver si es solo un string."""
        statements = file_input_ctx.statements() if hasattr(file_input_ctx, 'statements') else None
        if statements is None:
            return
        stmts = statements.statement()
        if not stmts:
            return
        self._remove_if_string_stmt(stmts[0])

    def _try_remove_first_string_stmt_from_block(self, block_ctx) -> None:
        """En un block, buscar el primer statement."""
        # block: NEWLINE INDENT statements DEDENT | simple_stmts
        statements = block_ctx.statements() if hasattr(block_ctx, 'statements') else None
        if statements is not None:
            stmts = statements.statement()
            if stmts:
                self._remove_if_string_stmt(stmts[0])
            return
        # simple_stmts
        simple_stmts = block_ctx.simple_stmts() if hasattr(block_ctx, 'simple_stmts') else None
        if simple_stmts is not None:
            small = simple_stmts.simple_stmt()
            if small:
                self._remove_if_string_stmt_simple(small[0])

    def _remove_if_string_stmt(self, stmt_ctx) -> None:
        """statement: compound_stmt | simple_stmts -> recurse a simple_stmts."""
        simple_stmts = stmt_ctx.simple_stmts() if hasattr(stmt_ctx, 'simple_stmts') else None
        if simple_stmts is None:
            return
        small = simple_stmts.simple_stmt()
        if not small:
            return
        self._remove_if_string_stmt_simple(small[0])

    def _remove_if_string_stmt_simple(self, simple_stmt_ctx) -> None:
        """simple_stmt -> star_expressions -> ... -> strings.

        Si el simple_stmt es solo un string literal (triple-quoted o no),
        eliminar la linea completa que lo contiene (incluyendo la WS de
        indentacion que la precede y el NEWLINE que la sigue).
        """
        text = simple_stmt_ctx.getText() if hasattr(simple_stmt_ctx, 'getText') else ''
        text = text.strip()
        if not text:
            return
        if not self._looks_like_string_literal(text):
            return
        start_idx = simple_stmt_ctx.start.tokenIndex
        stop_idx = simple_stmt_ctx.stop.tokenIndex
        # Expandir hacia atras: incluir WS / INDENT-vacios anteriores
        i = start_idx - 1
        while i >= 0:
            t = self.tokens.tokens[i]
            if t.channel != 0 and t.type != PythonLexer.NEWLINE:
                start_idx = i
                i -= 1
                continue
            if t.type in (PythonLexer.INDENT, PythonLexer.DEDENT, PythonLexer.ENCODING):
                start_idx = i
                i -= 1
                continue
            break
        # Expandir hacia adelante: incluir el NEWLINE final
        try:
            after = self.tokens.tokens[stop_idx + 1]
            if after.type == PythonLexer.NEWLINE:
                stop_idx = stop_idx + 1
        except IndexError:
            pass
        self.rewriter.delete(
            self.rewriter.DEFAULT_PROGRAM_NAME, start_idx, stop_idx,
        )
        self.docstrings_removed += 1

    def _looks_like_string_literal(self, text: str) -> bool:
        """True si el texto luce como un string literal pelado."""
        # Quitar prefijos r, b, u, f (combinados, mayusculas/minusculas)
        i = 0
        while i < len(text) and text[i].lower() in ('r', 'b', 'u', 'f'):
            i += 1
            if i >= 4:  # max prefix length
                break
        rest = text[i:]
        if not rest:
            return False
        if rest.startswith('"""') and rest.endswith('"""') and len(rest) >= 6:
            return True
        if rest.startswith("'''") and rest.endswith("'''") and len(rest) >= 6:
            return True
        if rest.startswith('"') and rest.endswith('"') and len(rest) >= 2:
            return True
        if rest.startswith("'") and rest.endswith("'") and len(rest) >= 2:
            return True
        return False
