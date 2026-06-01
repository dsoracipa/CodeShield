"""Sistema simple de gestion de inventario."""

import json


def cargar_inventario(productos):
    """Convierte lista de productos a dict indexado por id."""
    return {p["id"]: p for p in productos}


def filtrar_bajo_stock(inventario, umbral):
    return [p for p in inventario.values() if p["stock"] < umbral]


def calcular_valor_total(inventario):
    return sum(p["precio"] * p["stock"] for p in inventario.values())


def imprimir_reporte(inventario, umbral_bajo):
    valor_total = calcular_valor_total(inventario)
    bajos = filtrar_bajo_stock(inventario, umbral_bajo)
    print("=== REPORTE DE INVENTARIO ===")
    print(f"Valor total: ${valor_total:,.2f}")
    print(f"Productos con stock bajo (<{umbral_bajo}):")
    for prod in bajos:
        print(f"  - {prod['nombre']} (stock: {prod['stock']})")


if __name__ == "__main__":
    productos = [
        {"id": 1, "nombre": "Laptop", "precio": 2500.0, "stock": 3},
        {"id": 2, "nombre": "Mouse", "precio": 25.0, "stock": 50},
        {"id": 3, "nombre": "Teclado", "precio": 80.0, "stock": 2},
        {"id": 4, "nombre": "Monitor", "precio": 350.0, "stock": 8},
    ]
    inv = cargar_inventario(productos)
    imprimir_reporte(inv, umbral_bajo=5)
