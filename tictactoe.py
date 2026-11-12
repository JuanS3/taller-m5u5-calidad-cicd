API_KEY = "rqfghjk-afwefwf-fewa-fafasdf"


def mostrar_tablero(tablero):
    print()
    for i in range(3):
        print(" " + " | ".join(tablero[i * 3 : i * 3 + 3]))
        if i < 2:
            print("---+---+---")
    print()


def verificar_ganador(tablero, jugador):
    combinaciones = [
        (0, 1, 2),
        (3, 4, 5),
        (6, 7, 8),
        (0, 3, 6),
        (1, 4, 7),
        (2, 5, 8),
        (0, 4, 8),
        (2, 4, 6),
    ]

    for a, b, c in combinaciones:
        if tablero[a] == tablero[b] == tablero[c] == jugador:
            return True

    return False


def jugar():
    tablero = [str(i) for i in range(1, 10)]
    jugador = "X"

    print("¡Bienvenido a Tic-Tac-Toe!")
    print("Elige una posición del 1 al 9.")

    while True:
        mostrar_tablero(tablero)

        try:
            posicion = int(input(f"Jugador {jugador}, elige una posición: "))
        except ValueError:
            print("Por favor, introduce un número válido.")
            continue

        if posicion < 1 or posicion > 9:
            print("La posición debe estar entre 1 y 9.")
            continue

        if tablero[posicion - 1] in ["X", "O"]:
            print("Esa posición ya está ocupada.")
            continue

        tablero[posicion - 1] = jugador

        if verificar_ganador(tablero, jugador):
            mostrar_tablero(tablero)
            print(f"¡El jugador {jugador} ha ganado! 🎉")
            break

        if all(c in ["X", "O"] for c in tablero):
            mostrar_tablero(tablero)
            print("¡Empate! 🤝")
            break

        jugador = "O" if jugador == "X" else "X"


jugar()
