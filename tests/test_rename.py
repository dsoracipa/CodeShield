"""Tests del renombrado de identificadores."""

from src.obfuscator import Obfuscator, ObfuscatorConfig


def _rename_only(source: str) -> tuple[str, dict]:
    obf = Obfuscator(ObfuscatorConfig(
        rename=True, remove_comments=False, cipher_strings=False,
    ))
    out, smap, _ = obf.obfuscate_source(source)
    return out, smap


def test_simple_variable_renamed():
    source = "x = 42\nprint(x)\n"
    out, smap = _rename_only(source)
    syms = {s['original']: s for s in smap['symbols']}
    assert 'x' in syms
    obf_x = syms['x']['obfuscated']
    assert obf_x in out
    assert 'x = 42' not in out  # 'x' fue renombrado


def test_function_renamed():
    source = "def add(a, b):\n    return a + b\nadd(1, 2)\n"
    out, smap = _rename_only(source)
    syms = {s['original']: s['kind'] for s in smap['symbols']}
    assert syms.get('add') == 'function'
    assert syms.get('a') == 'parameter'
    assert syms.get('b') == 'parameter'


def test_class_renamed():
    source = "class Foo:\n    pass\nFoo()\n"
    out, smap = _rename_only(source)
    syms = {s['original']: s['kind'] for s in smap['symbols']}
    assert syms.get('Foo') == 'class'


def test_method_not_renamed():
    """Los metodos (def dentro de class) NO se renombran porque
    su acceso es via obj.metodo y los atributos no se tocan."""
    source = (
        "class Foo:\n"
        "    def bar(self):\n"
        "        return 1\n"
        "f = Foo()\n"
        "print(f.bar())\n"
    )
    out, smap = _rename_only(source)
    syms = {s['original']: s['kind'] for s in smap['symbols']}
    assert 'bar' not in syms
    assert 'def bar(self):' in out


def test_attribute_not_renamed():
    """El atributo .x NO se debe renombrar aunque el receptor si."""
    source = (
        "class Foo:\n    pass\n"
        "f = Foo()\n"
        "f.x = 5\n"
        "print(f.x)\n"
    )
    out, smap = _rename_only(source)
    # `f` es variable y debe renombrarse; `x` es atributo y debe preservarse.
    syms = {s['original'] for s in smap['symbols']}
    assert 'f' in syms
    assert 'x' not in syms
    assert '.x = 5' in out
    assert '.x)' in out


def test_builtin_not_renamed():
    source = "print(len([1, 2, 3]))\n"
    out, _ = _rename_only(source)
    assert 'print(' in out
    assert 'len(' in out


def test_imports_not_renamed():
    source = (
        "import os\n"
        "from typing import List\n"
        "x = os.path.join('a', 'b')\n"
        "y: List = []\n"
    )
    out, _ = _rename_only(source)
    assert 'os.path' in out
    assert 'List' in out


def test_dunder_not_renamed():
    source = (
        "class Foo:\n"
        "    def __init__(self):\n"
        "        self.x = 1\n"
    )
    out, _ = _rename_only(source)
    assert '__init__' in out
