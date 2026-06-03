# CodeShield

Herramienta de análisis y manipulación automática de código fuente Python construida sobre **ANTLR v4**. Transforma scripts Python legibles en versiones funcionalmente equivalentes pero deliberadamente ilegibles, y permite revertir el proceso mediante un mapa de símbolos generado durante la ofuscación.

**Caso de uso:** protección de propiedad intelectual al distribuir código Python a terceros (algoritmos propietarios, scripts de automatización comercial, herramientas internas).

---

## Requisitos

- Python 3.10 o superior
- `pip install -r requirements.txt`

_(Solo para regenerar el parser desde los archivos `.g4`: Java JDK 11+ y `antlr-4.13.1-complete.jar`)_

---

## Instalación

```bash
# Opcional: crear entorno virtual
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

El parser ANTLR ya viene pre-generado en `generated/`. No es necesario regenerarlo para usar la herramienta.

---

## Uso rápido

```bash
# Ofuscar un archivo
python -m src.main obfuscate examples/input/01_simple.py

# Ofuscar con visor HTML comparativo
python -m src.main obfuscate examples/input/01_simple.py --html -v

# Deofuscar (requiere el symbol_map.json generado)
python -m src.main deobfuscate examples/input/01_simple_obfuscated.py \
    -m examples/input/01_simple_symbol_map.json
```

También están disponibles los scripts de conveniencia para Windows:

```bat
run.bat examples\input\01_simple.py --html
deobfuscate.bat examples\input\01_simple_obfuscated.py -m examples\input\01_simple_symbol_map.json
```

---

## Pipeline de ofuscación

```
archivo.py
    │
    ▼
PythonLexer + CommonTokenStream  (ANTLR v4, gramática Python 3.13)
    │
    ▼
PythonParser  →  ParseTree
    │
    ▼
SymbolCollectorVisitor            (patrón Visitor — análisis no destructivo)
    │   construye SymbolTable: original → ofuscado
    ▼
Transformaciones secuenciales (TokenStreamRewriter)
    ├─ RenameTransformer      → _v0001, _f0001, _C0001, _p0001 ...
    ├─ CommentRemover         → elimina # y docstrings
    ├─ StringCipher           → Base64 con decodificación inline
    └─ DeadCodeInserter       → snippets inofensivos (opcional)
    │
    ▼
Salidas:
  archivo_obfuscated.py
  archivo_symbol_map.json
  comparison.html (--html)
```

---

## Opciones del CLI

### `obfuscate`

| Opción | Descripción |
|--------|-------------|
| `-o, --output PATH` | Archivo de salida (default: `<nombre>_obfuscated.py`) |
| `-m, --map PATH` | Ruta del symbol map JSON |
| `--no-rename` | Desactivar renombrado de identificadores |
| `--no-remove-comments` | Desactivar eliminación de comentarios |
| `--no-cipher-strings` | Desactivar cifrado de strings |
| `--dead-code` | Activar inserción de código muerto |
| `--dead-code-density F` | Densidad 0.0–1.0 (default: 0.3) |
| `--dead-code-seed N` | Seed para reproducibilidad |
| `--html` | Generar comparativa HTML |
| `--html-output PATH` | Ruta del archivo HTML |
| `-v, --verbose` | Mostrar tabla de símbolos |

### `deobfuscate`

| Opción | Descripción |
|--------|-------------|
| `-m, --map PATH` | Symbol map JSON (requerido) |
| `-o, --output PATH` | Archivo restaurado |
| `-v, --verbose` | Modo verboso |

---

## Ejemplos incluidos

| Archivo | Descripción |
|---------|-------------|
| `examples/input/01_simple.py` | Función básica con variables y f-strings |
| `examples/input/02_classes.py` | Clases con herencia y `super()` |
| `examples/input/03_realistic.py` | Sistema de inventario con I/O y dict comprehensions |
| `examples/input/04_advanced.py` | Decoradores, lambdas, comprehensions, `functools` |

---

## Tests

```bash
pip install pytest
pytest tests/ -v
```

47 tests automatizados: parser, tabla de símbolos, cada transformación individualmente, tests de invariancia semántica (el código ofuscado ejecuta idéntico al original).

---

## Limitaciones conocidas

- La deofuscación **no** recupera comentarios ni docstrings eliminados.
- El código muerto insertado **no** se elimina al deofuscar.
- Atributos (`obj.atributo`) y métodos de clase **no** se renombran (preservación de APIs externas).
- Si una variable del usuario coincide con un kwarg externo (p.ej. `end` para `print(end=...)`), puede haber colisión.

---

## Documentación técnica

- [`docs/ARQUITECTURA.md`](docs/ARQUITECTURA.md) — decisiones de diseño, diagrama de flujo, detalles de implementación.
- [`docs/README.txt`](docs/README.txt) — manual de usuario completo.
- [`Code_Shiel_Spec.md`](Code_Shiel_Spec.md) — especificación técnica exhaustiva del proyecto.

---

## Autor

**Daniel Soracipa** — `dsoracipa@unal.edu.co`  
Universidad Nacional de Colombia — Procesadores de Lenguajes de Programación, 2025
