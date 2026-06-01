# CodeShield - Arquitectura interna

## Visión general

CodeShield está construido sobre ANTLR v4 con la gramática Python 3.13 de
[grammars-v4](https://github.com/antlr/grammars-v4/tree/master/python/python3_13).
El pipeline combina el **patrón Visitor** (para análisis no destructivo) con
**`TokenStreamRewriter`** (para mutación quirúrgica del código fuente
preservando todo lo no modificado).

## Diagrama de flujo

```
archivo.py
    │
    ▼
PythonLexer + CommonTokenStream
    │
    ▼
PythonParser  →  ParseTree
    │
    ▼
SymbolCollectorVisitor  (pasada de análisis)
    │
    ├─→ SymbolTable (original → ofuscado, global)
    └─→ set(imports)
    │
    ▼
Pipeline de transformaciones (cada paso re-tokeniza)
    │
    ├─→ RenameTransformer
    ├─→ CommentRemover
    ├─→ StringCipher
    └─→ DeadCodeInserter  (opcional)
    │
    ▼
Salidas:
  - archivo_obfuscated.py
  - symbol_map.json
  - comparison.html (opcional)
```

## Decisiones de diseño

### Visitor + TokenStreamRewriter (no visitor reconstructivo)

Un visitor reconstructivo (que recorre el AST y reemite cada nodo) requeriría
manejar manualmente cada una de las >100 reglas de la gramática Python, y
perder todos los tokens del canal `HIDDEN` (espacios, comentarios) salvo que
se manejen explícitamente.

`TokenStreamRewriter` opera sobre el stream de tokens directamente,
permitiendo hacer reemplazos, inserciones y eliminaciones quirúrgicas: todo
lo que no se modifica se preserva exactamente igual.

El enfoque híbrido **usa el Visitor para identificar qué transformar** y
aplica los cambios a través del `TokenStreamRewriter`. Cumple el requisito
académico del patrón Visitor y produce código limpio.

### Mapping global (un nombre → un nombre ofuscado)

Cada nombre original recibe un único nombre ofuscado en todo el archivo, sin
importar el scope. Esto preserva la semántica de Python (dos variables con el
mismo nombre en scopes distintos siguen siendo distintas porque el scope es
léxico, no por el nombre del identificador) y simplifica enormemente la
implementación.

### Re-tokenización entre etapas

Cada transformación crea su propio `TokenStreamRewriter`. Después de aplicar
una transformación, se obtiene el texto con `getDefaultText()` y se
re-tokeniza para la siguiente. Esto evita inconsistencias en los índices de
tokens al aplicar múltiples capas de cambios sobre el mismo stream.

## Detalles importantes

### Tokens sintéticos del PythonLexerBase

El `PythonLexerBase` (que maneja la generación de INDENT/DEDENT) emite tres
tipos de tokens sintéticos que NO corresponden a texto del código fuente:

- `ENCODING` (tipo 1): con texto `"utf-8"` o similar (canal HIDDEN).
- `INDENT` (tipo 2): con texto `<INDENT>` por defecto (canal DEFAULT).
- `DEDENT` (tipo 3): con texto `<DEDENT>` por defecto (canal DEFAULT).

Estos tokens deben tener su `.text` limpiado a cadena vacía **después** de
`tokenStream.fill()` y **antes** de cualquier operación de reescritura. De
lo contrario, `getDefaultText()` los incluye literalmente y se produce
código sintácticamente inválido.

### Gramática Python 3.13: nombres de reglas relevantes

- `function_def`, `function_def_raw` (no `funcdef`)
- `class_def`, `class_def_raw` (no `classdef`)
- `assignment` (no `expr_stmt`); maneja `x = ...`, `x: T = ...`, `x += ...`,
  asignaciones encadenadas (varios `star_targets` con `=`).
- `import_name`, `import_from`
- `for_stmt`, `with_stmt`, `try_stmt`
- `lambdef` y `lambda_param`
- `except_block` (no `except_clause`)
- `with_item`
- `for_if_clause` (para comprehensions)

La regla `name` envuelve los tokens NAME, NAME_OR_TYPE, NAME_OR_MATCH,
NAME_OR_CASE y NAME_OR_WILDCARD (este último es solo `_`). Para extraer el
texto de un identificador, llamar `name_ctx.getText()`.

### Detección de docstrings

Un string es docstring si es el **primer** statement de un bloque (módulo,
función o clase) Y es solo un string literal (no asignado a nada).

El `CommentRemover` recorre el AST buscando `File_inputContext`,
`Function_def_rawContext` y `Class_def_rawContext`, examina el primer
`simple_stmt` del bloque correspondiente, y si su texto luce como un string
literal (con prefijos opcionales `r/b/u/f`) lo elimina junto con su línea
completa (whitespace de indentación + STRING + NEWLINE).

### Métodos de clase no se renombran

Los `def` definidos dentro de un `class_def` son métodos: se acceden vía
`obj.metodo` y el atributo no se renombra. Por lo tanto, **el nombre del
método tampoco se debe renombrar** (de lo contrario, la llamada `obj.metodo`
no encontraría el método).

El `SymbolCollectorVisitor` lleva un contador `_class_depth` que se
incrementa al entrar en `visitClass_def_raw` y se decrementa al salir. Si
está en `> 0` cuando se visita `function_def_raw`, el nombre de la función
no se añade a la `SymbolTable` (pero los parámetros sí se añaden).

### Strings que NO se cifran

- F-strings: en la gramática Python 3.13 son tokens `FSTRING_START`,
  `FSTRING_MIDDLE`, `FSTRING_END`, no `STRING`. El `StringCipher` solo
  busca tokens `STRING`, así que los f-strings quedan automáticamente
  excluidos.
- Raw strings (`r"..."`) y byte strings (`b"..."`): sí son tokens `STRING`
  pero el `StringCipher` los detecta por su prefijo y los salta.

## Estructura de carpetas

```
codeshield/
├── grammar/                  # gramática original (.g4) y base del lexer
├── generated/                # parser generado por ANTLR (regenerable)
├── src/
│   ├── main.py               # CLI entry point
│   ├── obfuscator.py         # orquestador del pipeline
│   ├── deobfuscator.py       # pipeline inverso (string + ident restore)
│   ├── symbol_table.py       # mapping original → ofuscado
│   ├── protected_names.py    # built-ins, keywords, dunders, etc.
│   ├── visitors/
│   │   └── symbol_collector.py
│   ├── transformations/
│   │   ├── rename_transformer.py
│   │   ├── comment_remover.py
│   │   ├── string_cipher.py
│   │   └── dead_code_inserter.py
│   ├── stats/
│   │   └── obfuscation_stats.py
│   └── viewer/
│       └── html_viewer.py
├── examples/
│   ├── input/                # 4 archivos de ejemplo
│   └── output/               # outputs ya procesados
└── tests/
    ├── test_parser.py
    ├── test_symbol_table.py
    ├── test_protected_names.py
    ├── test_rename.py
    ├── test_comment_remover.py
    ├── test_string_cipher.py
    ├── test_deobfuscator.py
    └── test_end_to_end.py    # tests de invariancia (los más importantes)
```

## Criterio principal de corrección

**El código ofuscado debe ejecutar idéntico al original** (mismo stdout,
mismo exit code, mismos efectos secundarios observables). El test
`test_obfuscation_preserves_behavior` formaliza este criterio.
