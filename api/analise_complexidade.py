"""Uso (na raiz do projeto): python -m api.analise_complexidade"""
import random
import time
from api.sessoes import SessaoRecarga, busca_linear_por_id, insertion_sort, merge_sort


def gerar(n):
    return [
        SessaoRecarga(i, f"Carro {i}", "AC", round(random.uniform(1, 100), 2),
                      random.randint(10, 300), round(random.uniform(10, 300), 2),
                      "CONCLUIDO", "01/01/2026 10:00")
        for i in range(1, n + 1)
    ]


def medir(func, *args):
    inicio = time.perf_counter()
    resultado = func(*args)
    return resultado[-1], (time.perf_counter() - inicio) * 1000


print(f'{"n":>6} | {"Busca":>10} | {"Insertion":>12} {"ms":>9} | {"Merge":>10} {"ms":>8}')
print("-" * 68)
for n in (100, 500, 1000, 2000):
    sessoes = gerar(n)
    c_busca, _ = medir(busca_linear_por_id, sessoes, -1)            # pior caso: id inexistente
    c_ins, t_ins = medir(insertion_sort, sessoes, "energia_kWh")
    c_mer, t_mer = medir(merge_sort, sessoes, "energia_kWh")
    print(f"{n:>6} | {c_busca:>10} | {c_ins:>12} {t_ins:>9.1f} | {c_mer:>10} {t_mer:>8.1f}")