# CodeShield: Herramienta de Ofuscación y Deofuscación de Código Fuente Python mediante ANTLR v4

**Autor:** Daniel Soracipa — `dsoracipa@unal.edu.co`  
**Asignatura:** Procesadores de Lenguajes de Programación  
**Universidad Nacional de Colombia — Sede Bogotá**  
**Fecha:** Junio 2025

---

## Resumen

Este informe presenta el diseño e implementación de **CodeShield**, una herramienta de línea de comandos que aplica análisis y manipulación automática de código fuente Python mediante ANTLR v4. La herramienta construye un árbol sintáctico del código fuente usando la gramática oficial de Python 3.13, recorre dicho árbol con el **patrón Visitor** para recolectar identificadores, y aplica un pipeline de cuatro transformaciones (renombrado, eliminación de comentarios, cifrado de strings y código muerto) usando `TokenStreamRewriter`, preservando en todo momento la equivalencia semántica. El resultado es un archivo Python funcionalmente idéntico al original pero deliberadamente ilegible. El proceso es reversible mediante un mapa de símbolos generado durante la ofuscación. La herramienta cuenta con 47 tests automatizados, un visor HTML comparativo y un CLI completo.

---

## 1. Introducción

### 1.1 Contexto y motivación

Python es un lenguaje interpretado cuyo código fuente es directamente legible por cualquier persona con acceso al archivo `.py`. Esto representa un problema para organizaciones que distribuyen software propietario escrito en Python: algoritmos de negocio, fórmulas de valoración, lógica de evaluación o automatizaciones comerciales quedan expuestos cuando se comparte el archivo fuente.

Las soluciones existentes (compilación a `.pyc`, herramientas como PyArmor o pyminifier) tienen limitaciones: el bytecode es fácilmente descompilable, y las herramientas de terceros a menudo procesan el código mediante heurísticas basadas en expresiones regulares sin comprensión real de la sintaxis del lenguaje.

**CodeShield** aborda este problema desde una perspectiva de procesadores de lenguajes: construye un parser real del código fuente Python usando ANTLR v4, analiza su estructura mediante el patrón Visitor, y aplica transformaciones quirúrgicas basadas en el árbol sintáctico. El resultado preserva semántica verificable mediante tests de invariancia.

### 1.2 Alcance

El proyecto implementa una herramienta completa con:
- Parser Python 3.13 generado con ANTLR v4.13.1
- Visitor para análisis estático y construcción de tabla de símbolos
- Pipeline de 4 transformaciones configurables
- Proceso inverso (deofuscación) con mapa de símbolos
- CLI con 12 opciones
- Visor HTML comparativo
- 47 tests automatizados

---

## 2. Objetivos

### 2.1 Objetivo general

Construir una aplicación de análisis y manipulación automática de código fuente Python que demuestre el uso práctico de ANTLR v4, el patrón Visitor y la manipulación de streams de tokens para transformar código preservando su semántica.

### 2.2 Objetivos específicos

1. Integrar la gramática oficial Python 3.13 con ANTLR v4 y generar un parser funcional.
2. Implementar un Visitor que realice análisis estático del AST para identificar todos los identificadores definidos por el usuario.
3. Aplicar renombrado sistemático de variables, funciones, clases y parámetros sin romper la semántica del programa.
4. Eliminar comentarios y docstrings preservando la indentación y estructura del código.
5. Cifrar literales de string con Base64 con decodificación inline, preservando la ejecución.
6. Implementar un proceso inverso completo que restaure el código original a partir del mapa de símbolos.
7. Verificar la corrección mediante tests de invariancia: el código ofuscado debe producir el mismo stdout que el original.

---

## 3. Marco Teórico

### 3.1 ANTLR v4 y generación de parsers

ANTLR (*Another Tool for Language Recognition*) v4 es un generador de parsers que toma una gramática en formato EBNF y produce lexer y parser en el lenguaje objetivo (Python, Java, C#, etc.). El proceso general es:

1. **Gramática** (`.g4`): define tokens y reglas gramaticales.
2. **Lexer generado**: convierte la cadena de caracteres en una secuencia de tokens.
3. **Parser generado**: construye un árbol sintáctico concreto (parse tree) a partir de los tokens.
4. **Visitor/Listener**: recorre el árbol para realizar análisis o transformaciones.

ANTLR v4 usa *Adaptive LL(*)* como estrategia de parsing, lo que le permite manejar gramáticas ambiguas y predicados semánticos. La gramática Python 3.13 de grammars-v4 usa reglas ordenadas (`|`) para resolver ambigüedades de manera análoga a PEG parsers.

### 3.2 Patrón Visitor en procesadores de lenguajes

El **patrón Visitor** (Gamma et al., 1994) separa el algoritmo de recorrido de la estructura de datos sobre la que opera. En el contexto de ANTLR, permite definir operaciones sobre los nodos del árbol sintáctico sin modificar las clases de nodos generadas.

ANTLR genera automáticamente una clase `PythonParserVisitor` con métodos `visitX()` para cada regla gramatical `X`. Al extender esta clase y sobreescribir los métodos relevantes, se puede implementar cualquier análisis sobre el AST.

En CodeShield, el `SymbolCollectorVisitor` extiende `PythonParserVisitor` y sobreescribe 14 reglas para identificar todos los símbolos definidos por el usuario: funciones, clases, parámetros, variables locales, variables de comprehension, lambdas, operadores walrus, y variables de contexto (`for`, `with`, `except`).

### 3.3 TokenStreamRewriter

ANTLR incluye `TokenStreamRewriter`, una utilidad que permite aplicar reemplazos, inserciones y eliminaciones sobre el stream de tokens sin modificar el árbol sintáctico. Opera como un *overlay*: mantiene el stream original intacto y registra operaciones de edición que se aplican al invocar `getDefaultText()`.

Esto permite transformaciones quirúrgicas: solo se modifica lo necesario, preservando exactamente los espacios, comentarios y caracteres originales no afectados. Es superior a reconstruir el código desde el AST (que perdería formato, espacios, y tokens del canal `HIDDEN`).

### 3.4 Ofuscación de código

La ofuscación de código es una familia de técnicas que transforman código fuente o binario para dificultar su comprensión sin alterar su comportamiento (Collberg et al., 1997). Las técnicas utilizadas en CodeShield son:

- **Renombrado de identificadores**: reemplaza nombres significativos por identificadores crípticos (`_v0001`, `_f0001`). Es la técnica de mayor impacto en legibilidad.
- **Eliminación de comentarios y docstrings**: elimina documentación inline que facilita la comprensión.
- **Cifrado de literales**: reemplaza strings por expresiones de decodificación en tiempo de ejecución.
- **Inserción de código muerto**: añade sentencias que nunca afectan el estado del programa pero añaden ruido visual.

La propiedad central que valida cualquier ofuscador es la **invariancia semántica**: el programa ofuscado debe ejecutar idéntico al original.

---

## 4. Diseño e Implementación

### 4.1 Arquitectura general

El proyecto sigue una arquitectura de pipeline donde cada etapa recibe una cadena de código Python, la transforma, y pasa el resultado a la siguiente:

```
archivo.py
    │
    ▼
[ANTLR] PythonLexer → CommonTokenStream → PythonParser → ParseTree
    │
    ▼
[Visitor] SymbolCollectorVisitor
    ├─ SymbolTable: {nombre_original → nombre_ofuscado}
    └─ set(imports)
    │
    ▼
[Pipeline] Transformaciones secuenciales (re-tokenización entre cada paso)
    ├─ RenameTransformer      → usa SymbolTable + TokenStreamRewriter
    ├─ CommentRemover         → elimina tokens COMMENT y nodos docstring
    ├─ StringCipher           → cifra tokens STRING en Base64
    └─ DeadCodeInserter       → inserta snippets (opcional, configurable)
    │
    ▼
Salidas: archivo_obfuscated.py · symbol_map.json · comparison.html
```

**Decisión clave — diseño híbrido Visitor + TokenStreamRewriter:** un Visitor reconstructivo requeriría implementar manualmente las >100 reglas de la gramática. El enfoque híbrido usa el Visitor solo para *analizar* (qué transformar), y `TokenStreamRewriter` para *aplicar* los cambios. Todo lo no modificado se preserva bit a bit.

**Re-tokenización entre etapas:** cada transformación crea su propio `TokenStreamRewriter`, aplica los cambios y extrae el texto resultante. La siguiente etapa re-tokeniza desde cero. Esto evita inconsistencias de índices al acumular múltiples operaciones de reescritura sobre el mismo stream.

### 4.2 Gramática Python 3.13

Se usa la gramática Python 3.13 de grammars-v4 (autor: Robert Einhorn), que cubre el lenguaje Python completo incluyendo:
- `match/case` (Python 3.10+)
- Operador walrus `:=` (Python 3.8+)
- F-strings con tokens dedicados (`FSTRING_START`, `FSTRING_MIDDLE`, `FSTRING_END`)
- Type hints y `async/await`
- Todas las formas de comprensión y lambda

La gramática tiene 1399 líneas de lexer y 677 líneas de parser. El parser generado por ANTLR ocupa ~13.000 líneas de Python.

Un detalle crítico de implementación: el `PythonLexerBase` inyecta tokens sintéticos `ENCODING`, `INDENT` y `DEDENT` con texto literal (`"utf-8"`, `"<INDENT>"`). Estos deben limpiarse a cadena vacía después de `tokenStream.fill()` y antes de cualquier `replaceSingleToken()`, o `getDefaultText()` los emite literalmente y rompe la sintaxis del archivo de salida.

### 4.3 Tabla de símbolos y Visitor

El `SymbolCollectorVisitor` recorre el AST y construye la `SymbolTable`, un mapeo `{nombre_original → nombre_ofuscado}` con prefijos que indican el tipo del símbolo:

| Prefijo | Tipo |
|---------|------|
| `_v` | Variable |
| `_f` | Función |
| `_C` | Clase |
| `_p` | Parámetro |

Los símbolos **no** añadidos a la tabla (protegidos) incluyen: built-ins de Python, excepciones estándar, constantes del sistema, dunders (`__init__`, `__name__`), keywords, y todas las reglas de la gramática que corresponden a tokens NAME.

**Decisión: métodos de clase no se renombran.** Los métodos se acceden vía `obj.metodo`; los atributos no se renombran (no son `NAME` directo sino el token después de `.`). Si se renombrara `def metodo` sin renombrar `obj.metodo`, se produciría un `AttributeError`. El Visitor lleva un contador `_class_depth` para detectar funciones dentro de clases.

**Decisión: mapping global.** Un mismo nombre original recibe el mismo nombre ofuscado en todo el archivo, independientemente del scope. Esto simplifica la implementación y preserva la semántica: Python resuelve scopes léxicamente, no por nombre de identificador.

### 4.4 Transformaciones

#### RenameTransformer
Escanea todos los tokens `NAME` (y variantes `NAME_OR_TYPE`, `NAME_OR_MATCH`, `NAME_OR_CASE`) del stream. Para cada token cuyo texto aparece en la `SymbolTable`, lo reemplaza con el nombre ofuscado. La regla del punto: si el token anterior visible (no-hidden) es `.`, se salta (es un atributo de acceso, no una definición local).

#### CommentRemover
Elimina tokens `COMMENT` (canal HIDDEN) y docstrings. Para docstrings: recorre `File_inputContext`, `Function_def_rawContext` y `Class_def_rawContext`, detecta el primer statement de cada bloque, y si es un string literal aislado, elimina también los tokens `WS` de indentación y el `NEWLINE` final para no dejar líneas vacías que rompan la estructura indentada.

#### StringCipher
Reemplaza literales `STRING` ordinarios por:
```python
__import__("base64").b64decode("<encoded>").decode("utf-8")
```
No se cifran: raw strings (`r"..."`), byte strings (`b"..."`), f-strings (son tokens `FSTRING_*`, no `STRING`), ni strings dentro de expresiones de f-string (tokens `STRING` entre un `FSTRING_START` y su `FSTRING_END`, que rompería la sintaxis del f-string exterior al usar comillas dobles en el reemplazo).

#### DeadCodeInserter (opcional)
Inserta sentencias inofensivas (`_codeshield_dc_N = None`, `(lambda: None)()`) antes de statements top-level del módulo con probabilidad configurable (`--dead-code-density`). Usa un seed para reproducibilidad (`--dead-code-seed`).

### 4.5 Deofuscador

El `Deobfuscator` invierte el proceso usando el `symbol_map.json` generado durante la ofuscación. Opera con dos pases de expresiones regulares (no ANTLR):
1. **Restaurar strings:** busca el patrón `__import__("base64").b64decode("...").decode("utf-8")` y lo reemplaza por el string original decodificado.
2. **Restaurar identificadores:** ordena el mapa por longitud descendente (para evitar reemplazos parciales) y usa `\b` word boundaries para reemplazar cada nombre ofuscado por el original.

**Limitación conocida:** la deofuscación no recupera comentarios ni docstrings (eliminados de forma no reversible), ni código muerto (no distinguible del código de usuario).

---

## 5. Pruebas y Resultados

### 5.1 Estrategia de testing

Se implementaron 47 tests automatizados en 8 archivos usando pytest:

| Archivo de tests | Tests | Cobertura |
|-----------------|-------|-----------|
| `test_parser.py` | 4 | Parsing básico, smoke tests |
| `test_symbol_table.py` | 5 | Construcción del mapa, prefijos |
| `test_protected_names.py` | 8 | Identificadores protegidos |
| `test_rename.py` | 8 | Renombrado de variables, funciones, clases, parámetros |
| `test_comment_remover.py` | 5 | Comentarios, docstrings, indentación |
| `test_string_cipher.py` | 6 | Cifrado, exclusión de raw/byte strings |
| `test_deobfuscator.py` | 2 | Round-trip de strings e identificadores |
| `test_end_to_end.py` | 9 | Invariancia semántica, round-trip completo, dead code |

### 5.2 Tests de invariancia (criterio principal)

Los tests de mayor importancia son los de invariancia en `test_end_to_end.py`. Para cada uno de los 4 ejemplos incluidos:
1. Se ejecuta el archivo original y se captura su `stdout`.
2. Se ofusca el archivo.
3. Se ejecuta el archivo ofuscado y se captura su `stdout`.
4. Se verifica que ambos outputs sean idénticos.

Este criterio formaliza la propiedad central del ofuscador: la transformación preserva el comportamiento observable del programa.

### 5.3 Resultados

Todos los **47 tests pasan** tras corregir el bug de cifrado de strings dentro de f-strings.

**Resultado del bug corregido:** el ejemplo `03_realistic.py` contiene f-strings con acceso a claves de diccionario:
```python
print(f"  - {prod['nombre']} (stock: {prod['stock']})")
```
Los tokens `'nombre'` y `'stock'` son tokens `STRING` regulares, pero al cifrarlos se generaba:
```python
print(f"  - {prod[__import__("base64").b64decode("bm9tYnJl").decode("utf-8")]} ...")
```
Las comillas dobles del reemplazo conflictuaban con el f-string exterior, produciendo `SyntaxError`. La solución: pre-escanear el stream y marcar todos los tokens `STRING` que se encuentran entre un `FSTRING_START` y su correspondiente `FSTRING_END`, saltándolos durante el cifrado.

### 5.4 Análisis de rendimiento

El pipeline completo para los 4 ejemplos (11–37 líneas cada uno) tarda ~5 segundos en total, incluyendo 5 pasadas de tokenización por archivo. Para archivos de mayor tamaño podría ser un cuello de botella, pero está fuera del alcance del proyecto académico.

---

## 6. Conclusiones

### 6.1 Logros

- Se construyó un ofuscador Python completamente funcional usando ANTLR v4 con la gramática oficial Python 3.13, demostrando un caso de uso práctico y no trivial de procesadores de lenguajes.
- El patrón Visitor se aplicó de forma no destructiva para análisis estático: la `SymbolTable` se construye sin mutar el AST, lo que permite múltiples transformaciones independientes sobre el código original.
- El diseño híbrido Visitor + `TokenStreamRewriter` resulta más robusto y mantenible que un visitor reconstructivo, y preserva exactamente el formato original del código.
- Los tests de invariancia proporcionan una métrica objetiva de corrección: el código ofuscado ejecuta idéntico al original en los 4 ejemplos incluidos.
- El proceso es completamente reversible: dado el `symbol_map.json`, se puede restaurar el código ofuscado a un estado funcionalmente equivalente al original.

### 6.2 Limitaciones

- **Mapping global sin análisis de scopes:** dos variables en scopes distintos con el mismo nombre reciben el mismo nombre ofuscado. Esto preserva la semántica pero podría colisionar en casos extremos con kwargs de funciones externas.
- **Métodos de clase no renombrados:** necesario para preservar el protocolo de acceso vía atributo, pero reduce el impacto del renombrado en código orientado a objetos.
- **Deofuscación sin recuperación de comentarios:** los comentarios y docstrings eliminados no son recuperables, ya que no se almacenan en el mapa de símbolos.
- **Código muerto no eliminable en deofuscación:** no hay forma de distinguir código insertado artificialmente del código del usuario sin marcado adicional.

### 6.3 Trabajo futuro

- **Métricas de código sobre el AST:** complejidad ciclomática (McCabe), métricas de Halstead, detección de variables no usadas. El Visitor ya provee la infraestructura necesaria.
- **Análisis de dependencias entre scopes:** para un renombrado con conciencia de scopes que permita renombrar también los métodos de clase de forma segura.
- **Detección de patrones de seguridad:** uso de `eval`, `exec`, `os.system`, acceso a `__builtins__` — aplicación directa del análisis estático ya implementado.
- **Soporte multiplataforma para regeneración del parser:** script `generate_parser.sh` para Linux/Mac.

---

## Bibliografía

1. Parr, T. (2013). *The Definitive ANTLR 4 Reference*. Pragmatic Bookshelf.
2. Gamma, E., Helm, R., Johnson, R., & Vlissides, J. (1994). *Design Patterns: Elements of Reusable Object-Oriented Software*. Addison-Wesley.
3. Collberg, C., Thomborson, C., & Low, D. (1997). *A Taxonomy of Obfuscating Transformations*. Technical Report 148, University of Auckland.
4. Einhorn, R. (2024). *Python 3.13 ANTLR grammar*. grammars-v4 repository. https://github.com/antlr/grammars-v4/tree/master/python/python3_13
5. Python Software Foundation. (2024). *The Python Language Reference, version 3.13*. https://docs.python.org/3.13/reference/
6. Parr, T., & Fisher, K. (2011). *LL(*): the foundation of the ANTLR parser generator*. ACM SIGPLAN Notices, 46(6), 425–436.
7. Lam, M. S., Sethi, R., Ullman, J. D., & Aho, A. V. (2006). *Compilers: Principles, Techniques, and Tools* (2nd ed.). Addison-Wesley.
