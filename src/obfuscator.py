"""Orquesta el pipeline completo de ofuscacion.

El pipeline es:
1. Parse inicial -> arbol + token stream.
2. SymbolCollectorVisitor -> tabla de simbolos + imports.
3. RenameTransformer -> reemplaza identificadores.
4. CommentRemover -> elimina comentarios y docstrings.
5. StringCipher -> codifica strings en Base64.
6. DeadCodeInserter (opcional) -> inserta sentencias inofensivas.

Cada paso re-tokeniza el resultado del anterior. Esto evita inconsistencias
en los indices de tokens y permite que las transformaciones se apliquen en
secuencia limpia.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'generated'))

from antlr4 import InputStream, CommonTokenStream  # noqa: E402
from antlr4.error.ErrorListener import ErrorListener  # noqa: E402
from PythonLexer import PythonLexer  # noqa: E402
from PythonParser import PythonParser  # noqa: E402

from src.visitors.symbol_collector import SymbolCollectorVisitor
from src.transformations.rename_transformer import RenameTransformer
from src.transformations.comment_remover import CommentRemover
from src.transformations.string_cipher import StringCipher
from src.transformations.dead_code_inserter import DeadCodeInserter
from src.stats.obfuscation_stats import ObfuscationStats


class _FailFastErrorListener(ErrorListener):
    """Aborta el proceso ante el primer error de sintaxis."""

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise SyntaxError(f"Error de sintaxis Python en linea {line}:{column}: {msg}")


class ObfuscatorConfig:
    """Configuracion del Obfuscator. Cada flag activa o desactiva una pasada."""

    def __init__(self,
                 rename: bool = True,
                 remove_comments: bool = True,
                 cipher_strings: bool = True,
                 dead_code: bool = False,
                 dead_code_density: float = 0.3,
                 dead_code_seed: int | None = None):
        self.rename = rename
        self.remove_comments = remove_comments
        self.cipher_strings = cipher_strings
        self.dead_code = dead_code
        self.dead_code_density = dead_code_density
        self.dead_code_seed = dead_code_seed


class Obfuscator:
    """Orquestador del pipeline de ofuscacion."""

    def __init__(self, config: ObfuscatorConfig | None = None):
        self.config = config or ObfuscatorConfig()

    def obfuscate_source(self, source: str) -> tuple[str, dict, ObfuscationStats]:
        """Ofusca codigo. Retorna (codigo_ofuscado, symbol_map_dict, stats)."""
        stats = ObfuscationStats()
        stats.lines_original = self._count_lines(source)

        # Asegurar newline final (la gramatica requiere NEWLINE final).
        if source and not source.endswith('\n'):
            source = source + '\n'

        # ---- PASADA 1: analisis ----
        tree, _ = self._parse(source)
        collector = SymbolCollectorVisitor()
        collector.visit(tree)
        stats.symbols_total = len(collector.symbols.all_symbols())

        current_source = source

        # ---- PASADA 2: renombrado ----
        if self.config.rename:
            _, ts = self._parse(current_source)
            renamer = RenameTransformer(ts, collector.symbols, collector.imports)
            current_source = renamer.apply()
            stats.identifiers_renamed = renamer.renamed_count

        # ---- PASADA 3: comentarios y docstrings ----
        if self.config.remove_comments:
            tree3, ts3 = self._parse(current_source)
            remover = CommentRemover(ts3, tree3)
            current_source = remover.apply()
            stats.comments_removed = remover.comments_removed
            stats.docstrings_removed = remover.docstrings_removed

        # ---- PASADA 4: cifrado de strings ----
        if self.config.cipher_strings:
            _, ts4 = self._parse(current_source)
            cipher = StringCipher(ts4)
            current_source = cipher.apply()
            stats.strings_ciphered = cipher.ciphered_count

        # ---- PASADA 5: dead code ----
        if self.config.dead_code:
            tree5, ts5 = self._parse(current_source)
            inserter = DeadCodeInserter(
                ts5, tree5,
                density=self.config.dead_code_density,
                seed=self.config.dead_code_seed,
            )
            current_source = inserter.apply()
            stats.dead_code_inserted = inserter.inserted_count

        stats.lines_obfuscated = self._count_lines(current_source)
        return current_source, collector.symbols.to_dict(), stats

    def obfuscate_file(self,
                        input_path: Path,
                        output_path: Path,
                        map_path: Path) -> ObfuscationStats:
        source = input_path.read_text(encoding='utf-8')
        obfuscated, symbol_map, stats = self.obfuscate_source(source)
        output_path.write_text(obfuscated, encoding='utf-8')
        map_path.write_text(
            json.dumps(symbol_map, indent=2, ensure_ascii=False),
            encoding='utf-8',
        )
        return stats

    @staticmethod
    def _parse(source: str) -> tuple[object, CommonTokenStream]:
        """Tokeniza y parsea el codigo. Falla si hay errores de sintaxis.

        Despues de fill(), limpia el texto de los tokens sinteticos
        ENCODING/INDENT/DEDENT que el PythonLexerBase inyecta, para que
        no aparezcan literalmente en la salida del TokenStreamRewriter.
        """
        if source and not source.endswith('\n'):
            source = source + '\n'
        stream = InputStream(source)
        lexer = PythonLexer(stream)
        lexer.removeErrorListeners()
        lexer.addErrorListener(_FailFastErrorListener())
        token_stream = CommonTokenStream(lexer)
        token_stream.fill()
        # Limpiar tokens sinteticos del PythonLexerBase
        for tok in token_stream.tokens:
            if tok.type in (PythonLexer.ENCODING, PythonLexer.INDENT, PythonLexer.DEDENT):
                tok.text = ''
        parser = PythonParser(token_stream)
        parser.removeErrorListeners()
        parser.addErrorListener(_FailFastErrorListener())
        tree = parser.file_input()
        return tree, token_stream

    @staticmethod
    def _count_lines(s: str) -> int:
        if not s:
            return 0
        return s.count('\n') + (0 if s.endswith('\n') else 1)
