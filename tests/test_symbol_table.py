"""Tests de SymbolTable."""

import json
from src.symbol_table import SymbolTable, Symbol


def test_add_new_symbol():
    st = SymbolTable()
    sym = st.add("foo", "function")
    assert isinstance(sym, Symbol)
    assert sym.original == "foo"
    assert sym.kind == "function"
    assert sym.obfuscated.startswith("_f")


def test_add_duplicate_returns_existing():
    st = SymbolTable()
    a = st.add("foo", "function")
    b = st.add("foo", "variable")
    assert a is b


def test_different_prefixes_by_kind():
    st = SymbolTable()
    f = st.add("fn", "function")
    v = st.add("vr", "variable")
    c = st.add("Cl", "class")
    p = st.add("pr", "parameter")
    assert f.obfuscated.startswith("_f")
    assert v.obfuscated.startswith("_v")
    assert c.obfuscated.startswith("_C")
    assert p.obfuscated.startswith("_p")


def test_get_and_has():
    st = SymbolTable()
    st.add("foo", "function")
    assert st.has("foo")
    assert st.get("foo") is not None
    assert not st.has("bar")
    assert st.get("bar") is None


def test_serialization_roundtrip():
    st = SymbolTable()
    st.add("foo", "function")
    st.add("bar", "variable")
    data = st.to_dict()
    serialized = json.dumps(data)
    restored = SymbolTable.from_dict(json.loads(serialized))
    assert restored.has("foo")
    assert restored.has("bar")
    assert restored.get("foo").kind == "function"
