"""Tests de cifrado de strings."""

import base64

from src.obfuscator import Obfuscator, ObfuscatorConfig


def _only_cipher(source: str) -> tuple[str, object]:
    obf = Obfuscator(ObfuscatorConfig(
        rename=False, remove_comments=False, cipher_strings=True,
    ))
    out, _, stats = obf.obfuscate_source(source)
    return out, stats


def test_simple_string_ciphered():
    source = 'x = "hola"\n'
    out, stats = _only_cipher(source)
    assert '"hola"' not in out
    assert '__import__' in out
    assert stats.strings_ciphered == 1
    # Verificar que el base64 corresponde a 'hola'
    assert base64.b64encode(b'hola').decode() in out


def test_fstring_not_ciphered():
    source = 'x = 5\ny = f"x = {x}"\n'
    out, stats = _only_cipher(source)
    assert 'f"x = {' in out  # f-string preservado


def test_raw_string_not_ciphered():
    source = r'x = r"\nhola"' + '\n'
    out, stats = _only_cipher(source)
    assert r'r"\nhola"' in out


def test_byte_string_not_ciphered():
    source = 'x = b"bytes"\n'
    out, stats = _only_cipher(source)
    assert 'b"bytes"' in out


def test_string_with_escapes():
    source = 'print("hola\\nmundo")\n'
    out, _ = _only_cipher(source)
    # Verificar que el base64 corresponde a 'hola\nmundo'
    assert base64.b64encode("hola\nmundo".encode('utf-8')).decode() in out


def test_empty_string_ciphered():
    source = 'x = ""\n'
    out, stats = _only_cipher(source)
    assert stats.strings_ciphered == 1
