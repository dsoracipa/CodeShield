class Persona:
    """Representa una persona con nombre y edad."""

    def __init__(self, nombre, edad):
        self.nombre = nombre
        self.edad = edad

    def saludar(self):
        return f"Hola, soy {self.nombre} y tengo {self.edad} anos"


class Estudiante(Persona):
    def __init__(self, nombre, edad, carrera):
        super().__init__(nombre, edad)
        self.carrera = carrera

    def presentarse(self):
        base = self.saludar()
        return f"{base}. Estudio {self.carrera}"


def main():
    estudiantes = [
        Estudiante("Ana", 20, "Sistemas"),
        Estudiante("Luis", 22, "Mecanica"),
    ]
    for est in estudiantes:
        print(est.presentarse())


if __name__ == "__main__":
    main()
