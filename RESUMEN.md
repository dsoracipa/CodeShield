# CodeShield — Resumen de implementación

> Documento de cierre del proyecto. Mapea lo construido contra la
> especificación (`Code_Shiel_Spec.md`) y enumera lo que aún falta para
> entrega final.

---

## 1. Estado general

- **47/47 tests automáticos pasan** (`pytest tests/`).
- Los **4 ejemplos** del spec producen output idéntico al original
  después de ofuscar (test de invariancia, criterio principal de la
  especificación).
- Round-trip (ofuscar → deofuscar → ejecutar) preserva semántica para
  los 4 ejemplos.
- CLI completo (`obfuscate` / `deobfuscate`) con todos los flags del
  spec.
- Visor HTML con comparativa lado a lado generado para los 4 ejemplos.

---

## 2. Lo implementado por fase

Las fases siguen el orden recomendado en la sección 18 del spec.

### Fase 1 — Base estructural ✅
- Estructura de carpetas según sección 6 del spec.
- `requirements.txt`, `.gitignore`, `run.bat`, `deobfuscate.bat`,
  `generate_parser.bat`.

### Fase 2 — ANTLR y gramática ✅
- Gramática **Python 3.13** descargada de
  [`grammars-v4/python/python3_13`](https://github.com/antlr/grammars-v4/tree/master/python/python3_13)
  (el spec referenciaba `python3_12_1`, que ya no existe en el repo).
- Parser regenerado con ANTLR 4.13.1 en `generated/`.
- `tests/test_parser.py` con 4 smoke tests pasando.

### Fase 3 — Tabla de símbolos y visitor ✅
- `src/symbol_table.py`: mapping global con prefijos por tipo
  (`_v`, `_f`, `_C`, `_p`).
- `src/protected_names.py`: built-ins, excepciones, constantes,
  dunders, keywords.
- `src/visitors/symbol_collector.py`: recolecta funciones, clases,
  parámetros, variables (asignaciones, `for`, `with`, `except`,
  comprehensions, `lambda`, walrus, augmented assignment), imports.

### Fase 4 — Renombrado ✅
- `src/transformations/rename_transformer.py`: scan de tokens NAME /
  NAME_OR_TYPE / NAME_OR_MATCH / NAME_OR_CASE, con regla del punto
  para no tocar atributos.

### Fase 5 — Comentarios y docstrings ✅
- `src/transformations/comment_remover.py`: elimina tokens COMMENT
  del canal HIDDEN y docstrings (primer string-stmt del bloque).
- Borra la línea completa del docstring (WS de indentación incluida)
  para no romper la indentación del resto del bloque.

### Fase 6 — Cifrado de strings ✅
- `src/transformations/string_cipher.py`: codifica STRING en Base64
  con decodificación inline. F-strings (token FSTRING_*) quedan
  automáticamente excluidos. R-strings y b-strings se detectan por
  prefijo y se saltan.

### Fase 7 — Deofuscador ✅
- `src/deobfuscator.py`: restaura strings con regex
  (`__import__("base64")...`), luego identificadores con `\b` word
  boundaries en orden descendente de longitud.

### Fase 8 — Dead code ✅
- `src/transformations/dead_code_inserter.py`: inserta sentencias
  inofensivas (`_codeshield_dc_N = None`, `(lambda: None)()`, etc.)
  antes de statements top-level con probabilidad `--dead-code-density`
  (default 0.3). Reproducible vía `--dead-code-seed`.

### Fase 9 — Visor HTML ✅
- `src/viewer/html_viewer.py`: tema oscuro, 4 stat cards,
  comparativa side-by-side con highlight.js (CDN), tabla de símbolos
  al pie.
- `src/stats/obfuscation_stats.py`: contadores recolectados a lo
  largo del pipeline.

### Fase 10 — Documentación ✅
- `docs/README.txt` (manual de usuario completo).
- `docs/ARQUITECTURA.md` (decisiones de diseño internas).

---

## 3. Validación contra criterios del spec (sección 17)

### Funcionales

| Criterio | Estado |
|---|---|
| `generate_parser.bat` ejecuta sin errores | ✅ |
| `tests/test_parser.py` pasa | ✅ 4/4 |
| `tests/test_symbol_table.py` pasa | ✅ 5/5 |
| `tests/test_rename.py` pasa | ✅ 8/8 |
| `tests/test_comment_remover.py` pasa | ✅ 5/5 |
| `tests/test_string_cipher.py` pasa | ✅ 6/6 |
| `tests/test_deobfuscator.py` pasa | ✅ 2/2 |
| `tests/test_end_to_end.py` pasa (invariancia, **el más importante**) | ✅ 9/9 |
| CLI `obfuscate` funciona con los 4 ejemplos | ✅ |
| CLI `deobfuscate` funciona con los archivos generados | ✅ |
| `--html` genera HTML válido | ✅ |
| Cada flag de desactivación funciona individualmente | ✅ |

### No funcionales

| Criterio | Estado |
|---|---|
| Type hints en funciones públicas | ✅ |
| Docstring en cada módulo | ✅ |
| Sin rutas absolutas hardcoded | ✅ |
| `README.txt` completo y funcional | ✅ |
| `pip install -r requirements.txt` deja el proyecto listo | ✅ |

### Estructurales

| Criterio | Estado |
|---|---|
| Estructura coincide con sección 6 del spec | ✅ |
| `.gitignore` presente | ✅ |
| `requirements.txt` con solo `antlr4-python3-runtime==4.13.1` | ✅ |

**Bonus** (no exigido por el spec): `tests/test_protected_names.py`
con 8 tests adicionales sobre la lista de identificadores protegidos.

---

## 4. Decisiones que difieren del spec (todas justificadas)

### 4.1 Gramática Python 3.13 en lugar de 3.12.1

El spec referencia `python/python3_12_1` del repo `antlr/grammars-v4`,
pero ese directorio fue eliminado/renombrado. La versión actual es
`python/python3_13`. Cambios derivados:

- Reglas: `function_def_raw`, `class_def_raw`, `assignment`,
  `except_block`, `for_if_clause` (en lugar de `funcdef`, `classdef`,
  `expr_stmt`, `except_clause`).
- La regla `name` envuelve los tokens NAME / NAME_OR_TYPE /
  NAME_OR_MATCH / NAME_OR_CASE / NAME_OR_WILDCARD. Para extraer el
  texto de un identificador hay que llamar `name_ctx.getText()`.
- F-strings son tokens separados (FSTRING_START/MIDDLE/END), no tokens
  STRING — quedan excluidos del cifrado automáticamente.

### 4.2 Métodos de clase NO se renombran

El spec dice "renombrar funciones definidas por el usuario" (F3) pero
también dice "atributos accedidos vía `.` no se renombran" (regla en
sección 9, ejemplo 13.3). Si renombramos `def metodo(self)` pero no
renombramos `obj.metodo(...)`, se rompe el `AttributeError`.

**Solución implementada:** el `SymbolCollectorVisitor` lleva un contador
`_class_depth`. Si está `> 0` cuando se visita una `function_def`, no
añade el nombre a la `SymbolTable` (pero los parámetros sí). El test
`test_method_not_renamed` cubre esto.

### 4.3 Tokens sintéticos del LexerBase

El `PythonLexerBase` inyecta tokens `ENCODING`, `INDENT` y `DEDENT` con
texto `"utf-8"`, `"<INDENT>"` y `"<DEDENT>"` respectivamente. El spec
no menciona esto. Estos tokens deben tener su `.text` limpiado a
cadena vacía **después** de `tokenStream.fill()` y **antes** de
cualquier `replaceSingleToken()`, o el `getDefaultText()` los emite
literalmente y rompe la sintaxis.

Implementado en `Obfuscator._parse()`.

### 4.4 Eliminación de docstrings borra la línea completa

El spec sugiere eliminar el rango de tokens del docstring. Eso deja la
indentación WS de la línea como huérfana, lo que produce indentación
incorrecta (8 espacios en lugar de 4) en el siguiente statement.

**Solución implementada:** al detectar un docstring, expandir el rango
de eliminación hacia atrás (WS tokens del canal HIDDEN) y hacia
adelante (NEWLINE final) antes de llamar a `rewriter.delete`.

### 4.5 Heurística de kwargs eliminada

El spec no menciona kwargs. Una primera implementación intentó saltar
`name=value` dentro de paréntesis (kwargs externos), pero esto rompía
`03_realistic.py` (`imprimir_reporte(inv, umbral_bajo=5)` — `umbral_bajo`
es param renombrado y debe renombrarse también en el call site).

**Solución final:** seguir la regla del spec al pie de la letra y
documentar como limitación que un nombre de variable de usuario que
coincida con un kwarg externo (p.ej. `end` para `print(end=...)`) puede
colisionar.

---

## 5. Próximos pasos para entrega final

### 5.1 Crear la presentación (`docs/presentacion.pdf`) — **PENDIENTE**

El spec sección 19 exige un PDF de 10–12 slides:

1. Título y autores
2. Motivación y justificación del problema
3. Antecedentes y trabajos relacionados (pyarmor, pyminifier, papers
   de Collberg)
4. Objetivo del trabajo
5. Propuesta (diagrama de arquitectura de la sección 8 del spec)
6. Stack técnico (ANTLR + Python + Visitor + TokenStreamRewriter)
7. Detalle de las 4 transformaciones
8. Demo (transición a vivo)
9. Pruebas y validación (los tests de invariancia + 4 ejemplos)
10. Conclusiones (qué se logró, limitaciones, trabajos futuros)
11. Referencias
12. Preguntas

Sugerencia: usar Google Slides / PowerPoint / LaTeX Beamer. El material
de la sección 8 del spec y `docs/ARQUITECTURA.md` ya tiene la mayoría
del contenido técnico.

### 5.2 Limpiar artefactos antes de empaquetar

Antes del ZIP final, ejecutar:

```powershell
# Borrar caches de Python
Get-ChildItem -Path . -Include __pycache__ -Recurse -Force `
  | Remove-Item -Recurse -Force

# Borrar caches de pytest
Remove-Item -Recurse -Force .pytest_cache -ErrorAction SilentlyContinue

# Borrar archivos intermedios de ANTLR (.interp, .tokens)
Remove-Item generated\*.interp, generated\*.tokens
```

Ahora mismo `generated/` contiene `.interp` y `.tokens` que el spec
20.10 dice excluir.

### 5.3 Empaquetar el ZIP

Según spec sección 19:

```
CodeShield_<usuario1>_<usuario2>.zip
└── CodeShield_<usuario1>_<usuario2>/
    ├── grammar/
    ├── generated/                  # parser pre-generado (limpio de .interp/.tokens)
    ├── src/
    ├── examples/
    │   ├── input/
    │   └── output/                 # ya generado ✓
    ├── tests/
    ├── docs/
    │   ├── README.txt              ✓
    │   ├── ARQUITECTURA.md         ✓
    │   └── presentacion.pdf        ❌ FALTA
    ├── requirements.txt
    ├── generate_parser.bat
    ├── run.bat
    ├── deobfuscate.bat
    └── .gitignore
```

El ZIP **no debe incluir**: `venv/`, `__pycache__/`, `.pytest_cache/`,
`.vscode/`, `.idea/`, archivos `.interp` / `.tokens`.

### 5.4 (Opcional) Mejorar el demo en vivo

El spec sugiere un demo de 3 minutos. Los 4 ejemplos en
`examples/output/` ya están listos:

1. `python examples/input/01_simple.py` → mostrar output.
2. `run.bat examples/input/01_simple.py --html` → abrir el HTML.
3. `python examples/output/01_simple_obfuscated.py` → mismo output.
4. `deobfuscate.bat examples/output/01_simple_obfuscated.py -m examples/output/01_simple_symbol_map.json` → restaurar.
5. Mostrar `examples/output/04_advanced_obfuscated.py` para impacto visual.

---

## 6. Comandos clave para verificación

### Correr todos los tests
```powershell
cd C:\Users\DANIEL\Documents\UNI\sem 9\lenguajes\proyecto
python -m pytest tests/ -v
```

### Reproducir invariancia manualmente
```powershell
python -m src.main obfuscate examples\input\01_simple.py --html
python examples\input\01_simple.py
python examples\input\01_simple_obfuscated.py
# (deben imprimir el mismo output)
```

### Regenerar el parser (si se modifican los .g4)
```powershell
.\generate_parser.bat
```

---

## 7. Métricas finales

| Métrica | Valor |
|---|---|
| Líneas de código Python (src/) | ~1200 |
| Módulos en `src/` | 12 |
| Tests automáticos | 47 |
| Tests pasando | 47 |
| Ejemplos pasando invariancia | 4 / 4 |
| Ejemplos pasando round-trip | 4 / 4 |
| Tiempo de pipeline completo (4 ejemplos) | ~5 segundos |

---

## 8. Lo que está 100% según spec (sin tocar)

- F1–F13 del alcance funcional (todas implementadas).
- Pipeline de 5 etapas + dead code opcional.
- Pipeline inverso con limitaciones documentadas.
- 13 edge cases de la sección 13 cubiertos en tests / docs.
- CLI según sección 14 (todos los flags).
- HTML viewer según sección 15 (tema oscuro, 4 stat cards, comparativa
  side-by-side, tabla de símbolos).
- Casos de prueba según sección 16.
- Notas críticas sección 20 atendidas (encoding utf-8 explícito,
  re-tokenización entre pasos, FailFastErrorListener, etc.).

---

**Conclusión:** el proyecto está **funcionalmente completo** y supera
todos los criterios de validación del spec. Lo único que queda para
entrega es generar `docs/presentacion.pdf` y empaquetar el ZIP.
