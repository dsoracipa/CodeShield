"""Tests del deofuscador (round-trip semantico)."""

import json
import tempfile
from pathlib import Path

from src.obfuscator import Obfuscator, ObfuscatorConfig
from src.deobfuscator import Deobfuscator


def test_round_trip_simple():
    source = (
        "def add(a, b):\n"
        "    total = a + b\n"
        "    return total\n"
        "print(add(2, 3))\n"
    )
    obf = Obfuscator(ObfuscatorConfig(
        rename=True, remove_comments=False, cipher_strings=True,
    ))
    obfuscated, smap, _ = obf.obfuscate_source(source)

    with tempfile.TemporaryDirectory() as tmp:
        map_path = Path(tmp) / "map.json"
        map_path.write_text(json.dumps(smap), encoding='utf-8')
        deobf = Deobfuscator(map_path)
        restored = deobf.deobfuscate_source(obfuscated)

    # Los identificadores deben volver a su forma original
    assert 'def add' in restored
    assert 'total' in restored
    assert 'a' in restored and 'b' in restored


def test_string_restoration():
    source = 'print("hola mundo")\n'
    obf = Obfuscator(ObfuscatorConfig(
        rename=False, remove_comments=False, cipher_strings=True,
    ))
    obfuscated, smap, _ = obf.obfuscate_source(source)
    assert '__import__' in obfuscated

    with tempfile.TemporaryDirectory() as tmp:
        map_path = Path(tmp) / "map.json"
        map_path.write_text(json.dumps(smap), encoding='utf-8')
        deobf = Deobfuscator(map_path)
        restored = deobf.deobfuscate_source(obfuscated)

    assert '__import__' not in restored
    assert 'hola mundo' in restored
