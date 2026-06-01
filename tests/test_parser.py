"""Verifica que el parser ANTLR generado funciona correctamente."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'generated'))

from antlr4 import InputStream, CommonTokenStream  # noqa: E402
from PythonLexer import PythonLexer  # noqa: E402
from PythonParser import PythonParser  # noqa: E402


def _parse(code: str):
    if not code.endswith('\n'):
        code += '\n'
    stream = InputStream(code)
    lexer = PythonLexer(stream)
    tokens = CommonTokenStream(lexer)
    parser = PythonParser(tokens)
    return parser.file_input()


def test_parse_simple_assignment():
    tree = _parse("x = 42\nprint(x)\n")
    assert tree is not None


def test_parse_function_def():
    tree = _parse("def add(a, b):\n    return a + b\n")
    assert tree is not None


def test_parse_class():
    tree = _parse("class A:\n    def m(self):\n        pass\n")
    assert tree is not None


def test_parse_imports():
    code = "import os\nfrom collections import OrderedDict as OD\n"
    tree = _parse(code)
    assert tree is not None


if __name__ == '__main__':
    test_parse_simple_assignment()
    test_parse_function_def()
    test_parse_class()
    test_parse_imports()
    print("Parser OK")
