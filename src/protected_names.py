"""Identificadores que nunca deben ser renombrados por el ofuscador.

Categorias protegidas:
- Built-ins de Python (print, len, range, ...)
- Excepciones del lenguaje (Exception, ValueError, ...)
- Constantes del lenguaje (True, False, None)
- Parametros convencionales (self, cls)
- Metodos dunder (__init__, __str__, ...)
- Keywords de Python (def, class, ...)
"""

PYTHON_BUILTINS: set[str] = {
    # tipos
    'int', 'str', 'float', 'bool', 'list', 'dict', 'tuple', 'set',
    'frozenset', 'bytes', 'bytearray', 'complex', 'object', 'type',
    'memoryview', 'range', 'slice',
    # funciones built-in
    'print', 'input', 'len', 'open', 'abs', 'all', 'any', 'min', 'max',
    'sum', 'sorted', 'reversed', 'enumerate', 'zip', 'map', 'filter',
    'iter', 'next', 'round', 'pow', 'divmod', 'hash', 'id', 'repr',
    'format', 'chr', 'ord', 'bin', 'hex', 'oct', 'callable',
    'isinstance', 'issubclass', 'hasattr', 'getattr', 'setattr', 'delattr',
    'vars', 'dir', 'globals', 'locals', 'help', 'exit', 'quit',
    'super', 'property', 'staticmethod', 'classmethod', 'compile',
    'eval', 'exec', 'breakpoint', 'ascii',
    # excepciones built-in
    'BaseException', 'Exception', 'ArithmeticError', 'AssertionError',
    'AttributeError', 'BlockingIOError', 'BrokenPipeError', 'BufferError',
    'BytesWarning', 'ChildProcessError', 'ConnectionAbortedError',
    'ConnectionError', 'ConnectionRefusedError', 'ConnectionResetError',
    'DeprecationWarning', 'EOFError', 'EnvironmentError', 'FileExistsError',
    'FileNotFoundError', 'FloatingPointError', 'FutureWarning',
    'GeneratorExit', 'IOError', 'ImportError', 'ImportWarning',
    'IndentationError', 'IndexError', 'InterruptedError', 'IsADirectoryError',
    'KeyError', 'KeyboardInterrupt', 'LookupError', 'MemoryError',
    'ModuleNotFoundError', 'NameError', 'NotADirectoryError', 'NotImplemented',
    'NotImplementedError', 'OSError', 'OverflowError', 'PendingDeprecationWarning',
    'PermissionError', 'ProcessLookupError', 'RecursionError', 'ReferenceError',
    'ResourceWarning', 'RuntimeError', 'RuntimeWarning', 'StopAsyncIteration',
    'StopIteration', 'SyntaxError', 'SyntaxWarning', 'SystemError', 'SystemExit',
    'TabError', 'TimeoutError', 'TypeError', 'UnboundLocalError',
    'UnicodeDecodeError', 'UnicodeEncodeError', 'UnicodeError',
    'UnicodeTranslateError', 'UnicodeWarning', 'UserWarning', 'ValueError',
    'Warning', 'WindowsError', 'ZeroDivisionError',
    # constantes
    'True', 'False', 'None', 'Ellipsis', '__debug__',
    # atributos especiales del modulo
    '__name__', '__main__', '__file__', '__doc__', '__path__', '__package__',
    '__loader__', '__spec__', '__builtins__',
}

CONVENTIONAL_PARAMS: set[str] = {'self', 'cls'}

PYTHON_KEYWORDS: set[str] = {
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
    'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
    'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
    'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while',
    'with', 'yield', 'match', 'case', 'type',
}


def is_dunder(name: str) -> bool:
    """True si el nombre es de la forma __nombre__."""
    return name.startswith('__') and name.endswith('__') and len(name) > 4


def is_protected(name: str) -> bool:
    """True si el identificador no debe ser renombrado."""
    if not name:
        return True
    if name == '_':
        return True
    if name in PYTHON_BUILTINS:
        return True
    if name in CONVENTIONAL_PARAMS:
        return True
    if name in PYTHON_KEYWORDS:
        return True
    if is_dunder(name):
        return True
    return False
