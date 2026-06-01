"""Tests de eliminacion de comentarios y docstrings."""

from src.obfuscator import Obfuscator, ObfuscatorConfig


def _only_remove_comments(source: str) -> tuple[str, object]:
    obf = Obfuscator(ObfuscatorConfig(
        rename=False, remove_comments=True, cipher_strings=False,
    ))
    out, _, stats = obf.obfuscate_source(source)
    return out, stats


def test_hash_comments_removed():
    source = "x = 1  # comentario\nprint(x)  # otro\n"
    out, stats = _only_remove_comments(source)
    assert '# comentario' not in out
    assert '# otro' not in out
    assert stats.comments_removed == 2


def test_module_docstring_removed():
    source = (
        '"""Docstring del modulo."""\n'
        'x = 1\n'
    )
    out, stats = _only_remove_comments(source)
    assert 'Docstring' not in out
    assert stats.docstrings_removed == 1


def test_function_docstring_removed():
    source = (
        "def foo():\n"
        '    """Doc de foo."""\n'
        "    return 1\n"
    )
    out, stats = _only_remove_comments(source)
    assert 'Doc de foo' not in out
    assert stats.docstrings_removed == 1


def test_class_docstring_removed():
    source = (
        "class Foo:\n"
        '    """Doc de Foo."""\n'
        "    pass\n"
    )
    out, stats = _only_remove_comments(source)
    assert 'Doc de Foo' not in out
    assert stats.docstrings_removed == 1


def test_non_docstring_string_preserved():
    """Un string asignado a variable NO es docstring."""
    source = 'x = """es un valor"""\nprint(x)\n'
    out, stats = _only_remove_comments(source)
    assert 'es un valor' in out
    assert stats.docstrings_removed == 0
