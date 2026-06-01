"""Tests de identificadores protegidos."""

from src.protected_names import is_protected, is_dunder


def test_builtins_protected():
    assert is_protected("print")
    assert is_protected("len")
    assert is_protected("range")


def test_exceptions_protected():
    assert is_protected("Exception")
    assert is_protected("ValueError")


def test_constants_protected():
    assert is_protected("True")
    assert is_protected("False")
    assert is_protected("None")


def test_conventional_params_protected():
    assert is_protected("self")
    assert is_protected("cls")


def test_dunders_protected():
    assert is_protected("__init__")
    assert is_protected("__str__")
    assert is_dunder("__init__")
    assert not is_dunder("__")
    assert not is_dunder("init")


def test_user_names_not_protected():
    assert not is_protected("foo")
    assert not is_protected("my_variable")
    assert not is_protected("Calculator")


def test_keywords_protected():
    assert is_protected("def")
    assert is_protected("class")
    assert is_protected("import")


def test_empty_and_underscore():
    assert is_protected("")
    assert is_protected("_")
