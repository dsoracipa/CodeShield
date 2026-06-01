# CodeShield — Especificación Técnica de Implementación

> Aplicación de análisis y manipulación automática de código fuente Python construida sobre ANTLR v4.
> Este documento es la especificación completa que debe seguirse para construir la aplicación de principio a fin.

---

## Índice

1. [Visión general y objetivo](#1-visión-general-y-objetivo)
2. [Caso de uso real](#2-caso-de-uso-real)
3. [Alcance funcional](#3-alcance-funcional)
4. [Decisiones técnicas](#4-decisiones-técnicas)
5. [Entorno y dependencias](#5-entorno-y-dependencias)
6. [Estructura del proyecto](#6-estructura-del-proyecto)
7. [Setup de ANTLR y gramática](#7-setup-de-antlr-y-gramática)
8. [Arquitectura de la solución](#8-arquitectura-de-la-solución)
9. [Identificadores protegidos](#9-identificadores-protegidos)
10. [Especificación de módulos](#10-especificación-de-módulos)
11. [Pipeline de ofuscación](#11-pipeline-de-ofuscación)
12. [Pipeline de deofuscación](#12-pipeline-de-deofuscación)
13. [Edge cases críticos](#13-edge-cases-críticos)
14. [Especificación del CLI](#14-especificación-del-cli)
15. [Especificación del visor HTML](#15-especificación-del-visor-html)
16. [Casos de prueba](#16-casos-de-prueba)
17. [Criterios de validación](#17-criterios-de-validación)
18. [Orden de implementación recomendado](#18-orden-de-implementación-recomendado)
19. [Entregables finales](#19-entregables-finales)
20. [Notas críticas para la implementación](#20-notas-críticas-para-la-implementación)

---

## 1. Visión general y objetivo

**Nombre:** CodeShield — Ofuscador y Deofuscador de Código Fuente Python

**Objetivo técnico:** construir una aplicación de línea de comandos en Python que, usando un parser generado con ANTLR v4 sobre la gramática oficial de Python 3, transforme archivos `.py` legibles en versiones funcionalmente equivalentes pero deliberadamente ilegibles, y que permita revertir esa transformación mediante un mapa de símbolos generado durante la ofuscación.

**Restricción de invariancia:** el código ofuscado **debe ejecutar idénticamente** al original (mismo comportamiento observable, mismo output en stdout, mismas excepciones, mismos efectos secundarios). Esta es la propiedad central que valida la corrección de toda la herramienta.

---

## 2. Caso de uso real

Empresas y desarrolladores que distribuyen scripts o herramientas Python a clientes, contratistas o usuarios finales donde:

- No se quiere ceder la legibilidad de la lógica de negocio (algoritmos propietarios, fórmulas, reglas).
- La compilación a bytecode no es opción (el usuario necesita poder ejecutar como `.py`).
- Se necesita un mecanismo de protección reversible internamente (el desarrollador conserva el `symbol_map.json` y puede deofuscar cuando lo necesite).

Ejemplos concretos: scripts de automatización de procesos vendidos a empresas, algoritmos de trading distribuidos como Python, herramientas SaaS entregadas como código fuente, lógica de evaluación en plataformas educativas.

---

## 3. Alcance funcional

### Funcionalidades incluidas

| ID | Funcionalidad | Categoría |
|---|---|---|
| F1 | Parser de Python 3 generado con ANTLR v4 | Análisis |
| F2 | Renombrado de variables locales y globales | Manipulación |
| F3 | Renombrado de funciones definidas por el usuario | Manipulación |
| F4 | Renombrado de parámetros de funciones | Manipulación |
| F5 | Renombrado de clases definidas por el usuario | Manipulación |
| F6 | Eliminación de comentarios `#` | Manipulación |
| F7 | Eliminación de docstrings `"""..."""` y `'''...'''` | Manipulación |
| F8 | Cifrado de string literals con Base64 + decodificación inline | Manipulación |
| F9 | Inserción de código muerto inofensivo en puntos seguros | Manipulación |
| F10 | Generación de `symbol_map.json` con la tabla de correspondencias | Análisis |
| F11 | Deofuscador que aplica el mapa para revertir el código | Manipulación |
| F12 | CLI completo con subcomandos y flags configurables | Interfaz |
| F13 | Visor HTML con comparativa lado a lado del código original y el ofuscado | Demo |

### Funcionalidades excluidas (no implementar)

- **Aplanamiento de control de flujo** (convertir `if/else` en switches opacos con predicados booleanos). Es factible pero requiere análisis de flujo de datos no trivial.
- **Deofuscación por heurística sin mapa.** Solo se soporta deofuscación con `symbol_map.json` disponible.
- **Ofuscación de archivos `.pyc` (bytecode).** Esta herramienta opera exclusivamente sobre código fuente.
- **Soporte de Python 2.x.** Solo Python 3.
- **Resolución de imports entre múltiples archivos del mismo proyecto.** Cada archivo se ofusca de forma independiente.
- **Type-checking del código ofuscado.** No verificamos que el código original sea válido más allá de que el parser de ANTLR lo acepte.

---

## 4. Decisiones técnicas

| Decisión | Elección | Justificación |
|---|---|---|
| Lenguaje de implementación | Python 3.10+ | Mismo lenguaje del código a transformar; integración natural con el runtime Python de ANTLR. |
| Versión de ANTLR | 4.13.1 | Última versión estable con soporte completo del target Python 3. |
| Gramática | `python3_12_1` de [antlr/grammars-v4](https://github.com/antlr/grammars-v4/tree/master/python/python3_12_1) | Mantenida oficialmente, probada en producción, maneja correctamente INDENT/DEDENT mediante `Python3LexerBase`. |
| Estrategia de transformación | Visitor para análisis + `TokenStreamRewriter` para mutación | Visitor cumple el requisito del proyecto. `TokenStreamRewriter` preserva todo lo no modificado (espacios, formato, código no tocado) sin necesidad de reconstruir el código desde el AST. |
| Modelo de scopes | Mapping global (un nombre original → un único nombre ofuscado en todo el archivo) | Simplifica la implementación, garantiza corrección (mismo nombre se reemplaza igual en todas partes), suficiente para el caso de uso. Variables con el mismo nombre en distintas funciones reciben el mismo identificador ofuscado, lo cual es válido porque preserva la semántica del scope original. |
| Formato del mapa de símbolos | JSON con metadatos (tipo, contador) | Legible, estándar, fácil de versionar y procesar. |
| Codificación de strings | Base64 con decodificación `__import__("base64").b64decode("...").decode("utf-8")` | Reversible mecánicamente, no requiere imports adicionales en el código ofuscado, suficiente para ofuscación visual. |
| Sistema operativo target | Windows (compatible cross-platform) | Plataforma del usuario; el código Python en sí es portable. |
| Demo visual | HTML estático con `highlight.js` vía CDN | No requiere servidor, se abre en cualquier navegador, syntax highlighting de calidad sin dependencias locales. |

### Por qué Visitor + TokenStreamRewriter (y no Visitor puro)

ANTLR provee dos enfoques para transformar código:

1. **Visitor puro reconstructivo:** recorre el AST y reconstruye el código desde cero. Problema: hay que manejar explícitamente cada tipo de nodo de la gramática (Python tiene >100 reglas), y se pierden todos los tokens del canal `HIDDEN` (espacios y comentarios) salvo que se manejen manualmente.

2. **`TokenStreamRewriter`:** opera sobre el stream de tokens directamente, haciendo reemplazos, inserciones y eliminaciones quirúrgicas. Todo lo que no se modifica se preserva exactamente igual.

**El enfoque correcto es híbrido:** usar un Visitor para *identificar* qué transformar (qué identificadores renombrar, qué strings cifrar) y aplicar los cambios a través del `TokenStreamRewriter`. Esto cumple el requisito académico de usar el patrón Visitor y produce código de salida limpio.

---

## 5. Entorno y dependencias

### Software requerido

| Software | Versión mínima | Uso |
|---|---|---|
| Python | 3.10 | Runtime de la aplicación |
| Java JDK | 11 | Solo para ejecutar la herramienta ANTLR y regenerar el parser |
| ANTLR complete JAR | 4.13.1 | Solo para regenerar el parser desde los `.g4` |

Java y el JAR de ANTLR **solo son necesarios para regenerar el parser**. Una vez que el parser está generado en `/generated`, la aplicación corre solo con Python.

### `requirements.txt`

```
antlr4-python3-runtime==4.13.1
```

Esta es la única dependencia externa. Todo lo demás (`json`, `base64`, `argparse`, `pathlib`, `re`, `random`, `string`, `html`, `subprocess`, `tempfile`) es Python stdlib.

### Instalación (en Windows)

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

---

## 6. Estructura del proyecto

```
codeshield/
├── grammar/
│   ├── Python3Lexer.g4              # gramática del lexer (descargada de grammars-v4)
│   ├── Python3Parser.g4             # gramática del parser
│   └── Python3LexerBase.py          # base class con lógica de INDENT/DEDENT
│
├── generated/                       # archivos generados por ANTLR (regenerables)
│   ├── Python3Lexer.py
│   ├── Python3Parser.py
│   ├── Python3Visitor.py
│   ├── Python3Listener.py
│   ├── Python3LexerBase.py          # copia del archivo de grammar/
│   └── __init__.py
│
├── src/
│   ├── __init__.py
│   ├── main.py                      # entry point del CLI
│   ├── obfuscator.py                # orquestador del pipeline de ofuscación
│   ├── deobfuscator.py              # orquestador del pipeline inverso
│   ├── symbol_table.py              # tabla de símbolos
│   ├── protected_names.py           # lista de identificadores protegidos
│   │
│   ├── visitors/
│   │   ├── __init__.py
│   │   └── symbol_collector.py      # Visitor que identifica renombrables
│   │
│   ├── transformations/
│   │   ├── __init__.py
│   │   ├── rename_transformer.py
│   │   ├── comment_remover.py
│   │   ├── string_cipher.py
│   │   └── dead_code_inserter.py
│   │
│   ├── stats/
│   │   ├── __init__.py
│   │   └── obfuscation_stats.py     # contadores para el HTML viewer
│   │
│   └── viewer/
│       ├── __init__.py
│       └── html_viewer.py
│
├── examples/
│   ├── input/
│   │   ├── 01_simple.py             # función básica + variables
│   │   ├── 02_classes.py            # clases, métodos, herencia simple
│   │   ├── 03_realistic.py          # programa con I/O, strings, condicionales
│   │   └── 04_advanced.py           # comprehensions, lambdas, decoradores
│   └── output/                      # se llena al ejecutar (vacío en el ZIP)
│
├── tests/
│   ├── __init__.py
│   ├── test_parser.py               # smoke test del parser
│   ├── test_symbol_table.py
│   ├── test_protected_names.py
│   ├── test_rename.py
│   ├── test_comment_remover.py
│   ├── test_string_cipher.py
│   ├── test_deobfuscator.py
│   └── test_end_to_end.py           # tests de invariancia (mismo output)
│
├── docs/
│   ├── README.txt                   # manual de uso (requisito del proyecto)
│   └── ARQUITECTURA.md              # documento técnico interno
│
├── requirements.txt
├── generate_parser.bat              # regenera el parser ANTLR
├── run.bat                          # atajo: python -m src.main obfuscate
├── deobfuscate.bat                  # atajo: python -m src.main deobfuscate
└── .gitignore
```

### `.gitignore`

```
__pycache__/
*.pyc
*.pyo
venv/
.venv/
*.tokens
*.interp
examples/output/
.pytest_cache/
.vscode/
.idea/
```

---

## 7. Setup de ANTLR y gramática

### 7.1 Obtención de los archivos `.g4`

Descargar de https://github.com/antlr/grammars-v4/tree/master/python/python3_12_1 los siguientes archivos y colocarlos en `grammar/`:

- `Python3Lexer.g4`
- `Python3Parser.g4`
- `Python3LexerBase.py`

> El archivo `Python3LexerBase.py` es **crítico**: contiene la lógica que emite los tokens `INDENT` y `DEDENT` al detectar cambios en la indentación. Sin él, el lexer no compila.

### 7.2 Script `generate_parser.bat`

```batch
@echo off
setlocal
set ANTLR_JAR=C:\antlr\antlr-4.13.1-complete.jar

if not exist %ANTLR_JAR% (
    echo ERROR: no se encuentra %ANTLR_JAR%
    echo Descargar de https://www.antlr.org/download/antlr-4.13.1-complete.jar
    exit /b 1
)

echo Generando parser ANTLR para Python 3...
cd grammar
java -jar %ANTLR_JAR% -Dlanguage=Python3 -visitor -listener -o ..\generated Python3Lexer.g4 Python3Parser.g4

if errorlevel 1 (
    echo ERROR: generacion fallida
    cd ..
    exit /b 1
)

cd ..
copy grammar\Python3LexerBase.py generated\Python3LexerBase.py >nul

REM Crear __init__.py vacio para que generated sea un paquete
echo. > generated\__init__.py

echo OK. Parser generado en /generated
endlocal
```

### 7.3 Flags relevantes

- `-Dlanguage=Python3`: genera código Python (no Java por defecto).
- `-visitor`: genera la clase base `Python3Visitor` (necesaria).
- `-listener`: genera el Listener (no lo usamos, pero se mantiene para compatibilidad).
- `-o ../generated`: directorio de salida.

### 7.4 Smoke test obligatorio (`tests/test_parser.py`)

```python
"""Verifica que el parser ANTLR generado funciona correctamente."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'generated'))

from antlr4 import InputStream, CommonTokenStream
from Python3Lexer import Python3Lexer
from Python3Parser import Python3Parser


def test_parse_simple_assignment():
    code = "x = 42\nprint(x)\n"
    stream = InputStream(code)
    lexer = Python3Lexer(stream)
    tokens = CommonTokenStream(lexer)
    parser = Python3Parser(tokens)
    tree = parser.file_input()
    assert tree is not None


def test_parse_function_def():
    code = "def add(a, b):\n    return a + b\n"
    stream = InputStream(code)
    lexer = Python3Lexer(stream)
    tokens = CommonTokenStream(lexer)
    parser = Python3Parser(tokens)
    tree = parser.file_input()
    assert tree is not None


def test_parse_class():
    code = "class A:\n    def m(self):\n        pass\n"
    stream = InputStream(code)
    lexer = Python3Lexer(stream)
    tokens = CommonTokenStream(lexer)
    parser = Python3Parser(tokens)
    tree = parser.file_input()
    assert tree is not None


if __name__ == '__main__':
    test_parse_simple_assignment()
    test_parse_function_def()
    test_parse_class()
    print("Parser OK")
```

Este test debe pasar antes de implementar cualquier otra cosa. Es el indicador de que el setup de ANTLR está correcto.

---

## 8. Arquitectura de la solución

### Diagrama de flujo

```
                   ┌──────────────────┐
                   │  archivo .py     │
                   │  (entrada)       │
                   └────────┬─────────┘
                            │
                            ▼
                ┌────────────────────────┐
                │   Python3Lexer (ANTLR) │
                │   + TokenStream         │
                └────────┬───────────────┘
                            │
                            ▼
                ┌────────────────────────┐
                │   Python3Parser (ANTLR)│
                │   → ParseTree          │
                └────────┬───────────────┘
                            │
                            ▼
              ┌────────────────────────────┐
              │ SymbolCollectorVisitor     │   PASADA 1: análisis
              │  - identifica imports      │
              │  - identifica defs/clases  │
              │  - identifica params       │
              │  - identifica asignaciones │
              │ → SymbolTable + imports    │
              └────────┬───────────────────┘
                            │
                            ▼
              ┌────────────────────────────┐
              │ Pipeline de transformaciones│  PASADA 2..N: mutación
              │ (cada una re-tokeniza)     │
              │                            │
              │  1. RenameTransformer      │
              │  2. CommentRemover         │
              │  3. StringCipher           │
              │  4. DeadCodeInserter       │
              │                            │
              │ (cada transformación usa   │
              │  TokenStreamRewriter)      │
              └────────┬───────────────────┘
                            │
                            ▼
              ┌────────────────────────────┐
              │ Salidas                    │
              │  ├─ archivo_obfuscated.py  │
              │  ├─ symbol_map.json        │
              │  └─ comparison.html (opc.) │
              └────────────────────────────┘
```

### Principios de diseño

1. **Inmutabilidad del análisis:** el `SymbolCollectorVisitor` no muta nada; solo construye la `SymbolTable` y la lista de imports. Esto separa análisis de transformación.

2. **Composabilidad de transformaciones:** cada transformación es una clase con un único método `apply()` que retorna el código transformado. Esto permite encadenarlas en cualquier orden y desactivarlas individualmente con flags del CLI.

3. **Re-tokenización entre etapas:** después de cada transformación se obtiene el código como string y se re-tokeniza para la siguiente. Esto evita estado compartido y bugs sutiles del `TokenStreamRewriter` al aplicar múltiples capas de cambios.

4. **Idempotencia de la deofuscación:** dado el `symbol_map.json`, la deofuscación es determinista y no depende del proceso de ofuscación que la generó.

5. **Fail-fast en validación:** el parser ANTLR debe aceptar el código antes de cualquier transformación. Si el código fuente tiene errores de sintaxis, el proceso se aborta con mensaje claro.

---

## 9. Identificadores protegidos

Hay identificadores que **nunca** deben renombrarse porque al hacerlo se rompe el código.

### Categorías protegidas

1. **Built-ins de Python:** `print`, `len`, `range`, `int`, `str`, etc.
2. **Excepciones del lenguaje:** `Exception`, `ValueError`, `TypeError`, etc.
3. **Constantes del lenguaje:** `True`, `False`, `None`.
4. **Parámetros convencionales:** `self`, `cls`.
5. **Métodos dunder:** `__init__`, `__str__`, `__repr__`, etc. (cualquier `__*__`).
6. **Nombres importados:** todo identificador traído por `import` o `from ... import ...`.
7. **Atributos de objeto:** lo accedido vía `objeto.atributo` no se renombra (porque sería romper APIs externas — `dict.keys()`, `str.upper()`, etc.).

### Implementación de `src/protected_names.py`

```python
"""Identificadores que nunca deben ser renombrados por el ofuscador."""

PYTHON_BUILTINS = {
    # tipos
    'int', 'str', 'float', 'bool', 'list', 'dict', 'tuple', 'set',
    'frozenset', 'bytes', 'bytearray', 'complex', 'object', 'type',
    'memoryview', 'range', 'slice',
    # funciones built-in
    'print', 'input', 'len', 'open', 'abs', 'all', 'any', 'min', 'max',
    'sum', 'sorted', 'reversed', 'enumerate', 'zip', 'map', 'filter',
    'iter', 'next', 'round', 'pow', 'divmod', 'hash', 'id', 'repr',
    'format', 'chr', 'ord', 'bin', 'hex', 'oct', 'callable',
    'isinstance', 'issubclass', 'hasattr', 'getattr', 'setattr', 'delattr',
    'vars', 'dir', 'globals', 'locals', 'help', 'exit', 'quit',
    'super', 'property', 'staticmethod', 'classmethod', 'compile',
    'eval', 'exec', 'breakpoint', 'ascii',
    # excepciones built-in
    'BaseException', 'Exception', 'ArithmeticError', 'AssertionError',
    'AttributeError', 'BlockingIOError', 'BrokenPipeError', 'BufferError',
    'BytesWarning', 'ChildProcessError', 'ConnectionAbortedError',
    'ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError',
    'DeprecationWarning', 'EOFError', 'EnvironmentError', 'FileExistsError',
    'FileNotFoundError', 'FloatingPointError', 'FutureWarning',
    'GeneratorExit', 'IOError', 'ImportError', 'ImportWarning',
    'IndentationError', 'IndexError', 'InterruptedError', 'IsADirectoryError',
    'KeyError', 'KeyboardInterrupt', 'LookupError', 'MemoryError',
    'ModuleNotFoundError', 'NameError', 'NotADirectoryError', 'NotImplemented',
    'NotImplementedError', 'OSError', 'OverflowError', 'PendingDeprecationWarning',
    'PermissionError', 'ProcessLookupError', 'RecursionError', 'ReferenceError',
    'ResourceWarning', 'RuntimeError', 'RuntimeWarning', 'StopAsyncIteration',
    'StopIteration', 'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit',
    'TabError', 'TimeoutError', 'TypeError', 'UnboundLocalError',
    'UnicodeDecodeError', 'UnicodeEncodeError', 'UnicodeError',
    'UnicodeTranslateError', 'UnicodeWarning', 'UserWarning', 'ValueError',
    'Warning', 'WindowsError', 'ZeroDivisionError',
    # constantes
    'True', 'False', 'None', 'Ellipsis', '__debug__',
    # atributos especiales del módulo
    '__name__', '__main__', '__file__', '__doc__', '__path__', '__package__',
    '__loader__', '__spec__', '__builtins__',
}

CONVENTIONAL_PARAMS = {'self', 'cls'}

# Keywords de Python (no son identificadores pero los excluimos por seguridad)
PYTHON_KEYWORDS = {
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
    'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
    'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
    'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while',
    'with', 'yield', 'match', 'case',
}


def is_dunder(name: str) -> bool:
    """True si el nombre es de la forma __nombre__."""
    return name.startswith('__') and name.endswith('__') and len(name) > 4


def is_protected(name: str) -> bool:
    """True si el identificador no debe ser renombrado."""
    if name in PYTHON_BUILTINS:
        return True
    if name in CONVENTIONAL_PARAMS:
        return True
    if name in PYTHON_KEYWORDS:
        return True
    if is_dunder(name):
        return True
    return False
```

---

## 10. Especificación de módulos

Cada módulo se describe con: propósito, interface pública, código de referencia y casos a manejar.

### 10.1 `src/symbol_table.py`

**Propósito:** mantener un mapping global de identificadores originales a identificadores ofuscados, con metadatos del tipo (variable, función, clase, parámetro).

**Decisión clave:** se usa **mapping global** (no por scope). Esto significa que si un usuario tiene una variable `total` en una función y otra `total` en otra función, ambas reciben el mismo nombre ofuscado. Esto es correcto porque preserva la semántica: nombres iguales en Python son la misma referencia léxica solo si están en el mismo scope, y al ofuscar todos los `total` igual, los scopes siguen siendo independientes (cada función sigue teniendo su `total` local).

**Interface:**

```python
from dataclasses import dataclass

@dataclass
class Symbol:
    original: str
    obfuscated: str
    kind: str  # 'variable' | 'function' | 'class' | 'parameter'

class SymbolTable:
    def add(self, original: str, kind: str) -> Symbol: ...
    def get(self, original: str) -> Symbol | None: ...
    def has(self, original: str) -> bool: ...
    def all_symbols(self) -> list[Symbol]: ...
    def to_dict(self) -> dict: ...

    @classmethod
    def from_dict(cls, data: dict) -> 'SymbolTable': ...
```

**Código completo:**

```python
"""Tabla de símbolos con mapping global original → ofuscado."""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass(frozen=True)
class Symbol:
    original: str
    obfuscated: str
    kind: str  # 'variable', 'function', 'class', 'parameter'


# Prefijos por tipo (visible en el codigo ofuscado para debugging)
PREFIX_BY_KIND = {
    'variable': '_v',
    'function': '_f',
    'class': '_C',
    'parameter': '_p',
}


class SymbolTable:
    def __init__(self):
        self._symbols: dict[str, Symbol] = {}
        self._counter: int = 0

    def _generate_obfuscated_name(self, kind: str) -> str:
        prefix = PREFIX_BY_KIND.get(kind, '_x')
        name = f"{prefix}{self._counter:04x}"
        self._counter += 1
        return name

    def add(self, original: str, kind: str) -> Symbol:
        """Añade un símbolo. Si ya existe (con el mismo nombre), devuelve el existente.

        Si existe con tipo distinto (ej. era 'variable' y ahora se ve como 'function'),
        prevalece el primero — esto es la regla de 'first wins'.
        """
        if original in self._symbols:
            return self._symbols[original]
        obfuscated = self._generate_obfuscated_name(kind)
        sym = Symbol(original=original, obfuscated=obfuscated, kind=kind)
        self._symbols[original] = sym
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
        return st
```

### 10.2 `src/visitors/symbol_collector.py`

**Propósito:** recorrer el ParseTree y poblar la `SymbolTable` con todos los identificadores renombrables. También detecta los nombres importados (para excluirlos del renombrado).

**Reglas de recolección:**

- `def nombre(...)`: añadir `nombre` como `function`. Añadir cada parámetro como `parameter`.
- `class Nombre(...)`: añadir `Nombre` como `class`.
- Asignación `x = ...`: añadir `x` como `variable`. Para asignaciones múltiples `a, b = ...`, añadir cada nombre del LHS.
- `for x in ...`: añadir `x` como `variable`.
- `with ... as x:`: añadir `x` como `variable`.
- `except ... as x:`: añadir `x` como `variable`.
- `import foo`: añadir `foo` a la lista de imports (NO renombrar).
- `import foo as bar`: añadir `bar` a la lista de imports.
- `from foo import bar`: añadir `bar` a la lista de imports.
- `from foo import bar as baz`: añadir `baz` a la lista de imports.
- `lambda x, y: ...`: añadir `x` e `y` como `parameter`.
- Comprehensions (`[x for x in ...]`): añadir `x` como `variable`.

**Reglas de exclusión (no se añaden a la tabla):**

- Cualquier nombre que sea `is_protected(name) == True`.
- Cualquier nombre que esté en la lista de imports.
- Atributos accedidos vía `.` (ej. `obj.metodo` — `metodo` no se renombra).

**Patrón de implementación:**

El Visitor extiende `Python3ParserVisitor`. Para Python 3.12.1, los nombres de las reglas relevantes en la gramática son:

- `funcdef` o `function_def` (verificar en el `.g4` real)
- `classdef` o `class_def`
- `assignment` o `expr_stmt`
- `import_name`, `import_from`
- `for_stmt`, `with_stmt`, `try_stmt`
- `lambdef`

> **Importante:** los nombres exactos de las reglas pueden variar entre versiones de la gramática. **Antes de implementar el Visitor, abrir `grammar/Python3Parser.g4` y verificar los nombres reales de las reglas.** Si la implementación no detecta funciones, casi siempre es porque el nombre de la regla en la gramática no es exactamente `funcdef`.

**Esqueleto:**

```python
"""Primera pasada: recolecta identificadores que deben renombrarse."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'generated'))

from Python3ParserVisitor import Python3ParserVisitor
from Python3Parser import Python3Parser

from src.symbol_table import SymbolTable
from src.protected_names import is_protected


class SymbolCollectorVisitor(Python3ParserVisitor):
    def __init__(self):
        self.symbols = SymbolTable()
        self.imports: set[str] = set()

    # ---- imports ----
    def visitImport_name(self, ctx):
        """import foo, bar.baz [as x]"""
        # Iterar sobre dotted_as_names → dotted_as_name
        # Para 'foo.bar': el nombre top-level es 'foo'
        # Para 'foo as x': solo 'x' queda accesible
        for child in ctx.dotted_as_names().dotted_as_name():
            if child.NAME():  # 'as ALIAS'
                self.imports.add(child.NAME().getText())
            else:
                top = child.dotted_name().NAME(0).getText()
                self.imports.add(top)
        return None

    def visitImport_from(self, ctx):
        """from foo import a, b as c"""
        # Si tiene import_as_names, iterar
        import_as_names = ctx.import_as_names()
        if import_as_names:
            for item in import_as_names.import_as_name():
                names = item.NAME()
                # 'X as Y' → usar Y; solo 'X' → usar X
                self.imports.add(names[-1].getText())
        return None

    # ---- definiciones ----
    def visitFuncdef(self, ctx):
        name = ctx.NAME().getText()
        if not is_protected(name) and name not in self.imports:
            self.symbols.add(name, 'function')
        # Recolectar parámetros
        params_ctx = ctx.parameters()
        if params_ctx and params_ctx.typedargslist():
            self._collect_params(params_ctx.typedargslist())
        # Visitar el cuerpo
        return self.visit(ctx.suite()) if ctx.suite() else None

    def _collect_params(self, typedargslist_ctx):
        for tfpdef in typedargslist_ctx.tfpdef():
            param_name = tfpdef.NAME().getText()
            if not is_protected(param_name):
                self.symbols.add(param_name, 'parameter')

    def visitClassdef(self, ctx):
        name = ctx.NAME().getText()
        if not is_protected(name) and name not in self.imports:
            self.symbols.add(name, 'class')
        return self.visit(ctx.suite()) if ctx.suite() else None

    # ---- asignaciones ----
    def visitExpr_stmt(self, ctx):
        """x = ..., x, y = ..., x += ..."""
        # Si tiene un '=' simple (no augmented assignment)
        if ctx.ASSIGN():
            # El LHS es el primer testlist_star_expr
            lhs = ctx.testlist_star_expr(0)
            for name in self._extract_assignment_targets(lhs):
                if not is_protected(name) and name not in self.imports:
                    self.symbols.add(name, 'variable')
        return self.visitChildren(ctx)

    def _extract_assignment_targets(self, lhs_ctx) -> list[str]:
        """Extrae nombres simples del LHS. Ignora atributos (obj.x) y subscripts (a[0])."""
        names = []
        # Recorrer recursivamente buscando 'atom' nodes que sean solo NAME
        # sin trailers (.x, [0], (...))
        # Implementación detallada en función auxiliar abajo
        return self._walk_for_simple_names(lhs_ctx)

    def _walk_for_simple_names(self, ctx) -> list[str]:
        """
        Heurística: recorre el subárbol buscando tokens NAME que estén dentro
        de un atom_expr SIN trailer. Si hay '.algo' o '[algo]' es atributo/subscript
        y NO se considera asignación de variable simple.
        """
        results = []
        from Python3Parser import Python3Parser as P
        # NOTA: el código exacto depende de las reglas de la gramática.
        # Aquí va una implementación pragmática que se valida con tests:
        if ctx is None:
            return results
        # Si es un atom_expr, verificar si tiene trailers
        # ... (lógica detallada se completa al ver el .g4 real)
        return results

    # ---- for, with, except ----
    def visitFor_stmt(self, ctx):
        """for X in ...:"""
        # exprlist contiene los targets
        exprlist = ctx.exprlist()
        if exprlist:
            for name in self._walk_for_simple_names(exprlist):
                if not is_protected(name):
                    self.symbols.add(name, 'variable')
        return self.visitChildren(ctx)

    def visitWith_item(self, ctx):
        """with EXPR as X:"""
        if ctx.expr():  # parte after 'as'
            for name in self._walk_for_simple_names(ctx.expr()):
                if not is_protected(name):
                    self.symbols.add(name, 'variable')
        return self.visitChildren(ctx)

    def visitExcept_clause(self, ctx):
        """except EXPR as X:"""
        if ctx.NAME():
            name = ctx.NAME().getText()
            if not is_protected(name):
                self.symbols.add(name, 'variable')
        return self.visitChildren(ctx)

    # ---- lambda ----
    def visitLambdef(self, ctx):
        """lambda X, Y: ..."""
        varargslist = ctx.varargslist()
        if varargslist:
            for vfpdef in varargslist.vfpdef():
                name = vfpdef.NAME().getText()
                if not is_protected(name):
                    self.symbols.add(name, 'parameter')
        return self.visitChildren(ctx)
```

> Las funciones `_extract_assignment_targets` y `_walk_for_simple_names` requieren examinar la gramática real. La estrategia segura es: si en cualquier nivel del subárbol aparece un `trailer` (`.x`, `[x]`, `(x)`), abandonar esa rama (no es asignación de variable simple).

### 10.3 `src/transformations/rename_transformer.py`

**Propósito:** aplicar el renombrado usando `TokenStreamRewriter`. Itera sobre el token stream y reemplaza cada token `NAME` cuyo texto esté en la `SymbolTable`.

**Regla central:** un token `NAME` se renombra si y solo si:
- Su texto está en la `SymbolTable`, Y
- El token anterior visible **no** es un `.` (DOT) — porque eso significa que es un acceso a atributo.

**Implementación:**

```python
"""Renombra identificadores usando TokenStreamRewriter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'generated'))

from antlr4 import CommonTokenStream
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from Python3Lexer import Python3Lexer

from src.symbol_table import SymbolTable
from src.protected_names import is_protected


class RenameTransformer:
    def __init__(self, token_stream: CommonTokenStream, symbols: SymbolTable, imports: set[str]):
        self.rewriter = TokenStreamRewriter(token_stream)
        self.tokens = token_stream
        self.symbols = symbols
        self.imports = imports
        self.renamed_count = 0

    def apply(self) -> str:
        for i in range(self.tokens.size):
            token = self.tokens.get(i)
            if token.type != Python3Lexer.NAME:
                continue
            name = token.text
            if is_protected(name) or name in self.imports:
                continue
            # Verificar si el token anterior visible es un '.'
            if self._previous_visible_is_dot(i):
                continue
            sym = self.symbols.get(name)
            if sym is None:
                continue
            self.rewriter.replaceSingleToken(token, sym.obfuscated)
            self.renamed_count += 1
        return self.rewriter.getDefaultText()

    def _previous_visible_is_dot(self, index: int) -> bool:
        """Mira hacia atrás en el stream saltando whitespace/newlines."""
        i = index - 1
        while i >= 0:
            tok = self.tokens.get(i)
            # Si es token oculto (WS, NEWLINE), saltar
            if tok.channel != 0:  # canal 0 = visible
                i -= 1
                continue
            # NEWLINE puede estar en canal 0 también
            return tok.text == '.'
        return False
```

### 10.4 `src/transformations/comment_remover.py`

**Propósito:** eliminar todos los comentarios `#` y docstrings.

**Reglas:**

1. **Comentarios `#`:** están en el canal `HIDDEN` del lexer. Iterar todos los tokens con `channel != 0` y `text.startswith('#')`, y eliminarlos con `rewriter.deleteToken(token)`.

2. **Docstrings:** son `STRING` tokens triple-quoted (`"""..."""` o `'''...'''`) que aparecen como **primer statement** de un módulo, función o clase. Detección:
   - Recorrer el parse tree (no solo el token stream).
   - Para cada `funcdef`, `classdef` y para el `file_input` (módulo), inspeccionar el primer statement del cuerpo (suite).
   - Si el primer statement es una expresión que es solo un string literal triple-quoted, marcarlo para eliminación.
   - Reemplazar el token con cadena vacía o eliminarlo del stream.

**Implementación:**

```python
"""Elimina comentarios # y docstrings."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'generated'))

from antlr4 import CommonTokenStream
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from Python3Lexer import Python3Lexer
from Python3Parser import Python3Parser


class CommentRemover:
    def __init__(self, token_stream: CommonTokenStream, parse_tree):
        self.rewriter = TokenStreamRewriter(token_stream)
        self.tokens = token_stream
        self.tree = parse_tree
        self.comments_removed = 0
        self.docstrings_removed = 0

    def apply(self) -> str:
        self._remove_hash_comments()
        self._remove_docstrings()
        return self.rewriter.getDefaultText()

    def _remove_hash_comments(self):
        for i in range(self.tokens.size):
            tok = self.tokens.get(i)
            if tok.channel != 0 and tok.text.lstrip().startswith('#'):
                self.rewriter.delete(self.rewriter.DEFAULT_PROGRAM_NAME, tok.tokenIndex, tok.tokenIndex)
                self.comments_removed += 1

    def _remove_docstrings(self):
        """Recorre el parse tree y elimina el primer string de cada bloque."""
        self._scan_node(self.tree)

    def _scan_node(self, ctx):
        # Buscar funcdef, classdef, file_input
        # Para cada uno: obtener el suite (cuerpo) y mirar el primer simple_stmt
        # Si es un string literal solo, eliminarlo
        class_name = type(ctx).__name__
        if class_name in ('File_inputContext', 'FuncdefContext', 'ClassdefContext'):
            self._try_remove_first_docstring(ctx)
        # Recursión
        if hasattr(ctx, 'children') and ctx.children:
            for child in ctx.children:
                if hasattr(child, 'children'):
                    self._scan_node(child)

    def _try_remove_first_docstring(self, ctx):
        """Encuentra el primer statement del suite y, si es un string, lo elimina."""
        # Buscar el primer 'simple_stmt' o 'small_stmt' que contenga solo un STRING
        # Esta función requiere navegar la estructura específica del .g4
        suite = None
        if hasattr(ctx, 'suite'):
            suite = ctx.suite() if callable(ctx.suite) else None
        if suite is None:
            # Para file_input, los stmts están directamente
            stmts = ctx.children if hasattr(ctx, 'children') else []
        else:
            stmts = suite.children if hasattr(suite, 'children') else []

        for stmt in stmts:
            text = stmt.getText() if hasattr(stmt, 'getText') else ''
            # Heuristica: si el statement es solo un STRING triple-quoted
            if self._is_docstring_stmt(stmt):
                start = stmt.start.tokenIndex
                stop = stmt.stop.tokenIndex
                self.rewriter.delete(self.rewriter.DEFAULT_PROGRAM_NAME, start, stop)
                self.docstrings_removed += 1
                return  # solo el primero

    def _is_docstring_stmt(self, stmt) -> bool:
        """True si el statement es un string literal triple-quoted solo."""
        text = stmt.getText() if hasattr(stmt, 'getText') else ''
        text = text.strip().rstrip(';')
        if not text:
            return False
        return (text.startswith('"""') and text.endswith('"""')) or \
               (text.startswith("'''") and text.endswith("'''"))
```

### 10.5 `src/transformations/string_cipher.py`

**Propósito:** cifrar todos los string literals (no f-strings, no docstrings, no raw strings) reemplazándolos por una expresión que decodifica desde Base64 en runtime.

**Reglas de exclusión:**

- F-strings (`f"..."`, `f'...'`): NO cifrar porque contienen expresiones evaluables.
- Raw strings (`r"..."`, `r'...'`): NO cifrar porque preservan escapes literales.
- Byte strings (`b"..."`, `b'...'`): NO cifrar (tipo diferente).
- Triple-quoted strings: solo si no fueron docstrings (ya removidos en pasada anterior).

**Reemplazo:**

```
"hola"  →  __import__("base64").b64decode("aG9sYQ==").decode("utf-8")
```

**Implementación:**

```python
"""Cifra string literals en Base64 con decodificación inline."""

import base64
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'generated'))

from antlr4 import CommonTokenStream
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from Python3Lexer import Python3Lexer


class StringCipher:
    # Prefijos que indican strings que NO se ciframos
    SKIP_PREFIXES = ('f"', "f'", 'F"', "F'",
                     'r"', "r'", 'R"', "R'",
                     'b"', "b'", 'B"', "B'",
                     'rb', 'Rb', 'rB', 'RB',
                     'br', 'Br', 'bR', 'BR',
                     'fr', 'Fr', 'fR', 'FR',
                     'rf', 'Rf', 'rF', 'RF')

    def __init__(self, token_stream: CommonTokenStream):
        self.rewriter = TokenStreamRewriter(token_stream)
        self.tokens = token_stream
        self.ciphered_count = 0

    def apply(self) -> str:
        for i in range(self.tokens.size):
            tok = self.tokens.get(i)
            if tok.type != Python3Lexer.STRING:
                continue
            text = tok.text
            if self._should_skip(text):
                continue
            content = self._extract_content(text)
            if content is None:
                continue
            encoded = base64.b64encode(content.encode('utf-8')).decode('ascii')
            replacement = f'__import__("base64").b64decode("{encoded}").decode("utf-8")'
            self.rewriter.replaceSingleToken(tok, replacement)
            self.ciphered_count += 1
        return self.rewriter.getDefaultText()

    def _should_skip(self, text: str) -> bool:
        return text.startswith(self.SKIP_PREFIXES)

    def _extract_content(self, raw: str) -> str | None:
        """Extrae el contenido de un string literal, manejando escapes."""
        # Triple-quoted
        if raw.startswith('"""') and raw.endswith('"""'):
            inner = raw[3:-3]
        elif raw.startswith("'''") and raw.endswith("'''"):
            inner = raw[3:-3]
        elif raw.startswith('"') and raw.endswith('"'):
            inner = raw[1:-1]
        elif raw.startswith("'") and raw.endswith("'"):
            inner = raw[1:-1]
        else:
            return None
        # Procesar escapes: \n, \t, \\, \', \", \xNN, \uNNNN
        try:
            # Usar codecs.decode con 'unicode_escape' para procesar los escapes
            import codecs
            decoded = codecs.decode(inner, 'unicode_escape')
            return decoded
        except Exception:
            return None
```

### 10.6 `src/transformations/dead_code_inserter.py`

**Propósito:** insertar sentencias inofensivas en puntos seguros del código para aumentar el ruido visual.

**Reglas de seguridad:**

- Solo insertar **a nivel de módulo** (statements top-level). No insertar dentro de funciones (puede romper la indentación o cambiar el comportamiento si hay returns prematuros).
- Las inserciones deben respetar la indentación: a nivel de módulo, indentación 0.
- Las sentencias insertadas no deben tener efectos secundarios observables.

**Snippets seguros:**

```python
DEAD_SNIPPETS = [
    "_unused_{i} = None",
    "_unused_{i} = 0",
    "_unused_{i} = []",
    "if False:\n    _x_{i} = 0",
    "_unused_{i} = (lambda: None)()",
]
```

**Estrategia:** después de cada simple_stmt top-level, con probabilidad `density` (default 0.3), insertar un snippet seleccionado al azar.

**Implementación:**

```python
"""Inserta código muerto a nivel de módulo."""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / 'generated'))

from antlr4 import CommonTokenStream
from antlr4.TokenStreamRewriter import TokenStreamRewriter
from Python3Parser import Python3Parser


DEAD_SNIPPETS = [
    "_unused_{i} = None\n",
    "_unused_{i} = 0\n",
    "_unused_{i} = []\n",
    "_unused_{i} = (lambda: None)()\n",
]


class DeadCodeInserter:
    def __init__(self, token_stream: CommonTokenStream, parse_tree, density: float = 0.3, seed: int | None = None):
        self.rewriter = TokenStreamRewriter(token_stream)
        self.tokens = token_stream
        self.tree = parse_tree
        self.density = density
        self.counter = 0
        self.inserted_count = 0
        if seed is not None:
            random.seed(seed)

    def apply(self) -> str:
        # Iterar sobre los statements top-level del file_input
        stmts = self._get_top_level_stmts()
        for stmt in stmts:
            if random.random() < self.density:
                snippet = random.choice(DEAD_SNIPPETS).format(i=self.counter)
                self.counter += 1
                # Insertar antes del start token del statement
                self.rewriter.insertBeforeToken(stmt.start, snippet)
                self.inserted_count += 1
        return self.rewriter.getDefaultText()

    def _get_top_level_stmts(self):
        """Retorna los nodos stmt directos del file_input."""
        results = []
        if hasattr(self.tree, 'children') and self.tree.children:
            for child in self.tree.children:
                # Los stmts del file_input son nodos 'stmt' o 'simple_stmt'/'compound_stmt'
                class_name = type(child).__name__
                if class_name.endswith('StmtContext') or class_name == 'StmtContext':
                    results.append(child)
        return results
```

### 10.7 `src/stats/obfuscation_stats.py`

**Propósito:** recolectar estadísticas durante el pipeline para mostrarlas en el HTML viewer.

```python
"""Estadisticas del proceso de ofuscacion."""

from dataclasses import dataclass, asdict


@dataclass
class ObfuscationStats:
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
```

### 10.8 `src/obfuscator.py`

**Propósito:** orquestador del pipeline de ofuscación. Toma un archivo de entrada y configuración; retorna el código ofuscado, el symbol map y las estadísticas.

```python
"""Orquesta el pipeline completo de ofuscacion."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'generated'))

from antlr4 import InputStream, CommonTokenStream
from Python3Lexer import Python3Lexer
from Python3Parser import Python3Parser

from src.symbol_table import SymbolTable
from src.visitors.symbol_collector import SymbolCollectorVisitor
from src.transformations.rename_transformer import RenameTransformer
from src.transformations.comment_remover import CommentRemover
from src.transformations.string_cipher import StringCipher
from src.transformations.dead_code_inserter import DeadCodeInserter
from src.stats.obfuscation_stats import ObfuscationStats


class ObfuscatorConfig:
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
    def __init__(self, config: ObfuscatorConfig | None = None):
        self.config = config or ObfuscatorConfig()

    def obfuscate_source(self, source: str) -> tuple[str, dict, ObfuscationStats]:
        """Ofuscar codigo. Retorna (codigo_ofuscado, symbol_map_dict, stats)."""
        stats = ObfuscationStats()
        stats.lines_original = source.count('\n') + 1

        # ---- PASADA 1: analisis ----
        tree, token_stream = self._parse(source)
        collector = SymbolCollectorVisitor()
        collector.visit(tree)
        stats.symbols_total = len(collector.symbols.all_symbols())

        # ---- PASADA 2: renombrado ----
        current_source = source
        if self.config.rename:
            tree2, ts2 = self._parse(current_source)
            ts2.fill()
            renamer = RenameTransformer(ts2, collector.symbols, collector.imports)
            current_source = renamer.apply()
            stats.identifiers_renamed = renamer.renamed_count

        # ---- PASADA 3: comentarios y docstrings ----
        if self.config.remove_comments:
            tree3, ts3 = self._parse(current_source)
            ts3.fill()
            remover = CommentRemover(ts3, tree3)
            current_source = remover.apply()
            stats.comments_removed = remover.comments_removed
            stats.docstrings_removed = remover.docstrings_removed

        # ---- PASADA 4: cifrado de strings ----
        if self.config.cipher_strings:
            tree4, ts4 = self._parse(current_source)
            ts4.fill()
            cipher = StringCipher(ts4)
            current_source = cipher.apply()
            stats.strings_ciphered = cipher.ciphered_count

        # ---- PASADA 5: dead code ----
        if self.config.dead_code:
            tree5, ts5 = self._parse(current_source)
            inserter = DeadCodeInserter(ts5, tree5,
                                         density=self.config.dead_code_density,
                                         seed=self.config.dead_code_seed)
            current_source = inserter.apply()
            stats.dead_code_inserted = inserter.inserted_count

        stats.lines_obfuscated = current_source.count('\n') + 1
        return current_source, collector.symbols.to_dict(), stats

    def obfuscate_file(self, input_path: Path, output_path: Path, map_path: Path) -> ObfuscationStats:
        import json
        source = input_path.read_text(encoding='utf-8')
        obfuscated, symbol_map, stats = self.obfuscate_source(source)
        output_path.write_text(obfuscated, encoding='utf-8')
        map_path.write_text(json.dumps(symbol_map, indent=2, ensure_ascii=False), encoding='utf-8')
        return stats

    @staticmethod
    def _parse(source: str):
        stream = InputStream(source)
        lexer = Python3Lexer(stream)
        token_stream = CommonTokenStream(lexer)
        parser = Python3Parser(token_stream)
        tree = parser.file_input()
        return tree, token_stream
```

### 10.9 `src/deobfuscator.py`

**Propósito:** revertir un archivo ofuscado al código original usando el `symbol_map.json`.

**Estrategia:**

1. **Restaurar strings:** buscar todas las ocurrencias del patrón `__import__("base64").b64decode("CONTENIDO").decode("utf-8")` y reemplazar por el string literal original. Usar regex con cuidado de escapar comillas internas.

2. **Restaurar identificadores:** para cada `Symbol` del mapa, reemplazar el `obfuscated` por el `original`. Usar regex con `\b` (word boundaries) y procesar en orden descendente de longitud del nombre ofuscado para evitar reemplazos parciales (aunque con el formato `_v0001` esto no debería pasar — pero es defensivo).

3. **Limitación honesta:** los comentarios y docstrings eliminados **no se pueden recuperar**. El código deofuscado es funcionalmente equivalente al original pero pierde la documentación. Esto se documenta en el README.

**Implementación:**

```python
"""Pipeline inverso: ofuscado -> codigo legible."""

import base64
import json
import re
from pathlib import Path

from src.symbol_table import SymbolTable


class Deobfuscator:
    def __init__(self, symbol_map_path: Path):
        data = json.loads(symbol_map_path.read_text(encoding='utf-8'))
        self.table = SymbolTable.from_dict(data)
        # Mapping inverso obfuscated -> original
        self._reverse_map = {s.obfuscated: s.original for s in self.table.all_symbols()}

    def deobfuscate_source(self, source: str) -> str:
        # 1. Restaurar strings cifrados
        source = self._restore_strings(source)
        # 2. Restaurar identificadores
        source = self._restore_identifiers(source)
        return source

    def deobfuscate_file(self, input_path: Path, output_path: Path) -> None:
        source = input_path.read_text(encoding='utf-8')
        result = self.deobfuscate_source(source)
        output_path.write_text(result, encoding='utf-8')

    def _restore_strings(self, source: str) -> str:
        pattern = re.compile(
            r'__import__\("base64"\)\.b64decode\("([A-Za-z0-9+/=]+)"\)\.decode\("utf-8"\)'
        )

        def replacer(match: re.Match) -> str:
            encoded = match.group(1)
            try:
                decoded = base64.b64decode(encoded).decode('utf-8')
                # Re-escapar para construir un string literal Python valido
                # Usar repr() y manejar comillas
                literal = repr(decoded)
                return literal
            except Exception:
                return match.group(0)

        return pattern.sub(replacer, source)

    def _restore_identifiers(self, source: str) -> str:
        # Ordenar por longitud descendente para evitar reemplazos parciales
        ordered = sorted(self._reverse_map.keys(), key=len, reverse=True)
        for obf in ordered:
            original = self._reverse_map[obf]
            pattern = r'\b' + re.escape(obf) + r'\b'
            source = re.sub(pattern, original, source)
        return source
```

### 10.10 `src/viewer/html_viewer.py`

Ver sección 15 para la especificación completa del HTML viewer.

### 10.11 `src/main.py`

Ver sección 14 para la especificación completa del CLI.

---

## 11. Pipeline de ofuscación

Orden secuencial de aplicación (cada paso re-tokeniza el código resultante):

1. **Parse inicial** → árbol + token stream.
2. **Symbol collection** (Visitor) → `SymbolTable` + lista de imports.
3. **Rename transformation** → reemplaza identificadores en el token stream.
4. **Comment & docstring removal** → elimina comentarios `#` y docstrings.
5. **String cipher** → codifica string literals en Base64.
6. **Dead code insertion** (opcional) → inserta sentencias inofensivas a nivel de módulo.

**Por qué este orden:**

- Rename **antes** de String cipher: si ciframos primero, los strings ya cifrados contendrían el nombre `__import__` que nunca debe renombrarse (no pasa porque está protegido, pero es más limpio renombrar primero).
- Comments **antes** de String cipher: los docstrings son strings que se eliminan; si ciframos primero, intentaríamos cifrar y luego eliminar, lo cual es redundante y arriesgado.
- Dead code **al final**: las sentencias insertadas no deben ser afectadas por las otras transformaciones.

---

## 12. Pipeline de deofuscación

1. **Cargar `symbol_map.json`** → reconstruir `SymbolTable`.
2. **Restaurar strings:** regex search-and-replace de las expresiones `__import__("base64").b64decode(...).decode("utf-8")` por el string literal correspondiente.
3. **Restaurar identificadores:** regex search-and-replace de cada `obfuscated` por su `original`, con word boundaries.
4. **Escribir archivo restaurado.**

**Limitaciones documentadas:**

- Comentarios y docstrings eliminados no se pueden recuperar.
- El código muerto insertado permanece (porque el deofuscador no sabe distinguirlo de código real).
- El formato exacto (espaciado interno) puede diferir ligeramente del original.

---

## 13. Edge cases críticos

### 13.1 Strings con caracteres especiales

Strings como `"hola\nmundo"`, `"comilla \" interna"`, `"unicode \u00e9"` deben ser:
- **Procesados correctamente** al extraer su contenido (interpretar los escapes).
- **Re-emitidos correctamente** al cifrar (los caracteres reales van al Base64).
- **Restaurados correctamente** al deofuscar (usar `repr()` de Python para generar un literal válido).

**Test obligatorio:** un archivo con `print("hola\nmundo")` debe producir el mismo output después de ofuscar.

### 13.2 F-strings

Los f-strings (`f"Hola {nombre}"`) contienen expresiones evaluables. Si los ciframos perderíamos la capacidad de evaluar las expresiones. **Solución: nunca cifrar f-strings (saltarlos en `string_cipher.py`).**

Importante: si el f-string contiene un identificador renombrable (ej. `f"Hola {nombre}"` donde `nombre` se renombró a `_v0003`), el f-string debe quedar como `f"Hola {_v0003}"`. El `RenameTransformer` ya maneja esto correctamente porque opera a nivel de token, y los identificadores dentro de un f-string son tokens `NAME` separados (ANTLR los expone como tokens del f-string).

**Verificar:** abrir un archivo ofuscado con f-strings y confirmar visualmente que la sintaxis sigue siendo válida.

### 13.3 Atributos de objeto

Código como `usuario.nombre = "Juan"` tiene dos nombres: `usuario` (variable) y `nombre` (atributo). **Solo `usuario` debe renombrarse**, no `nombre`. La regla en el `RenameTransformer` es: si el token anterior visible es `.`, no renombrar.

**Test:** `class A: pass\na = A()\na.x = 1\nprint(a.x)` ofuscado debe seguir funcionando.

### 13.4 Asignaciones encadenadas y múltiples

```python
a = b = c = 5        # caso 1: encadenada
x, y = 1, 2          # caso 2: tupla
[p, q] = [3, 4]      # caso 3: lista
(m, n) = (5, 6)      # caso 4: tupla con parens
```

El `SymbolCollectorVisitor` debe identificar `a`, `b`, `c`, `x`, `y`, `p`, `q`, `m`, `n` como variables.

### 13.5 Comprehensions

```python
[x for x in range(10) if x > 5]
{k: v for k, v in items.items()}
{x for x in lista}
(x ** 2 for x in numeros)
```

Las variables iteradoras (`x`, `k`, `v`) son scope local del comprehension. Con el mapping global, se renombran como cualquier otra variable. Verificar que no rompan.

### 13.6 Decoradores

```python
@my_decorator
def funcion():
    pass
```

`my_decorator` es un identificador normal (variable o función). Se renombra. La sintaxis del decorador se mantiene.

### 13.7 Imports complejos

```python
import os
import os.path
import numpy as np
from typing import List, Dict
from collections import OrderedDict as ODict
```

Los nombres que quedan disponibles en el scope son: `os`, `np`, `List`, `Dict`, `ODict`. Todos deben quedar en la lista `imports` y nunca renombrarse.

### 13.8 Métodos `__init__` y otros dunders

Aunque `__init__` es un `def`, **no debe renombrarse** (rompería la construcción de objetos). La regla `is_dunder()` ya cubre esto.

### 13.9 Argumentos `*args` y `**kwargs`

Los nombres `args` y `kwargs` por convención no se deberían renombrar para mantener legibilidad, pero técnicamente son parámetros normales. **Decisión: sí renombrarlos**, porque la convención no es semánticamente requerida y la ofuscación es el objetivo.

### 13.10 Anotaciones de tipo

```python
def funcion(x: int, y: List[str]) -> Dict[str, int]:
    ...
```

`int`, `List`, `str`, `Dict` aparecen como `NAME` tokens. Los que sean built-ins (`int`, `str`) están protegidos. Los importados (`List`, `Dict`) están en `imports`. Verificar que las anotaciones no rompan.

### 13.11 Triple-quoted strings que NO son docstrings

```python
sql = """
SELECT * FROM users
WHERE id = 1
"""
```

Este string NO es docstring (no es el primer statement de un bloque). El `CommentRemover` debe dejarlo intacto. El `StringCipher` debe cifrarlo. **Test obligatorio:** asegurarse de que `sql` se cifra y el código sigue funcionando.

### 13.12 Imports usados solo como tipos

```python
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from foo import Bar

def funcion() -> 'Bar':
    ...
```

Caso límite raro. Si aparece, la herramienta puede comportarse impredecible. **Decisión: documentar como limitación conocida, no soportar específicamente.**

### 13.13 Cadenas vacías

`""` y `''` al cifrar dan `__import__("base64").b64decode("").decode("utf-8")` que es válido (devuelve `""`). Verificar.

### 13.14 Conflictos de nombres con dead code

Las variables `_unused_X` insertadas como dead code podrían colisionar con variables del usuario. **Mitigación:** usar un prefijo improbable (`_unused_dc_{i}` o `_codeshield_dead_{i}`) y verificar que no colisione con la `SymbolTable` antes de insertar.

---

## 14. Especificación del CLI

### 14.1 Comandos

```
codeshield obfuscate <archivo> [opciones]
codeshield deobfuscate <archivo> -m <map.json> [opciones]
```

### 14.2 Subcomando `obfuscate`

```
python -m src.main obfuscate <input.py> [opciones]

Argumentos posicionales:
  input.py                      Archivo Python de entrada

Opciones:
  -o, --output PATH             Archivo de salida ofuscado
                                (default: <input>_obfuscated.py)
  -m, --map PATH                Ruta del symbol_map.json
                                (default: <input>_symbol_map.json)
  --no-rename                   Desactivar renombrado de identificadores
  --no-remove-comments          Desactivar eliminación de comentarios/docstrings
  --no-cipher-strings           Desactivar cifrado de strings
  --dead-code                   Activar inserción de código muerto
  --dead-code-density FLOAT     Densidad de inserción (0.0-1.0, default: 0.3)
  --dead-code-seed INT          Seed para reproducibilidad del dead code
  --html                        Generar comparativa HTML
  --html-output PATH            Ruta del HTML (default: <input>_comparison.html)
  -v, --verbose                 Mostrar estadísticas detalladas
```

### 14.3 Subcomando `deobfuscate`

```
python -m src.main deobfuscate <input.py> -m <map.json> [opciones]

Argumentos posicionales:
  input.py                      Archivo ofuscado de entrada

Opciones:
  -m, --map PATH                symbol_map.json correspondiente (REQUERIDO)
  -o, --output PATH             Archivo de salida restaurado
                                (default: <input>_restored.py)
  -v, --verbose                 Mostrar estadísticas
```

### 14.4 Comportamiento esperado

- Si el archivo de entrada no existe, error claro y código de salida 1.
- Si la sintaxis no es Python válido, mensaje claro y código 1.
- Si la salida sobrescribiría un archivo existente, advertir (no falla, sobrescribe).
- Output siempre incluye al final un resumen con las estadísticas (líneas, identificadores renombrados, etc.).
- Si se pasa `--verbose`, mostrar la `SymbolTable` completa.

### 14.5 Implementación de `src/main.py`

```python
"""CLI entry point de CodeShield."""

import argparse
import sys
from pathlib import Path

from src.obfuscator import Obfuscator, ObfuscatorConfig
from src.deobfuscator import Deobfuscator
from src.viewer.html_viewer import generate_comparison_html


def cmd_obfuscate(args: argparse.Namespace) -> int:
    inp = Path(args.input)
    if not inp.exists():
        print(f"ERROR: archivo no encontrado: {inp}", file=sys.stderr)
        return 1
    if not inp.suffix == '.py':
        print(f"ADVERTENCIA: archivo no tiene extensión .py", file=sys.stderr)

    output = Path(args.output) if args.output else inp.with_name(inp.stem + '_obfuscated.py')
    map_path = Path(args.map) if args.map else inp.with_name(inp.stem + '_symbol_map.json')

    config = ObfuscatorConfig(
        rename=not args.no_rename,
        remove_comments=not args.no_remove_comments,
        cipher_strings=not args.no_cipher_strings,
        dead_code=args.dead_code,
        dead_code_density=args.dead_code_density,
        dead_code_seed=args.dead_code_seed,
    )

    obf = Obfuscator(config)
    try:
        stats = obf.obfuscate_file(inp, output, map_path)
    except Exception as e:
        print(f"ERROR al ofuscar: {e}", file=sys.stderr)
        return 1

    print(f"✓ Código ofuscado:  {output}")
    print(f"✓ Mapa de símbolos: {map_path}")
    print()
    print("Estadísticas:")
    print(f"  Líneas:                  {stats.lines_original} → {stats.lines_obfuscated}")
    print(f"  Identificadores:         {stats.identifiers_renamed} renombrados")
    print(f"  Símbolos en tabla:       {stats.symbols_total}")
    print(f"  Comentarios eliminados:  {stats.comments_removed}")
    print(f"  Docstrings eliminados:   {stats.docstrings_removed}")
    print(f"  Strings cifrados:        {stats.strings_ciphered}")
    if config.dead_code:
        print(f"  Dead code insertado:     {stats.dead_code_inserted}")

    if args.html:
        html_path = Path(args.html_output) if args.html_output else inp.with_name(inp.stem + '_comparison.html')
        generate_comparison_html(inp, output, map_path, html_path, stats)
        print(f"✓ Comparativa HTML: {html_path}")

    return 0


def cmd_deobfuscate(args: argparse.Namespace) -> int:
    inp = Path(args.input)
    map_path = Path(args.map)
    if not inp.exists():
        print(f"ERROR: archivo no encontrado: {inp}", file=sys.stderr)
        return 1
    if not map_path.exists():
        print(f"ERROR: symbol_map.json no encontrado: {map_path}", file=sys.stderr)
        return 1

    output = Path(args.output) if args.output else inp.with_name(inp.stem + '_restored.py')

    deobf = Deobfuscator(map_path)
    try:
        deobf.deobfuscate_file(inp, output)
    except Exception as e:
        print(f"ERROR al deofuscar: {e}", file=sys.stderr)
        return 1

    print(f"✓ Código restaurado: {output}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog='codeshield',
        description='Ofuscador y Deofuscador de código fuente Python.',
    )
    subparsers = parser.add_subparsers(dest='command', required=True)

    p_obf = subparsers.add_parser('obfuscate', help='Ofuscar un archivo Python.')
    p_obf.add_argument('input', help='Archivo .py de entrada')
    p_obf.add_argument('-o', '--output', help='Archivo de salida')
    p_obf.add_argument('-m', '--map', help='Ruta de symbol_map.json')
    p_obf.add_argument('--no-rename', action='store_true')
    p_obf.add_argument('--no-remove-comments', action='store_true')
    p_obf.add_argument('--no-cipher-strings', action='store_true')
    p_obf.add_argument('--dead-code', action='store_true')
    p_obf.add_argument('--dead-code-density', type=float, default=0.3)
    p_obf.add_argument('--dead-code-seed', type=int, default=None)
    p_obf.add_argument('--html', action='store_true')
    p_obf.add_argument('--html-output', default=None)
    p_obf.add_argument('-v', '--verbose', action='store_true')
    p_obf.set_defaults(func=cmd_obfuscate)

    p_de = subparsers.add_parser('deobfuscate', help='Deofuscar un archivo Python.')
    p_de.add_argument('input', help='Archivo ofuscado de entrada')
    p_de.add_argument('-m', '--map', required=True, help='symbol_map.json correspondiente')
    p_de.add_argument('-o', '--output', help='Archivo de salida restaurado')
    p_de.add_argument('-v', '--verbose', action='store_true')
    p_de.set_defaults(func=cmd_deobfuscate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
```

### 14.6 Scripts `.bat` de conveniencia

`run.bat`:
```batch
@echo off
python -m src.main obfuscate %*
```

`deobfuscate.bat`:
```batch
@echo off
python -m src.main deobfuscate %*
```

---

## 15. Especificación del visor HTML

### 15.1 Características

- **Tema oscuro** (más profesional para una demo de ofuscación).
- **Header** con título del proyecto y nombre del archivo procesado.
- **4 stat cards** en la parte superior con: líneas originales, identificadores renombrados, strings cifrados, comentarios eliminados.
- **Comparativa lado a lado**: dos paneles con scroll independiente, syntax highlighting con `highlight.js`.
- **Tabla de símbolos** debajo de la comparativa: columnas `Original | Ofuscado | Tipo`.
- **Footer** con texto "Generado por CodeShield".

### 15.2 Dependencias externas

`highlight.js` desde CDN (no requiere instalación):
- CSS: `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css`
- JS: `https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js`

### 15.3 Implementación de `src/viewer/html_viewer.py`

```python
"""Generador de comparativa HTML."""

import html
import json
from pathlib import Path

from src.stats.obfuscation_stats import ObfuscationStats


TEMPLATE = '''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>CodeShield — Comparativa de {filename}</title>
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
    background: #1a1a1a;
    color: #ddd;
    padding: 24px;
    min-height: 100vh;
}}
.header {{
    margin-bottom: 24px;
}}
h1 {{
    font-size: 28px;
    color: #fff;
    margin-bottom: 4px;
    font-weight: 600;
}}
.subtitle {{
    color: #888;
    font-size: 14px;
}}
.stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 12px;
    margin-bottom: 24px;
}}
.stat-card {{
    background: #2a2a2a;
    padding: 16px 20px;
    border-radius: 8px;
    border-left: 3px solid #4a9eff;
}}
.stat-card.alt {{ border-left-color: #ff7a59; }}
.stat-card.alt2 {{ border-left-color: #9bff7a; }}
.stat-card.alt3 {{ border-left-color: #d97aff; }}
.stat-label {{
    font-size: 11px;
    color: #888;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 6px;
}}
.stat-value {{
    font-size: 28px;
    font-weight: 600;
    color: #fff;
}}
.comparison {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 32px;
}}
.panel {{
    background: #282c34;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #333;
}}
.panel-header {{
    background: #1e1e1e;
    padding: 12px 16px;
    font-weight: 500;
    border-bottom: 1px solid #333;
    display: flex;
    justify-content: space-between;
    align-items: center;
}}
.panel-header .label {{ font-size: 13px; }}
.panel-header .badge {{
    font-size: 11px;
    background: #333;
    padding: 2px 8px;
    border-radius: 10px;
    color: #aaa;
}}
.panel-content {{
    max-height: 600px;
    overflow: auto;
}}
.panel-content pre {{ margin: 0; }}
.panel-content code {{
    font-family: "JetBrains Mono", "Fira Code", "Consolas", monospace;
    font-size: 13px;
    line-height: 1.6;
}}
.symbol-table {{
    background: #2a2a2a;
    padding: 20px;
    border-radius: 8px;
    margin-top: 16px;
}}
.symbol-table h3 {{
    color: #fff;
    margin-bottom: 12px;
    font-weight: 500;
    font-size: 16px;
}}
table {{
    width: 100%;
    border-collapse: collapse;
}}
th, td {{
    text-align: left;
    padding: 10px 14px;
    border-bottom: 1px solid #333;
    font-size: 13px;
}}
th {{
    background: #1e1e1e;
    color: #aaa;
    font-weight: 500;
    text-transform: uppercase;
    font-size: 11px;
    letter-spacing: 0.5px;
}}
td.original {{ color: #6ab7ff; font-family: monospace; }}
td.obfuscated {{ color: #ff9a6a; font-family: monospace; }}
td.kind {{
    color: #aaa;
    font-size: 11px;
    text-transform: uppercase;
}}
.footer {{
    margin-top: 32px;
    text-align: center;
    color: #555;
    font-size: 12px;
}}
@media (max-width: 900px) {{
    .comparison {{ grid-template-columns: 1fr; }}
}}
</style>
</head>
<body>
<div class="header">
  <h1>CodeShield — Comparativa</h1>
  <p class="subtitle">{filename}</p>
</div>

<div class="stats">
  <div class="stat-card">
    <div class="stat-label">Identificadores renombrados</div>
    <div class="stat-value">{renamed}</div>
  </div>
  <div class="stat-card alt">
    <div class="stat-label">Strings cifrados</div>
    <div class="stat-value">{ciphered}</div>
  </div>
  <div class="stat-card alt2">
    <div class="stat-label">Comentarios eliminados</div>
    <div class="stat-value">{comments}</div>
  </div>
  <div class="stat-card alt3">
    <div class="stat-label">Docstrings eliminados</div>
    <div class="stat-value">{docstrings}</div>
  </div>
</div>

<div class="comparison">
  <div class="panel">
    <div class="panel-header">
      <span class="label">Código original</span>
      <span class="badge">{lines_original} líneas</span>
    </div>
    <div class="panel-content"><pre><code class="language-python">{original_code}</code></pre></div>
  </div>
  <div class="panel">
    <div class="panel-header">
      <span class="label">Código ofuscado</span>
      <span class="badge">{lines_obfuscated} líneas</span>
    </div>
    <div class="panel-content"><pre><code class="language-python">{obfuscated_code}</code></pre></div>
  </div>
</div>

<div class="symbol-table">
  <h3>Mapa de símbolos ({symbols_total})</h3>
  <table>
    <thead><tr><th>Original</th><th>Ofuscado</th><th>Tipo</th></tr></thead>
    <tbody>
      {symbol_rows}
    </tbody>
  </table>
</div>

<div class="footer">Generado por CodeShield · Universidad Nacional de Colombia</div>

<script>hljs.highlightAll();</script>
</body>
</html>
'''


def generate_comparison_html(original_path: Path,
                              obfuscated_path: Path,
                              map_path: Path,
                              output_path: Path,
                              stats: ObfuscationStats) -> None:
    original = original_path.read_text(encoding='utf-8')
    obfuscated = obfuscated_path.read_text(encoding='utf-8')
    symbol_data = json.loads(map_path.read_text(encoding='utf-8'))

    # Construir filas de la tabla de símbolos
    rows = []
    for s in symbol_data.get('symbols', []):
        rows.append(
            f'<tr>'
            f'<td class="original">{html.escape(s["original"])}</td>'
            f'<td class="obfuscated">{html.escape(s["obfuscated"])}</td>'
            f'<td class="kind">{s["kind"]}</td>'
            f'</tr>'
        )

    rendered = TEMPLATE.format(
        filename=html.escape(original_path.name),
        renamed=stats.identifiers_renamed,
        ciphered=stats.strings_ciphered,
        comments=stats.comments_removed,
        docstrings=stats.docstrings_removed,
        lines_original=stats.lines_original,
        lines_obfuscated=stats.lines_obfuscated,
        symbols_total=stats.symbols_total,
        original_code=html.escape(original),
        obfuscated_code=html.escape(obfuscated),
        symbol_rows='\n      '.join(rows),
    )

    output_path.write_text(rendered, encoding='utf-8')
```

---

## 16. Casos de prueba

### 16.1 Archivos de entrada (en `examples/input/`)

#### `01_simple.py`
```python
def calcular_promedio(numeros):
    """Calcula el promedio de una lista de numeros."""
    total = sum(numeros)
    cantidad = len(numeros)
    return total / cantidad


# Programa principal
valores = [10, 20, 30, 40]
resultado = calcular_promedio(valores)
print(f"El promedio es: {resultado}")
```

**Output esperado al ejecutar:** `El promedio es: 25.0`

#### `02_classes.py`
```python
class Persona:
    """Representa una persona con nombre y edad."""

    def __init__(self, nombre, edad):
        self.nombre = nombre
        self.edad = edad

    def saludar(self):
        return f"Hola, soy {self.nombre} y tengo {self.edad} anos"


class Estudiante(Persona):
    def __init__(self, nombre, edad, carrera):
        super().__init__(nombre, edad)
        self.carrera = carrera

    def presentarse(self):
        base = self.saludar()
        return f"{base}. Estudio {self.carrera}"


def main():
    estudiantes = [
        Estudiante("Ana", 20, "Sistemas"),
        Estudiante("Luis", 22, "Mecanica"),
    ]
    for est in estudiantes:
        print(est.presentarse())


if __name__ == "__main__":
    main()
```

**Output esperado:**
```
Hola, soy Ana y tengo 20 anos. Estudio Sistemas
Hola, soy Luis y tengo 22 anos. Estudio Mecanica
```

#### `03_realistic.py`
```python
"""Sistema simple de gestion de inventario."""

import json


def cargar_inventario(productos):
    """Convierte lista de productos a dict indexado por id."""
    return {p["id"]: p for p in productos}


def filtrar_bajo_stock(inventario, umbral):
    return [p for p in inventario.values() if p["stock"] < umbral]


def calcular_valor_total(inventario):
    return sum(p["precio"] * p["stock"] for p in inventario.values())


def imprimir_reporte(inventario, umbral_bajo):
    valor_total = calcular_valor_total(inventario)
    bajos = filtrar_bajo_stock(inventario, umbral_bajo)
    print("=== REPORTE DE INVENTARIO ===")
    print(f"Valor total: ${valor_total:,.2f}")
    print(f"Productos con stock bajo (<{umbral_bajo}):")
    for prod in bajos:
        print(f"  - {prod['nombre']} (stock: {prod['stock']})")


if __name__ == "__main__":
    productos = [
        {"id": 1, "nombre": "Laptop", "precio": 2500.0, "stock": 3},
        {"id": 2, "nombre": "Mouse", "precio": 25.0, "stock": 50},
        {"id": 3, "nombre": "Teclado", "precio": 80.0, "stock": 2},
        {"id": 4, "nombre": "Monitor", "precio": 350.0, "stock": 8},
    ]
    inv = cargar_inventario(productos)
    imprimir_reporte(inv, umbral_bajo=5)
```

#### `04_advanced.py`
```python
"""Caso avanzado: decoradores, comprehensions, lambdas."""

from functools import wraps


def contar_llamadas(func):
    """Decorador que cuenta las invocaciones."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.contador += 1
        return func(*args, **kwargs)
    wrapper.contador = 0
    return wrapper


@contar_llamadas
def cuadrado(x):
    return x ** 2


def procesar(numeros):
    pares = [n for n in numeros if n % 2 == 0]
    cuadrados = list(map(lambda x: cuadrado(x), pares))
    return {n: c for n, c in zip(pares, cuadrados)}


if __name__ == "__main__":
    datos = list(range(1, 11))
    resultado = procesar(datos)
    print("Resultados:")
    for k, v in sorted(resultado.items()):
        print(f"  {k} -> {v}")
    print(f"cuadrado() fue llamado {cuadrado.contador} veces")
```

### 16.2 Tests automatizados

#### `tests/test_end_to_end.py` (test de invariancia — el más importante)

```python
"""Tests de invariancia: el codigo ofuscado debe ejecutar identico al original."""

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / 'examples' / 'input'


def run_python_file(path: Path) -> tuple[str, int]:
    """Ejecuta un archivo Python y devuelve (stdout, exit_code)."""
    result = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result.stdout, result.returncode


@pytest.mark.parametrize("example_name", [
    "01_simple.py",
    "02_classes.py",
    "03_realistic.py",
    "04_advanced.py",
])
def test_obfuscation_preserves_behavior(example_name):
    original = EXAMPLES_DIR / example_name
    assert original.exists(), f"Falta el archivo de ejemplo: {original}"

    expected_stdout, expected_code = run_python_file(original)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        obf = tmp_path / 'obfuscated.py'
        smap = tmp_path / 'map.json'

        result = subprocess.run([
            sys.executable, '-m', 'src.main', 'obfuscate',
            str(original),
            '-o', str(obf),
            '-m', str(smap),
        ], capture_output=True, text=True)
        assert result.returncode == 0, f"Ofuscacion fallo: {result.stderr}"

        actual_stdout, actual_code = run_python_file(obf)
        assert actual_code == expected_code
        assert actual_stdout == expected_stdout


@pytest.mark.parametrize("example_name", [
    "01_simple.py",
    "02_classes.py",
    "03_realistic.py",
])
def test_round_trip(example_name):
    """Ofuscar y luego deofuscar debe producir codigo ejecutable equivalente."""
    original = EXAMPLES_DIR / example_name
    expected_stdout, _ = run_python_file(original)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        obf = tmp_path / 'obfuscated.py'
        smap = tmp_path / 'map.json'
        restored = tmp_path / 'restored.py'

        subprocess.run([
            sys.executable, '-m', 'src.main', 'obfuscate',
            str(original), '-o', str(obf), '-m', str(smap),
        ], check=True, capture_output=True)

        subprocess.run([
            sys.executable, '-m', 'src.main', 'deobfuscate',
            str(obf), '-m', str(smap), '-o', str(restored),
        ], check=True, capture_output=True)

        restored_stdout, _ = run_python_file(restored)
        assert restored_stdout == expected_stdout
```

---

## 17. Criterios de validación

La aplicación se considera **completa y correcta** cuando se cumplen todos estos criterios:

### Funcionales

- [ ] El script `generate_parser.bat` ejecuta sin errores y produce los archivos en `/generated`.
- [ ] `tests/test_parser.py` pasa.
- [ ] `tests/test_symbol_table.py` pasa.
- [ ] `tests/test_rename.py` pasa.
- [ ] `tests/test_comment_remover.py` pasa.
- [ ] `tests/test_string_cipher.py` pasa.
- [ ] `tests/test_deobfuscator.py` pasa.
- [ ] **Todos los tests de `tests/test_end_to_end.py` pasan** (criterio más importante).
- [ ] El CLI `obfuscate` funciona con los 4 archivos de ejemplo.
- [ ] El CLI `deobfuscate` funciona con los archivos generados.
- [ ] El flag `--html` genera un archivo HTML válido que se abre en navegador y muestra correctamente la comparativa.
- [ ] Cada flag de desactivación (`--no-rename`, etc.) funciona independientemente.

### No funcionales

- [ ] El código tiene type hints en todas las funciones públicas.
- [ ] Cada módulo tiene docstring describiendo su propósito.
- [ ] No hay rutas absolutas hardcoded.
- [ ] El `README.txt` está completo y los comandos del README funcionan tal cual.
- [ ] El proyecto se ejecuta correctamente después de:
  ```
  pip install -r requirements.txt
  python -m src.main obfuscate examples/input/01_simple.py --html
  ```

### Estructurales

- [ ] La estructura de carpetas coincide con la sección 6.
- [ ] El `.gitignore` está presente y excluye `__pycache__`, `venv`, `examples/output/`.
- [ ] `requirements.txt` contiene solo `antlr4-python3-runtime==4.13.1`.

---

## 18. Orden de implementación recomendado

Este orden minimiza riesgos al construir incrementalmente. Cada fase tiene un criterio de salida claro.

### Fase 1 — Base estructural

1. Crear estructura de carpetas (sección 6).
2. Crear `requirements.txt`, `.gitignore`.
3. Descargar archivos `.g4` y `Python3LexerBase.py` en `grammar/`.
4. Crear `generate_parser.bat` y ejecutarlo.
5. Implementar `tests/test_parser.py` y verificar que pasa.

**Salida:** parser ANTLR funcional, smoke test pasa.

### Fase 2 — Análisis de símbolos

6. Implementar `src/protected_names.py`.
7. Implementar `src/symbol_table.py`.
8. Implementar `src/visitors/symbol_collector.py` (manejar inicialmente solo: funciones, clases, asignaciones simples, imports).
9. Crear `examples/input/01_simple.py`.
10. Test manual: ejecutar el `SymbolCollectorVisitor` sobre `01_simple.py` e imprimir la tabla; verificar que detecta los identificadores esperados.

**Salida:** tabla de símbolos generada correctamente para `01_simple.py`.

### Fase 3 — Renombrado básico

11. Implementar `src/transformations/rename_transformer.py`.
12. Implementar `src/obfuscator.py` (versión mínima: solo `rename`).
13. Implementar `src/main.py` con el subcomando `obfuscate` (solo flag `--no-cipher-strings --no-remove-comments`).
14. Probar manualmente: ofuscar `01_simple.py` y verificar que ejecuta con mismo output.
15. **Test obligatorio:** `test_obfuscation_preserves_behavior` para `01_simple.py`.

**Salida:** renombrado funcional con preservación de comportamiento verificada.

### Fase 4 — Eliminación de comentarios y docstrings

16. Implementar `src/transformations/comment_remover.py`.
17. Integrar en `obfuscator.py`.
18. Crear `examples/input/02_classes.py`.
19. Verificar que comentarios y docstrings desaparecen, código sigue ejecutando.

**Salida:** test end-to-end pasa para `01_simple.py` y `02_classes.py`.

### Fase 5 — Cifrado de strings

20. Implementar `src/transformations/string_cipher.py`.
21. Integrar en `obfuscator.py`.
22. Crear `examples/input/03_realistic.py`.
23. Verificar que strings se ven como `__import__("base64").b64decode(...)` y código sigue ejecutando.

**Salida:** tests end-to-end pasan para los 3 ejemplos hasta acá.

### Fase 6 — Extensión del Visitor

24. Extender `SymbolCollectorVisitor` para manejar: `for`, `with`, `except`, `lambda`, comprehensions.
25. Crear `examples/input/04_advanced.py`.
26. Verificar que el test end-to-end pasa para `04_advanced.py`.

**Salida:** los 4 ejemplos pasan invariancia.

### Fase 7 — Deofuscador

27. Implementar `src/deobfuscator.py`.
28. Agregar subcomando `deobfuscate` al CLI.
29. Implementar tests `test_round_trip` para `01_simple.py`, `02_classes.py`, `03_realistic.py`.

**Salida:** deofuscación funcional, round-trip verificado.

### Fase 8 — Dead code (opcional)

30. Implementar `src/transformations/dead_code_inserter.py`.
31. Integrar con flag `--dead-code`.
32. Verificar invariancia con dead code activado.

**Salida:** dead code funcional sin romper la invariancia.

### Fase 9 — Visor HTML

33. Implementar `src/stats/obfuscation_stats.py`.
34. Implementar `src/viewer/html_viewer.py`.
35. Verificar que el HTML generado se abre correctamente y muestra los 3 paneles esperados.

**Salida:** HTML viewer funcional.

### Fase 10 — Documentación y polish

36. Escribir `docs/README.txt`.
37. Verificar que todos los comandos del README funcionan.
38. Limpiar código: docstrings consistentes, type hints, eliminación de prints de debug.
39. Verificar todos los criterios de la sección 17.

**Salida:** proyecto listo para entrega.

---

## 19. Entregables finales

Estructura del ZIP a entregar:

```
CodeShield_<usuario1>_<usuario2>.zip
└── CodeShield_<usuario1>_<usuario2>/
    ├── grammar/
    ├── generated/                  # parser pre-generado
    ├── src/
    ├── examples/
    │   ├── input/                  # 4 archivos .py de ejemplo
    │   └── output/                 # ejemplos de output ya ejecutado
    │       ├── 01_simple_obfuscated.py
    │       ├── 01_simple_symbol_map.json
    │       ├── 01_simple_comparison.html
    │       ├── 01_simple_restored.py
    │       └── (idem para los 4 ejemplos)
    ├── tests/
    ├── docs/
    │   ├── README.txt
    │   └── presentacion.pdf
    ├── requirements.txt
    ├── generate_parser.bat
    ├── run.bat
    ├── deobfuscate.bat
    └── .gitignore
```

### Contenido del `README.txt`

```
================================================================
  CodeShield — Ofuscador y Deofuscador de Codigo Fuente Python
  Proyecto Final - Procesadores de Lenguajes de Programacion
  Universidad Nacional de Colombia
================================================================

DESCRIPCION
-----------
CodeShield es una herramienta de analisis y manipulacion automatica
de codigo fuente Python construida con ANTLR v4. Transforma scripts
Python legibles en versiones funcionalmente equivalentes pero
deliberadamente ilegibles, y permite revertir el proceso usando un
mapa de simbolos generado durante la ofuscacion.

Caso de uso: proteccion de propiedad intelectual al distribuir
codigo Python a terceros (algoritmos propietarios, herramientas
internas, scripts de automatizacion comercial).

REQUISITOS
----------
- Python 3.10 o superior
- (Solo para regenerar el parser) Java JDK 11+ y antlr-4.13.1-complete.jar

INSTALACION
-----------
1. Crear entorno virtual (opcional):
     python -m venv venv
     venv\Scripts\activate

2. Instalar dependencias:
     pip install -r requirements.txt

El parser ANTLR ya viene pre-generado en /generated, solo necesita
regenerarse si modifica los archivos .g4.

USO BASICO
----------

Ofuscar un archivo:
  run.bat examples\input\01_simple.py

Esto genera:
  - examples\input\01_simple_obfuscated.py
  - examples\input\01_simple_symbol_map.json

Ofuscar con visor HTML:
  run.bat examples\input\01_simple.py --html

Deofuscar:
  deobfuscate.bat examples\input\01_simple_obfuscated.py ^
                  -m examples\input\01_simple_symbol_map.json

OPCIONES DEL CLI
----------------

obfuscate <archivo.py>
  -o, --output PATH         archivo ofuscado (default: <nombre>_obfuscated.py)
  -m, --map PATH            symbol_map.json (default: <nombre>_symbol_map.json)
  --no-rename               desactivar renombrado
  --no-remove-comments      desactivar eliminacion de comentarios
  --no-cipher-strings       desactivar cifrado de strings
  --dead-code               activar insercion de codigo muerto
  --dead-code-density F     densidad de dead code (0.0-1.0, default 0.3)
  --html                    generar comparativa HTML
  -v, --verbose             mostrar estadisticas detalladas

deobfuscate <archivo.py> -m <map.json>
  -o, --output PATH         archivo restaurado
  -v, --verbose             modo verboso

LIMITACIONES CONOCIDAS
----------------------
- La deofuscacion NO recupera comentarios ni docstrings eliminados.
- El codigo muerto insertado no se elimina al deofuscar (no es
  distinguible del codigo del usuario).
- Strings tipo f-string, r-string y b-string NO se cifran (preservan
  su funcionalidad).
- Atributos de objeto (obj.atributo) NO se renombran (preservacion
  de APIs externas).

EJEMPLOS INCLUIDOS
------------------
examples/input/01_simple.py     - Funcion basica con variables
examples/input/02_classes.py    - Clases con herencia
examples/input/03_realistic.py  - Sistema de inventario con I/O
examples/input/04_advanced.py   - Decoradores, lambdas, comprehensions

Cada ejemplo tiene su contraparte ya procesada en examples/output/.

REGENERAR EL PARSER (opcional)
------------------------------
Solo si modifica los archivos .g4:

1. Descargar antlr-4.13.1-complete.jar a C:\antlr\
2. Ejecutar:  generate_parser.bat

CORRER TESTS
------------
  pip install pytest
  pytest tests/

ARQUITECTURA
------------
Ver docs/ARQUITECTURA.md para detalles del pipeline interno.

AUTORES
-------
[Nombres y correos institucionales]
```

### Contenido de la presentación (`presentacion.pdf`)

10-12 slides cubriendo lo que pide el enunciado del proyecto:

1. Título y autores
2. Motivación y justificación del problema (caso de uso real)
3. Antecedentes y trabajos relacionados (pyarmor, pyminifier, papers de Collberg)
4. Objetivo del trabajo
5. Propuesta (diagrama de arquitectura de la sección 8)
6. Implementación: stack técnico (ANTLR + Python + Visitor + TokenStreamRewriter)
7. Implementación: detalle de las 4 transformaciones
8. Demo (transición a vivo)
9. Pruebas y validación (los tests de invariancia y los 4 ejemplos)
10. Conclusiones (qué se logró, limitaciones, trabajos futuros)
11. Referencias
12. Preguntas

### Demo en vivo (3 minutos)

1. Mostrar `01_simple.py` original.
2. Ejecutarlo y mostrar el output.
3. Ejecutar `run.bat 01_simple.py --html`.
4. Abrir el HTML y mostrar la comparativa lado a lado.
5. Ejecutar el archivo ofuscado y mostrar el mismo output.
6. Ejecutar `deobfuscate.bat` y abrir el archivo restaurado.
7. Mostrar brevemente `04_advanced.py` ofuscado (impacto visual: completamente ilegible).

---

## 20. Notas críticas para la implementación

### 20.1 Verificación temprana de la gramática

Antes de implementar el `SymbolCollectorVisitor`, abrir `grammar/Python3Parser.g4` y **listar los nombres exactos de las reglas relevantes**: `funcdef`, `classdef`, `expr_stmt`, `import_name`, `import_from`, `for_stmt`, `with_stmt`, `try_stmt`, `lambdef`, `atom_expr`, `trailer`. Si la versión de la gramática usa nombres diferentes (ej. `function_def` en lugar de `funcdef`), ajustar el código del Visitor. Esto es la fuente #1 de bugs silenciosos.

### 20.2 Re-tokenización entre transformaciones

Cada transformación opera sobre un `TokenStreamRewriter` propio. **Nunca compartir un rewriter entre transformaciones.** El patrón correcto está en `obfuscator.py`: después de aplicar una transformación, llamar `rewriter.getDefaultText()`, y re-tokenizar el resultado para la siguiente. Esto evita inconsistencias en los índices de tokens.

### 20.3 Manejo de errores del parser

Si el archivo de entrada tiene errores de sintaxis Python, ANTLR puede tolerar algunos errores y seguir produciendo un árbol parcial, lo que causaría ofuscación incorrecta. **Solución:** instalar un `ErrorListener` que detecte errores y aborte el proceso:

```python
from antlr4.error.ErrorListener import ErrorListener

class FailFastErrorListener(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        raise SyntaxError(f"Error de sintaxis Python en linea {line}:{column}: {msg}")

# En Obfuscator._parse:
lexer = Python3Lexer(stream)
lexer.removeErrorListeners()
lexer.addErrorListener(FailFastErrorListener())
token_stream = CommonTokenStream(lexer)
parser = Python3Parser(token_stream)
parser.removeErrorListeners()
parser.addErrorListener(FailFastErrorListener())
```

### 20.4 Encoding

Todos los archivos se leen y escriben con `encoding='utf-8'`. Importante en Windows donde el default puede ser CP-1252.

### 20.5 Docstrings y triple-quoted strings que no son docstrings

La heurística para detectar docstrings es: triple-quoted string que es el primer statement del bloque (módulo, función o clase). Verificar específicamente que:

- Un string asignado a una variable (`x = """texto"""`) NO se trata como docstring.
- Un string que aparece después de otro statement NO se trata como docstring.
- Solo el primer string del bloque cuenta; si hay un segundo, ya no es docstring.

### 20.6 Verificación post-implementación

Después de implementar cada transformación, ejecutar:

```powershell
python -m src.main obfuscate examples\input\01_simple.py
python examples\input\01_simple_obfuscated.py
```

Y comparar visualmente el output con el de `python examples\input\01_simple.py`. Si difieren, hay un bug. El test automatizado `test_obfuscation_preserves_behavior` formaliza esta verificación.

### 20.7 Comentarios del código (interno)

Todo el código de la aplicación debe tener docstrings en **español** (consistente con el idioma del proyecto). Type hints obligatorios en todas las funciones públicas (`def func(x: int) -> str:`).

### 20.8 Logging vs prints

En el código de producción, usar `print()` solo en el `main.py` para output al usuario. Internamente, **no usar prints** — si se necesita debug, agregar un módulo de logging opcional o eliminarlo antes de la entrega.

### 20.9 Si una transformación rompe el código

El criterio de aceptación es: el código ofuscado **debe ejecutar idéntico** al original. Si después de implementar una transformación, un ejemplo deja de pasar el test de invariancia:

1. Aislar qué transformación lo rompe (desactivar las otras con flags).
2. Identificar el patrón del código original que dispara el bug (ej. f-strings, decoradores, comprehensions).
3. Refinar la regla específica de esa transformación para manejarlo, o documentarlo como limitación conocida.

### 20.10 Polish final

Antes de empaquetar para entrega:

- Eliminar archivos `.pyc`, `__pycache__`, `.pytest_cache`.
- Ejecutar la suite completa de tests y verificar que todos pasan.
- Generar los archivos de output en `examples/output/` para que el ZIP traiga ejemplos ya procesados.
- Verificar que el ZIP no incluye carpetas `venv/` ni archivos `.tokens` o `.interp` de ANTLR (estos son intermedios).

---

## Referencias técnicas

- The Definitive ANTLR 4 Reference, Terence Parr (Pragmatic Bookshelf, 2013)
- ANTLR 4 Documentation: https://github.com/antlr/antlr4/blob/master/doc/index.md
- ANTLR Python Target: https://github.com/antlr/antlr4/blob/master/doc/python-target.md
- Gramática Python3 oficial: https://github.com/antlr/grammars-v4/tree/master/python/python3_12_1
- TokenStreamRewriter (source): https://github.com/antlr/antlr4/blob/master/runtime/Python3/src/antlr4/TokenStreamRewriter.py
- Collberg, Thomborson, Low. "A Taxonomy of Obfuscating Transformations" (1997)

---

**Fin de la especificación.**