"""Inserta codigo muerto inofensivo a nivel de modulo.

Solo inserta statements top-level para no afectar el flujo de control de
funciones o clases. Las variables insertadas usan un prefijo improbable
(`_codeshield_dc_*`) para minimizar colisiones con codigo del usuario.
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'generated'))

from antlr4 import CommonTokenStream  # noqa: E402
from antlr4.TokenStreamRewriter import TokenStreamRewriter  # noqa: E402


DEAD_SNIPPETS: list[str] = [
    "_codeshield_dc_{i} = None\n",
    "_codeshield_dc_{i} = 0\n",
    "_codeshield_dc_{i} = []\n",
    "_codeshield_dc_{i} = (lambda: None)()\n",
    "_codeshield_dc_{i} = True or False\n",
]


class DeadCodeInserter:
    """Inserta snippets de codigo muerto antes de cada statement top-level."""

    def __init__(self,
                 token_stream: CommonTokenStream,
                 parse_tree,
                 density: float = 0.3,
                 seed: int | None = None):
        self.tokens = token_stream
        self.tree = parse_tree
        self.density = density
        self.rewriter = TokenStreamRewriter(token_stream)
        self.counter: int = 0
        self.inserted_count: int = 0
        self._rng = random.Random(seed) if seed is not None else random.Random()

    def apply(self) -> str:
        stmts = self._get_top_level_stmts()
        for stmt in stmts:
            if self._rng.random() < self.density:
                snippet = self._rng.choice(DEAD_SNIPPETS).format(i=self.counter)
                self.counter += 1
                self.rewriter.insertBeforeToken(stmt.start, snippet)
                self.inserted_count += 1
        return self.rewriter.getDefaultText()

    def _get_top_level_stmts(self):
        """Retorna los nodos statement directos del file_input."""
        results = []
        statements = self.tree.statements() if hasattr(self.tree, 'statements') else None
        if statements is None:
            return results
        for stmt in statements.statement():
            results.append(stmt)
        return results
