from datetime import time


AULAS = (
    {"numero": 1, "nome": "1ª aula", "inicio": time(7, 10), "fim": time(8, 0)},
    {"numero": 2, "nome": "2ª aula", "inicio": time(8, 0), "fim": time(8, 50)},
    {"numero": 3, "nome": "3ª aula", "inicio": time(8, 50), "fim": time(9, 40)},
    {"numero": 4, "nome": "4ª aula", "inicio": time(9, 55), "fim": time(10, 45)},
    {"numero": 5, "nome": "5ª aula", "inicio": time(10, 45), "fim": time(11, 35)},
    {"numero": 6, "nome": "6ª aula", "inicio": time(11, 35), "fim": time(12, 25)},
    {"numero": 7, "nome": "7ª aula", "inicio": time(13, 30), "fim": time(14, 20)},
    {"numero": 8, "nome": "8ª aula", "inicio": time(14, 20), "fim": time(15, 10)},
    {"numero": 9, "nome": "9ª aula", "inicio": time(15, 10), "fim": time(16, 0)},
)

AULAS_CHOICES = tuple(
    (aula["numero"], f'{aula["nome"]} · {aula["inicio"]:%H:%M}–{aula["fim"]:%H:%M}')
    for aula in AULAS
)
AULAS_POR_NUMERO = {aula["numero"]: aula for aula in AULAS}


def aulas_que_sobrepoem(hora_inicio, hora_fim):
    return [
        aula["numero"]
        for aula in AULAS
        if aula["inicio"] < hora_fim and aula["fim"] > hora_inicio
    ]


