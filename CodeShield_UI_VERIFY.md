# CodeShield — Extensión: Verificación de Invariancia + Interfaz Web

> Este documento es una especificación de implementación para Claude Code.
> Se asume que la aplicación base de CodeShield ya existe según `CodeShield_SPEC.md`.
> Este documento agrega dos funcionalidades nuevas: verificación automática de invariancia y una interfaz web.

---

## Contexto del proyecto existente

CodeShield es un ofuscador/deofuscador de código Python construido con ANTLR v4.
El pipeline actual produce:
- `archivo_obfuscated.py` — código ofuscado
- `symbol_map.json` — tabla de correspondencias para deofuscar
- `comparison.html` — reporte visual (opcional con `--html`)

El CLI actual tiene dos subcomandos: `obfuscate` y `deobfuscate`.

Las dos funcionalidades a implementar son **independientes entre sí** pero deben integrarse al pipeline y a la UI.

---

## PARTE 1 — Verificación automática de invariancia

### Qué es

Un módulo que ejecuta el archivo original y el archivo ofuscado con el mismo entorno y compara su comportamiento observable. Si ambos producen el mismo stdout y el mismo código de retorno, la ofuscación es "invariante" — correcta.

### Por qué importa

Convierte la corrección del ofuscador de algo que "se asume" a algo que "se demuestra" en cada ejecución. Es el criterio de validación más sólido del proyecto.

### Módulo: `src/verifier/invariance_checker.py`

Implementar la clase `InvarianceChecker` con la siguiente interfaz y comportamiento:

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class VerificationResult:
    passed: bool
    original_stdout: str
    obfuscated_stdout: str
    original_returncode: int
    obfuscated_returncode: int
    original_stderr: str
    obfuscated_stderr: str
    execution_time_original: float   # segundos
    execution_time_obfuscated: float
    diff_lines: list[str]            # líneas que difieren (vacío si passed=True)
    error_message: Optional[str]     # si hubo excepción durante la verificación
    skipped: bool = False            # True si no se pudo verificar
    skip_reason: Optional[str] = None

class InvarianceChecker:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def verify(self,
               original_path: Path,
               obfuscated_path: Path,
               args: list[str] | None = None,
               stdin_data: str | None = None) -> VerificationResult:
        """
        Ejecuta ambos archivos y compara sus salidas.

        Parámetros:
          - args: lista de argumentos CLI a pasar a ambos scripts
          - stdin_data: string que se pasa como stdin a ambos (para scripts interactivos)
        """
        ...
```

**Comportamiento requerido:**

1. Ejecutar `original_path` con `subprocess.run([sys.executable, str(original_path)] + (args or []))`.
2. Ejecutar `obfuscated_path` con los mismos argumentos.
3. Capturar `stdout`, `stderr` y `returncode` de ambos.
4. Medir el tiempo de ejecución de cada uno con `time.perf_counter()`.
5. Comparar `stdout` byte a byte. Si difieren, calcular las líneas que difieren usando `difflib.unified_diff`.
6. `passed = (stdout_original == stdout_obfuscated) and (returncode_original == returncode_obfuscated)`.

**Casos especiales que deben manejarse sin romperse:**

- **Timeout:** si cualquiera de los dos excede `self.timeout` segundos, retornar `VerificationResult(skipped=True, skip_reason="timeout después de Xs")`.
- **Error de importación / SyntaxError en el ofuscado:** capturar la excepción y retornar `VerificationResult(passed=False, error_message=str(e))`.
- **Output no determinista** (timestamp, random sin seed): no hay forma de detectarlo automáticamente. El verificador simplemente reporta el diff y deja que el usuario interprete.
- **Script que pide input interactivo** (llama a `input()` sin que se le pase stdin): detectar que stderr contiene `EOFError` y retornar `skipped=True, skip_reason="script requiere input interactivo — usar --stdin-data"`.

**Función auxiliar para generar el resumen imprimible:**

```python
def format_result(result: VerificationResult) -> str:
    """Retorna un string formateado para imprimir en terminal."""
    ...
```

El formato esperado en terminal (usar colores con `colorama` o con códigos ANSI directos):

```
Verificación de invariancia
───────────────────────────────────────────────────────
  Original:   0.023s  →  returncode 0
  Ofuscado:   0.031s  →  returncode 0
  Resultado:  ✓ INVARIANTE  (stdout idéntico)
───────────────────────────────────────────────────────
```

Si falla:

```
Verificación de invariancia
───────────────────────────────────────────────────────
  Original:   0.021s  →  returncode 0
  Ofuscado:   0.019s  →  returncode 1
  Resultado:  ✗ FALLA  (stdout difiere en 2 líneas)

  Diferencias:
  - Precio: 450.0
  + Precio: 0
───────────────────────────────────────────────────────
```

### Integración en el CLI existente

Agregar a `src/main.py` → subcomando `obfuscate`:

```
--verify                    Ejecutar verificación de invariancia después de ofuscar
--verify-timeout FLOAT      Timeout en segundos para la verificación (default: 10.0)
--verify-args ARGS          Argumentos a pasar al script durante verificación
--verify-stdin TEXT         Texto a pasar como stdin durante verificación
```

El flujo con `--verify` activo:

```
1. Ofuscar normalmente
2. Ejecutar InvarianceChecker.verify(original, obfuscated)
3. Imprimir el resultado con format_result()
4. Si passed=False: imprimir advertencia en amarillo
5. Si skipped=True: imprimir razón del skip en gris
6. En ambos casos continuar normalmente (no abortar)
7. Si --html está activo: incluir el resultado de verificación en el HTML
```

### Integración en el HTML viewer existente

Cuando se pasa un `VerificationResult` al `html_viewer.py`, agregar una sección visible entre las stat cards y la comparativa lado a lado:

- Si `passed=True`: barra verde con texto "✓ Comportamiento verificado — stdout idéntico".
- Si `passed=False`: barra roja con texto "✗ Verificación fallida — stdout difiere" + acordeón expandible con el diff.
- Si `skipped=True`: barra gris con texto "— Verificación omitida: {skip_reason}".

Modificar la firma de `generate_comparison_html` para aceptar `verification_result: VerificationResult | None = None`.

### Tests para el verificador: `tests/test_verifier.py`

```python
def test_simple_invariance_passes():
    """Un script simple debe verificar correctamente después de ofuscar."""

def test_invariance_fails_on_broken_obfuscation():
    """Si se introduce un bug en el ofuscado manualmente, el verificador debe detectarlo."""

def test_timeout_returns_skipped():
    """Un script con bucle infinito debe retornar skipped, no colgarse."""

def test_stdin_data_passthrough():
    """Un script que usa input() debe funcionar si se pasa --verify-stdin."""
```

Para `test_timeout_returns_skipped`, crear un script temporal que contenga `while True: pass`.

---

## PARTE 2 — Interfaz web

### Stack tecnológico

- **Backend:** Flask (agregar a `requirements.txt`: `flask==3.0.3`)
- **Frontend:** HTML + CSS + JS vanilla en un único archivo template. Sin frameworks externos salvo `highlight.js` (ya usado en el HTML viewer).
- **Comunicación:** AJAX con `fetch()` — el frontend llama al backend vía JSON, sin recargas de página.
- **Entry point:** `src/web_app.py`
- **Templates:** `src/templates/index.html` (único template)
- **Arranque:** `python -m src.web_app` o `web.bat`

### Estructura de archivos nuevos

```
src/
├── web_app.py                  # Flask app, rutas, lógica de request/response
├── templates/
│   └── index.html              # UI completa (HTML + CSS + JS en un solo archivo)
└── verifier/
    ├── __init__.py
    └── invariance_checker.py   # (ya descrito en Parte 1)

web.bat                         # script de arranque: python -m src.web_app
```

### Diseño de la interfaz

**Paleta y estilo** — debe ser coherente con el tema oscuro de CodeShield:
- Fondo: `#0D1117`
- Superficie de paneles: `#161B22`
- Bordes: `#30363D`
- Acento primario: `#4A9EFF`
- Acento secundario: `#FF7A59`
- Verde éxito: `#9BFF7A`
- Texto principal: `#FFFFFF`
- Texto secundario: `#8B949E`
- Fuente código: `Consolas, "Courier New", monospace`
- Fuente UI: `-apple-system, "Segoe UI", system-ui, sans-serif`

**Layout general** — tres zonas verticales:

```
┌─────────────────────────────────────────────────────────┐
│  HEADER: logo + título + badge "UNAL"                   │
├──────────────────────┬──────────────────────────────────┤
│                      │                                  │
│  PANEL IZQUIERDO     │  PANEL DERECHO                   │
│  (entrada)           │  (resultados)                    │
│                      │                                  │
│  Editor de código    │  — vacío hasta ejecutar —        │
│  + opciones          │  Luego muestra:                  │
│  + botones           │    · stats cards                 │
│                      │    · verificación                │
│                      │    · código ofuscado             │
│                      │    · tabla de símbolos           │
└──────────────────────┴──────────────────────────────────┘
```

Ancho de paneles: 40% izquierdo / 60% derecho en desktop. En móvil (<768px): columna única, izquierdo encima.

### Panel izquierdo — entrada y opciones

**Sección 1: editor de código**

- Label: "Código Python a ofuscar"
- `<textarea id="code-input">` con fondo `#010409`, fuente monospace, altura mínima 280px, resize vertical.
- Placeholder con un ejemplo de código Python (usar el `01_simple.py` del proyecto).
- Botón secundario "Cargar ejemplo" que rellena el textarea con el ejemplo.

**Sección 2: opciones de transformación**

Checkboxes con label y descripción corta, todos activados por defecto excepto dead-code:

```
[✓] Renombrar identificadores
    vars, funciones, clases y parámetros

[✓] Eliminar comentarios
    # y docstrings """..."""

[✓] Cifrar strings
    codificación Base64 inline

[ ] Insertar código muerto
    sentencias inofensivas (opcional)
    Densidad: [slider 0-100%]  (visible solo si checkbox activo)

[✓] Verificar invariancia
    ejecutar original y ofuscado y comparar stdout
```

**Sección 3: botones de acción**

- Botón principal: "Ofuscar" — color `#4A9EFF`, ancho completo, 44px de alto.
- Botón secundario: "Limpiar" — borde `#30363D`, limpia el textarea y los resultados.
- Estado de carga: mientras se procesa, el botón "Ofuscar" muestra un spinner y texto "Procesando...". Deshabilitar ambos botones durante el proceso.

### Panel derecho — resultados

**Estado inicial:** mostrar un placeholder con texto centrado: `// Los resultados aparecerán aquí` en color `#30363D`.

**Tras una ofuscación exitosa, mostrar en este orden:**

**A) Stats cards** — fila de 4 tarjetas (igual que el HTML viewer existente):

```
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│      6       │ │      1       │ │      2       │ │      0       │
│ Identificad. │ │   Strings    │ │ Comentarios  │ │  Dead code   │
│ renombrados  │ │  cifrados    │ │  eliminados  │ │  insertado   │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

**B) Banner de verificación** — solo si la opción estaba activa:

- Verde con `✓ Comportamiento verificado` si `passed=True`
- Rojo con `✗ Verificación fallida` + diff expandible si `passed=False`
- Gris con `— Verificación omitida: {razón}` si `skipped=True`

El banner debe tener 48px de alto, bordes redondeados, fuente monospace.

**C) Visor de código ofuscado** — panel con:
- Header con tabs: `Ofuscado` | `Original`
- Clicking en tab cambia el código mostrado sin re-petición al servidor
- Syntax highlighting con `highlight.js` cargado desde CDN
- Botón "Copiar" en esquina superior derecha del panel (usa `navigator.clipboard.writeText`)
- Botón "Descargar .py" que descarga el contenido como archivo

**D) Tabla de símbolos** — colapsable (por defecto abierta si hay ≤20 símbolos, cerrada si hay más):
- Columnas: `Original` | `Ofuscado` | `Tipo`
- Tipo usa un badge de color: variable=azul, function=naranja, class=verde, parameter=gris
- Buscador de texto inline que filtra las filas en tiempo real (JS, sin petición al servidor)
- Botón "Descargar symbol_map.json"

**E) Sección de deofuscación** — aparece siempre después de una ofuscación exitosa:
- Textarea pequeño con el código ofuscado (editable, por si el usuario quiere pegar otro)
- Botón "Deofuscar" que envía el código + el symbol_map al servidor y muestra el resultado
- Panel de resultado con el código restaurado + botón copiar

### API del backend: `src/web_app.py`

Implementar las siguientes rutas Flask:

**`POST /api/obfuscate`**

Request body (JSON):
```json
{
  "code": "def calcular(x):\n    return x * 2",
  "options": {
    "rename": true,
    "remove_comments": true,
    "cipher_strings": true,
    "dead_code": false,
    "dead_code_density": 0.3,
    "verify": true,
    "verify_timeout": 10.0
  }
}
```

Response (JSON):
```json
{
  "success": true,
  "obfuscated_code": "def _f0000(_p0001):\n    return _p0001 * 2",
  "original_code": "def calcular(x):\n    return x * 2",
  "symbol_map": {
    "version": "1.0",
    "symbols": [
      {"original": "calcular", "obfuscated": "_f0000", "kind": "function"},
      {"original": "x", "obfuscated": "_p0001", "kind": "parameter"}
    ]
  },
  "stats": {
    "lines_original": 2,
    "lines_obfuscated": 2,
    "identifiers_renamed": 2,
    "strings_ciphered": 0,
    "comments_removed": 0,
    "docstrings_removed": 0,
    "dead_code_inserted": 0,
    "symbols_total": 2
  },
  "verification": {
    "ran": true,
    "passed": true,
    "skipped": false,
    "skip_reason": null,
    "execution_time_original": 0.023,
    "execution_time_obfuscated": 0.031,
    "diff_lines": [],
    "error_message": null
  },
  "error": null
}
```

Si `success=false`, incluir `"error": "mensaje descriptivo"` y los demás campos pueden ser null.

**Implementación interna de `/api/obfuscate`:**

1. Validar que `code` no esté vacío.
2. Escribir `code` en un archivo temporal (`tempfile.NamedTemporaryFile` con sufijo `.py`).
3. Instanciar `Obfuscator` con la config recibida.
4. Llamar `obfuscator.obfuscate_source(code)` → `(obfuscated, symbol_map_dict, stats)`.
5. Si `verify=True`: escribir el obfuscado en otro archivo temporal, ejecutar `InvarianceChecker().verify(original_tmp, obfuscated_tmp)`.
6. Limpiar los archivos temporales (usar `try/finally`).
7. Serializar y retornar JSON.

**`POST /api/deobfuscate`**

Request body (JSON):
```json
{
  "code": "def _f0000(_p0001):\n    return _p0001 * 2",
  "symbol_map": { "version": "1.0", "symbols": [...] }
}
```

Response (JSON):
```json
{
  "success": true,
  "restored_code": "def calcular(x):\n    return x * 2",
  "error": null
}
```

**Implementación:** instanciar `Deobfuscator` desde el dict directamente (no desde archivo). Agregar un método de clase `Deobfuscator.from_dict(symbol_map_dict)` que construya la instancia sin leer un archivo.

**`GET /`**

Retornar el template `index.html`. Usar `flask.render_template("index.html")`.

**`GET /health`**

Retornar `{"status": "ok", "version": "1.0"}`. Útil para verificar que el servidor está corriendo.

### Manejo de errores en la UI

- Si la API retorna `success=false`: mostrar un banner rojo en el panel derecho con el mensaje de error.
- Si el fetch falla (servidor caído): mostrar "No se puede conectar al servidor. Verifica que `web.bat` está ejecutándose."
- Si el código Python tiene errores de sintaxis: la API debe detectarlo (el parser ANTLR fallará) y retornar un error descriptivo. La UI muestra: "Error de sintaxis Python en línea X: {mensaje}".

### Script de arranque: `web.bat`

```batch
@echo off
echo Iniciando CodeShield Web UI...
echo Abre http://localhost:5000 en tu navegador
echo Presiona Ctrl+C para detener
echo.
python -m src.web_app
```

### Modificar `requirements.txt`

Agregar:
```
flask==3.0.3
colorama==0.4.6
```

`colorama` es necesario para los colores ANSI en Windows en el output del verificador.

---

## Detalles de implementación críticos

### Archivos temporales en el verificador

El verificador necesita escribir código a disco para ejecutarlo con subprocess. Usar siempre `tempfile.NamedTemporaryFile(suffix='.py', delete=False, mode='w', encoding='utf-8')` y eliminar en el bloque `finally`. En Windows, `delete=True` puede fallar si el archivo está abierto por el subprocess — usar `delete=False` y eliminar manualmente.

```python
import tempfile, os

def _run_in_tempfile(self, code: str, args: list, stdin_data: str | None):
    tmp = tempfile.NamedTemporaryFile(suffix='.py', delete=False,
                                      mode='w', encoding='utf-8')
    try:
        tmp.write(code)
        tmp.flush()
        tmp.close()
        return self._execute(Path(tmp.name), args, stdin_data)
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
```

### Flask en modo desarrollo vs producción

El servidor Flask debe arrancar con `debug=False` y `threaded=True` en el entry point final. Durante desarrollo, el hot-reload está bien.

```python
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False, threaded=True)
```

### CORS

No es necesario — el frontend y el backend corren en el mismo origen (`localhost:5000`).

### Seguridad básica

La interfaz corre solo en `localhost`. No exponer en `0.0.0.0`. El código que el usuario ingresa se ejecuta en el mismo proceso — esto es aceptable para una herramienta de desarrollo local, pero documentarlo en el README.

### La UI debe funcionar sin conexión a internet

`highlight.js` se carga desde CDN. Si la máquina no tiene internet, el código se mostrará sin colores pero la funcionalidad seguirá operando. Documentar esto.

---

## Criterios de aceptación

La implementación se considera completa cuando:

**Verificador:**
- [ ] `InvarianceChecker.verify()` funciona con los 4 archivos de ejemplo del proyecto
- [ ] El flag `--verify` en el CLI muestra el resultado en terminal con colores
- [ ] El HTML generado con `--verify --html` incluye el banner de verificación
- [ ] El test de timeout no se cuelga (retorna en ≤ `timeout + 1` segundos)
- [ ] `tests/test_verifier.py` pasa completo

**Interfaz web:**
- [ ] `web.bat` arranca el servidor sin errores
- [ ] Abrir `http://localhost:5000` muestra la UI correctamente
- [ ] Pegar código Python, hacer click en "Ofuscar" y ver resultados funciona end-to-end
- [ ] La verificación de invariancia aparece en la UI si el checkbox estaba activo
- [ ] El botón "Copiar" funciona
- [ ] El botón "Descargar .py" descarga el archivo correcto
- [ ] La deofuscación desde la UI funciona
- [ ] El buscador de la tabla de símbolos filtra en tiempo real
- [ ] La UI es responsive en móvil (columna única)
- [ ] Si se pega código con error de sintaxis, la UI muestra un mensaje claro

---

## Notas para Claude Code

1. **Leer `CodeShield_SPEC.md` primero** para entender la arquitectura base antes de modificar cualquier archivo existente.

2. **No romper el CLI existente.** Todos los flags actuales deben seguir funcionando igual. Solo se agregan flags nuevos.

3. **El `Deobfuscator.from_dict()`** que requiere la API web puede no existir en la implementación actual. Si `Deobfuscator` solo acepta una ruta de archivo, agregar el método de clase sin modificar el comportamiento existente.

4. **El template `index.html`** debe ser un archivo completo y funcional — HTML, CSS y JS en un solo archivo. No crear archivos CSS o JS separados. Flask solo necesita servir el template y los endpoints de la API.

5. **Los colores ANSI en Windows** requieren `colorama.init()` al inicio de `main.py`. Agregar esa llamada solo si `colorama` está disponible (usar `try/except ImportError`).

6. **Implementar en este orden:**
   - Primero: `src/verifier/invariance_checker.py` con sus tests
   - Segundo: integración del verificador en el CLI y en el HTML viewer
   - Tercero: `src/web_app.py` y `src/templates/index.html`
   - Cuarto: `web.bat` y actualización de `requirements.txt` y `README.txt`

7. **Si el código original del usuario llama a `input()`** y no se pasa `--verify-stdin`, el verificador debe detectarlo y marcar como `skipped` en vez de colgarse esperando input.