================================================================
  CodeShield - Ofuscador y Deofuscador de Codigo Fuente Python
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
- Python 3.10 o superior (probado en 3.12).
- (Solo para regenerar el parser) Java JDK 11+ y antlr-4.13.1-complete.jar.


INSTALACION
-----------
1. Crear entorno virtual (opcional):
     python -m venv venv
     venv\Scripts\activate

2. Instalar dependencias:
     pip install -r requirements.txt

El parser ANTLR ya viene pre-generado en /generated, solo necesita
regenerarse si se modifican los archivos .g4.


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
  --dead-code-seed N        seed para reproducibilidad
  --html                    generar comparativa HTML
  --html-output PATH        ruta del HTML
  -v, --verbose             mostrar tabla de simbolos

deobfuscate <archivo.py> -m <map.json>
  -o, --output PATH         archivo restaurado
  -v, --verbose             modo verboso


PIPELINE DE OFUSCACION
----------------------
1. Parse del codigo Python con ANTLR (gramatica Python 3.13).
2. SymbolCollectorVisitor recorre el AST y construye la tabla de simbolos.
3. RenameTransformer renombra identificadores usando TokenStreamRewriter.
4. CommentRemover elimina comentarios '#' y docstrings.
5. StringCipher codifica strings en Base64 con decodificacion inline.
6. DeadCodeInserter (opcional) inserta sentencias inofensivas.


LIMITACIONES CONOCIDAS
----------------------
- La deofuscacion NO recupera comentarios ni docstrings eliminados.
- El codigo muerto insertado no se elimina al deofuscar (no es
  distinguible del codigo del usuario).
- Strings tipo f-string, r-string y b-string NO se cifran (preservan
  su funcionalidad).
- Atributos de objeto (obj.atributo) NO se renombran (preservacion
  de APIs externas).
- Los metodos de clases (def dentro de class) NO se renombran
  porque su acceso es via obj.metodo y los atributos no se tocan.
- Si una variable del usuario tiene el mismo nombre que un kwarg
  externo (p.ej. `end` para `print(end=...)`), puede haber colision.


EJEMPLOS INCLUIDOS
------------------
examples/input/01_simple.py     - Funcion basica con variables
examples/input/02_classes.py    - Clases con herencia
examples/input/03_realistic.py  - Sistema de inventario con I/O
examples/input/04_advanced.py   - Decoradores, lambdas, comprehensions

Cada ejemplo tiene su contraparte ya procesada en examples/output/.


REGENERAR EL PARSER (opcional)
------------------------------
Solo si se modifican los archivos .g4:

1. Descargar antlr-4.13.1-complete.jar a C:\antlr\
   (https://www.antlr.org/download/antlr-4.13.1-complete.jar)
2. Ejecutar: generate_parser.bat


CORRER TESTS
------------
  pip install pytest
  pytest tests/


ARQUITECTURA
------------
Ver docs/ARQUITECTURA.md para detalles del pipeline interno.


AUTORES
-------
Daniel Soracipa  <dsoracipa@unal.edu.co>
Universidad Nacional de Colombia - Sede Bogota
