def calcular_promedio(numeros):
    """Calcula el promedio de una lista de numeros."""
    total = sum(numeros)
    cantidad = len(numeros)
    return total / cantidad


# Programa principal
valores = [10, 20, 30, 40]
resultado = calcular_promedio(valores)
print(f"El promedio es: {resultado}")
