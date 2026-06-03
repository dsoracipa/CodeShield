# Demo de 1 minuto — CodeShield

> Objetivo: mostrar en ~60 segundos que la herramienta ofusca código Python real,
> que el resultado sigue ejecutando igual, y que el proceso es reversible.

---

## Preparación (antes de la demo, no contar el tiempo)

```bat
cd C:\Users\DANIEL\Documents\UNI\sem 9\lenguajes\proyecto
```

Asegurarse de tener el entorno activo: `pip install -r requirements.txt`

---

## Secuencia de comandos

### Paso 1 — Mostrar el código original (10 seg)

```bat
type examples\input\01_simple.py
```

**Lo que se ve:** función `calcular_promedio`, variable `valores`, `resultado`. Código limpio y legible.

---

### Paso 2 — Ofuscar y generar HTML (15 seg)

```bat
python -m src.main obfuscate examples\input\01_simple.py --html -v
```

**Lo que ocurre:**
- Se muestra la tabla de símbolos en consola: `calcular_promedio → _f0001`, `valores → _v0001`, etc.
- Se generan `01_simple_obfuscated.py` y `01_simple_comparison.html`.

Abrir el HTML en el navegador (doble clic en el archivo generado).  
**Impacto visual:** comparativa lado a lado, código original vs. ofuscado con names crípticos y strings en Base64.

---

### Paso 3 — Verificar invariancia semántica (15 seg)

```bat
python examples\input\01_simple.py
python examples\input\01_simple_obfuscated.py
```

**Lo que se demuestra:** ambos imprimen exactamente `El promedio es: 25.0`. El código ofuscado ejecuta idéntico.

---

### Paso 4 — Deofuscar y restaurar (10 seg)

```bat
python -m src.main deobfuscate examples\input\01_simple_obfuscated.py ^
    -m examples\input\01_simple_symbol_map.json
```

```bat
type examples\input\01_simple_restored.py
```

**Lo que se demuestra:** el archivo restaurado recupera los nombres originales a partir del `symbol_map.json`.

---

## Total: ~50 segundos + reacciones del público

---

## Frases clave para decir durante la demo

- *"La ofuscación usa un parser real generado con ANTLR sobre la gramática oficial de Python 3.13 — no expresiones regulares."*
- *"El patrón Visitor recorre el árbol sintáctico para identificar cada identificador definido por el usuario."*
- *"El código ofuscado ejecuta idéntico al original — lo verificamos con tests de invariancia semántica."*
- *"El proceso es completamente reversible: quien tenga el `symbol_map.json` puede restaurar el código."*

---

## Si sobra tiempo (~10 seg extra)

Mostrar el ejemplo más complejo:

```bat
python -m src.main obfuscate examples\input\04_advanced.py --html
```

Abrir el HTML para mostrar que funciona con decoradores, lambdas y comprensiones.

---

## Archivos que se generan (para no perderlos antes de la demo)

| Archivo | Descripción |
|---------|-------------|
| `examples/input/01_simple_obfuscated.py` | Código ofuscado |
| `examples/input/01_simple_symbol_map.json` | Mapa de símbolos |
| `examples/input/01_simple_comparison.html` | Visor comparativo |
| `examples/input/01_simple_restored.py` | Código restaurado |
