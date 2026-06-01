"""Visitor que recorre el ParseTree y recolecta identificadores renombrables.

Esta es la pasada de analisis del pipeline. No muta nada, solo construye:
- una SymbolTable con todos los identificadores que deben ser renombrados
- un set de nombres importados (que no deben renombrarse)

La gramatica usada (Python 3.13 de grammars-v4) define un rule `name` que
envuelve los tokens NAME / NAME_OR_TYPE / NAME_OR_MATCH / NAME_OR_CASE /
NAME_OR_WILDCARD. Para extraer el texto de un identificador, hay que llamar
`getText()` sobre el `NameContext` (no sobre el token directamente).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'generated'))

from PythonParserVisitor import PythonParserVisitor  # noqa: E402
from PythonParser import PythonParser  # noqa: E402

from src.symbol_table import SymbolTable
from src.protected_names import is_protected


class SymbolCollectorVisitor(PythonParserVisitor):
    """Recolecta identificadores renombrables del codigo fuente.

    Reglas de coleccion:
    - def NOMBRE(...)   -> NOMBRE como 'function', params como 'parameter'.
    - class NOMBRE(...) -> NOMBRE como 'class'.
    - x = ...           -> x como 'variable'.
    - x, y = ...        -> cada nombre del LHS como 'variable'.
    - for x in ...      -> x como 'variable'.
    - with ... as x:    -> x como 'variable'.
    - except ... as x:  -> x como 'variable'.
    - lambda x: ...     -> x como 'parameter'.
    - [x for x in ...]  -> x como 'variable'.

    Reglas de exclusion:
    - is_protected(name) -> excluido.
    - name en self.imports -> excluido.
    - Atributos accedidos con punto (`obj.x`) -> excluido.
    """

    def __init__(self) -> None:
        super().__init__()
        self.symbols: SymbolTable = SymbolTable()
        self.imports: set[str] = set()
        self.global_decls: set[str] = set()
        # Profundidad de anidamiento dentro de class_def. Si > 0, las funciones
        # son metodos y NO se renombran (porque su acceso es via obj.metodo).
        self._class_depth: int = 0

    # ----------------------- helpers -----------------------

    def _name_text(self, name_ctx) -> str:
        """Extrae el texto de un NameContext sin espacios."""
        return name_ctx.getText() if name_ctx is not None else ''

    def _add(self, name: str, kind: str) -> None:
        if not name:
            return
        if is_protected(name):
            return
        if name in self.imports:
            return
        self.symbols.add(name, kind)

    def _collect_names_from_target(self, ctx, kind: str = 'variable') -> None:
        """Walk recursivo: extrae nombres simples de un target de asignacion.

        Un nombre simple aparece como un `star_atom: name` o `del_t_atom: name`,
        sin trailers (sin '.x' ni '[x]'). Si encontramos un nodo
        `target_with_star_atom` o `single_subscript_attribute_target` con su
        forma `t_primary ('.' name | '[' slices ']')`, ese subarbol completo
        es un acceso a atributo o subscript: NO recolectar nombres de adentro.
        """
        if ctx is None:
            return

        cls_name = type(ctx).__name__

        # star_atom: name | '(' ... ')' | '[' ... ']'
        if cls_name == 'Star_atomContext':
            # Si el primer hijo es un NameContext, es un nombre simple
            if ctx.name() is not None:
                self._add(self._name_text(ctx.name()), kind)
                return
            # Si es tupla/lista, recorrer los hijos
            for child in ctx.children or []:
                self._collect_names_from_target(child, kind)
            return

        # target_with_star_atom: t_primary ('.'|'[') ...  |  star_atom
        # Si tiene t_primary, es un atributo/subscript -> NO recolectar
        if cls_name == 'Target_with_star_atomContext':
            if ctx.t_primary() is not None:
                # acceso a atributo o subscript: ignorar
                return
            if ctx.star_atom() is not None:
                self._collect_names_from_target(ctx.star_atom(), kind)
            return

        # star_target: '*' star_target  |  target_with_star_atom
        if cls_name == 'Star_targetContext':
            if ctx.target_with_star_atom() is not None:
                self._collect_names_from_target(ctx.target_with_star_atom(), kind)
            elif ctx.star_target() is not None:
                self._collect_names_from_target(ctx.star_target(), kind)
            return

        # star_targets: star_target (',' star_target)* ','?
        if cls_name == 'Star_targetsContext':
            for st in ctx.star_target():
                self._collect_names_from_target(st, kind)
            return

        if cls_name == 'Star_targets_tuple_seqContext':
            for st in ctx.star_target():
                self._collect_names_from_target(st, kind)
            return

        if cls_name == 'Star_targets_list_seqContext':
            for st in ctx.star_target():
                self._collect_names_from_target(st, kind)
            return

        if cls_name == 'Single_targetContext':
            # single_target: single_subscript_attribute_target | name | '(' single_target ')'
            if ctx.name() is not None:
                self._add(self._name_text(ctx.name()), kind)
            elif ctx.single_target() is not None:
                self._collect_names_from_target(ctx.single_target(), kind)
            # single_subscript_attribute_target -> ignorar (atributo)
            return

        # Para cualquier otro tipo, intentar recorrer hijos
        if hasattr(ctx, 'children') and ctx.children:
            for child in ctx.children:
                if hasattr(child, 'children'):
                    self._collect_names_from_target(child, kind)

    # ----------------------- imports -----------------------

    def visitImport_name(self, ctx: PythonParser.Import_nameContext):
        """import foo, bar.baz [as x]"""
        dotted_as_names = ctx.dotted_as_names()
        if dotted_as_names is not None:
            for dan in dotted_as_names.dotted_as_name():
                # dotted_as_name: dotted_name ('as' name )?
                names = dan.name()  # lista de NameContext si hay 'as'
                if names:
                    # 'as NAME': la ultima name es el alias
                    self.imports.add(self._name_text(names[-1]))
                else:
                    # Sin alias: el nombre top-level del dotted_name
                    dn = dan.dotted_name()
                    if dn is not None:
                        first = self._extract_first_name_from_dotted(dn)
                        if first:
                            self.imports.add(first)
        return None

    def _extract_first_name_from_dotted(self, dotted_name_ctx) -> str:
        """dotted_name: dotted_name '.' name | name -> extraer el primer nombre."""
        # Recursivo: bajar por la izquierda
        cur = dotted_name_ctx
        while True:
            inner = cur.dotted_name()
            if inner is None:
                # caso base: cur es solo `name`
                n = cur.name()
                return self._name_text(n) if n is not None else ''
            cur = inner

    def visitImport_from(self, ctx: PythonParser.Import_fromContext):
        """from foo import a, b as c"""
        targets = ctx.import_from_targets()
        if targets is None:
            return None
        as_names_ctx = targets.import_from_as_names()
        if as_names_ctx is None:
            return None
        for item in as_names_ctx.import_from_as_name():
            names = item.name()  # lista: 1 si solo 'X', 2 si 'X as Y'
            if names:
                # El nombre disponible en el scope es el ultimo
                self.imports.add(self._name_text(names[-1]))
        return None

    # ----------------------- definiciones -----------------------

    def visitFunction_def_raw(self, ctx: PythonParser.Function_def_rawContext):
        """def NOMBRE(params): block  |  async def NOMBRE(params): block.

        Si estamos DENTRO de una clase, el nombre es un metodo y NO se
        renombra (su acceso es via obj.metodo y el atributo no se toca).
        Los parametros si se renombran siempre.
        """
        name_ctx = ctx.name()
        if name_ctx is not None and self._class_depth == 0:
            self._add(self._name_text(name_ctx), 'function')
        params = ctx.params()
        if params is not None:
            self._collect_params(params)
        block = ctx.block()
        if block is not None:
            self.visit(block)
        return None

    def _collect_params(self, params_ctx) -> None:
        """Recorre toda la estructura de params recolectando NAMEs."""
        # Estrategia general: buscar todos los Param/ParamContext dentro
        # y extraer su `name`. Los lambda_param tienen el mismo patron.
        for node in self._descendant_contexts(params_ctx, {'ParamContext', 'Param_star_annotationContext'}):
            n = node.name() if hasattr(node, 'name') else None
            if n is not None:
                self._add(self._name_text(n), 'parameter')

    def _descendant_contexts(self, ctx, target_class_names: set[str]):
        """Yield todos los descendientes cuya clase nombre este en target_class_names."""
        stack = [ctx]
        while stack:
            node = stack.pop()
            if type(node).__name__ in target_class_names:
                yield node
            if hasattr(node, 'children') and node.children:
                for ch in node.children:
                    if hasattr(ch, 'children'):
                        stack.append(ch)

    def visitClass_def_raw(self, ctx: PythonParser.Class_def_rawContext):
        """class NOMBRE(args): block"""
        name_ctx = ctx.name()
        if name_ctx is not None:
            self._add(self._name_text(name_ctx), 'class')
        block = ctx.block()
        if block is not None:
            self._class_depth += 1
            try:
                self.visit(block)
            finally:
                self._class_depth -= 1
        return None

    # ----------------------- asignaciones -----------------------

    def visitAssignment(self, ctx: PythonParser.AssignmentContext):
        """Multiples formas:
        - name ':' expression ('=' annotated_rhs)?            (anotada simple)
        - (single_target | ...) ':' expression ('=' ...)?     (anotada compleja)
        - (star_targets '=')+ (yield_expr | star_expressions) TYPE_COMMENT?
        - single_target augassign (yield_expr | star_expressions)
        """
        # Caso 1: anotada simple `x: int = ...`
        # En la gramatica esto es: name ':' expression ('=' annotated_rhs)?
        # ctx.name() retorna NameContext si esta presente
        if ctx.name() is not None:
            self._add(self._name_text(ctx.name()), 'variable')

        # Caso 3: una o mas star_targets con '='
        for star_targets in ctx.star_targets():
            self._collect_names_from_target(star_targets, 'variable')

        # Caso 4: augmented assignment (x += 1). LHS es single_target, NO se
        # debe agregar como variable nueva (ya existe), pero si el nombre no
        # esta declarado en otro lado, lo agregamos defensivamente.
        if ctx.augassign() is not None and ctx.single_target() is not None:
            self._collect_names_from_target(ctx.single_target(), 'variable')

        return self.visitChildren(ctx)

    # ----------------------- for / with / except -----------------------

    def visitFor_stmt(self, ctx: PythonParser.For_stmtContext):
        """for STAR_TARGETS in EXPR: BLOCK"""
        st = ctx.star_targets()
        if st is not None:
            self._collect_names_from_target(st, 'variable')
        return self.visitChildren(ctx)

    def visitWith_item(self, ctx: PythonParser.With_itemContext):
        """with EXPR as STAR_TARGET"""
        st = ctx.star_target()
        if st is not None:
            self._collect_names_from_target(st, 'variable')
        return self.visitChildren(ctx)

    def visitExcept_block(self, ctx: PythonParser.Except_blockContext):
        """except EXPR as NAME : BLOCK"""
        # ctx.name() es el NameContext del 'as NAME'
        if ctx.name() is not None:
            self._add(self._name_text(ctx.name()), 'variable')
        return self.visitChildren(ctx)

    def visitExcept_star_block(self, ctx: PythonParser.Except_star_blockContext):
        if ctx.name() is not None:
            self._add(self._name_text(ctx.name()), 'variable')
        return self.visitChildren(ctx)

    # ----------------------- lambda y comprehensions -----------------------

    def visitLambdef(self, ctx: PythonParser.LambdefContext):
        """lambda PARAMS: EXPR"""
        params = ctx.lambda_params()
        if params is not None:
            # Buscar todos los lambda_param dentro
            for node in self._descendant_contexts(params, {'Lambda_paramContext'}):
                n = node.name() if hasattr(node, 'name') else None
                if n is not None:
                    self._add(self._name_text(n), 'parameter')
        return self.visitChildren(ctx)

    def visitFor_if_clause(self, ctx: PythonParser.For_if_clauseContext):
        """for STAR_TARGETS in DISJUNCTION (if DISJUNCTION)*"""
        st = ctx.star_targets()
        if st is not None:
            self._collect_names_from_target(st, 'variable')
        return self.visitChildren(ctx)

    # ----------------------- walrus -----------------------

    def visitAssignment_expression(self, ctx: PythonParser.Assignment_expressionContext):
        """NAME ':=' EXPR"""
        if ctx.name() is not None:
            self._add(self._name_text(ctx.name()), 'variable')
        return self.visitChildren(ctx)

    # ----------------------- declaraciones globales -----------------------

    def visitGlobal_stmt(self, ctx: PythonParser.Global_stmtContext):
        for n in ctx.name():
            self.global_decls.add(self._name_text(n))
        return None

    def visitNonlocal_stmt(self, ctx: PythonParser.Nonlocal_stmtContext):
        for n in ctx.name():
            self.global_decls.add(self._name_text(n))
        return None
