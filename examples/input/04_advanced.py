"""Caso avanzado: decoradores, comprehensions, lambdas."""

from functools import wraps


def contar_llamadas(func):
    """Decorador que cuenta las invocaciones."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        wrapper.contador += 1
        return func(*args, **kwargs)
    wrapper.contador = 0
    return wrapper


@contar_llamadas
def cuadrado(x):
    return x ** 2


def procesar(numeros):
    pares = [n for n in numeros if n % 2 == 0]
    cuadrados = list(map(lambda x: cuadrado(x), pares))
    return {n: c for n, c in zip(pares, cuadrados)}


if __name__ == "__main__":
    datos = list(range(1, 11))
    resultado = procesar(datos)
    print("Resultados:")
    for k, v in sorted(resultado.items()):
        print(f"  {k} -> {v}")
    print(f"cuadrado() fue llamado {cuadrado.contador} veces")
