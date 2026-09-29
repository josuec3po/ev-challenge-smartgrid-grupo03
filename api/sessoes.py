"""
Estruturas de dados e algoritmos do sistema de recarga (Sprint 4).

- Sessão de recarga  -> dataclass SessaoRecarga
- Armazenamento      -> list[SessaoRecarga] em memória, persistida em database.json
- Busca              -> busca linear implementada manualmente
- Ordenação          -> Insertion Sort e Merge Sort implementados manualmente
"""
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime

CAMINHO_DB = "database.json"
FORMATO_DATA = "%d/%m/%Y %H:%M"
CAMPOS_ORDENAVEIS = ("energia_kWh", "custo_total", "tempo_min", "data_hora", "id_sessao")


# ─────────────────────────────────────────────────────────────────────────────
# ESTRUTURA DE DADOS
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class SessaoRecarga:
    """Representa UMA sessão de recarga. Agrupa os dados relacionados em um único
    objeto, com acesso por atributo (sessao.energia_kWh) e conversão fácil para JSON."""
    id_sessao: int
    veiculo: str
    tipo_carregador: str
    energia_kWh: float
    tempo_min: int
    custo_total: float
    status: str
    data_hora: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> "SessaoRecarga":
        # int()/float() também aceitam registros antigos em que custo_total era string
        return SessaoRecarga(
            id_sessao=int(d.get("id_sessao", 0)),
            veiculo=str(d.get("veiculo", "—")),
            tipo_carregador=str(d.get("tipo_carregador", "—")),
            energia_kWh=float(d.get("energia_kWh", 0)),
            tempo_min=int(d.get("tempo_min", 0)),
            custo_total=float(d.get("custo_total", 0)),
            status=str(d.get("status", "CONCLUIDO")),
            data_hora=str(d.get("data_hora", "")),
        )


# ─────────────────────────────────────────────────────────────────────────────
# ARMAZENAMENTO (lista de objetos <-> database.json)
# ─────────────────────────────────────────────────────────────────────────────
def carregar_sessoes() -> list:
    """Lê o database.json e devolve uma LISTA de SessaoRecarga. Custo: O(n)."""
    if not os.path.exists(CAMINHO_DB):
        return []
    try:
        with open(CAMINHO_DB, "r", encoding="utf-8") as f:
            brutos = json.load(f)
    except json.JSONDecodeError:
        return []
    return [SessaoRecarga.from_dict(d) for d in brutos]


def salvar_sessoes(sessoes: list) -> None:
    """Grava a lista inteira no database.json. Custo: O(n)."""
    with open(CAMINHO_DB, "w", encoding="utf-8") as f:
        json.dump([s.to_dict() for s in sessoes], f, indent=4, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# BUSCA LINEAR — O(n)
# ─────────────────────────────────────────────────────────────────────────────
def busca_linear_por_id(sessoes: list, id_procurado: int):
    """
    Chave de busca: id_sessao.
    Percorre a lista uma sessão por vez, comparando o id.
    Termina quando ENCONTRA (melhor caso: 1 comparação, O(1))
    ou quando chega ao FIM da lista (pior caso: n comparações, O(n)).
    Retorna (sessao_ou_None, quantidade_de_comparacoes).
    """
    comparacoes = 0
    for sessao in sessoes:
        comparacoes += 1
        if sessao.id_sessao == id_procurado:
            return sessao, comparacoes
    return None, comparacoes


def busca_linear_por_veiculo(sessoes: list, trecho: str):
    """Busca por nome do veículo (contém o trecho). Precisa olhar TODAS as sessões,
    pois pode haver várias correspondências: sempre n comparações, O(n)."""
    encontradas = []
    comparacoes = 0
    trecho = trecho.lower()
    for sessao in sessoes:
        comparacoes += 1
        if trecho in sessao.veiculo.lower():
            encontradas.append(sessao)
    return encontradas, comparacoes


# ─────────────────────────────────────────────────────────────────────────────
# ORDENAÇÃO (implementação própria, sem list.sort() nem sorted())
# ─────────────────────────────────────────────────────────────────────────────
def _chave(sessao: SessaoRecarga, campo: str):
    """Extrai o valor do campo usado na comparação. A data vira datetime
    para ordenar cronologicamente (e não como texto)."""
    if campo == "data_hora":
        try:
            return datetime.strptime(sessao.data_hora, FORMATO_DATA)
        except ValueError:
            return datetime.min
    return getattr(sessao, campo)


def insertion_sort(sessoes: list, campo: str, decrescente: bool = False):
    """
    INSERTION SORT — pior/médio caso O(n²), melhor caso O(n) (lista já ordenada).
    Para cada elemento, compara com os anteriores e o "insere" na posição certa,
    deslocando os maiores uma casa para a direita. Dois laços aninhados -> n².
    Trabalha em uma CÓPIA: a lista original não é alterada.
    Retorna (lista_ordenada, comparacoes).
    """
    lista = list(sessoes)
    comparacoes = 0
    for i in range(1, len(lista)):
        atual = lista[i]
        chave_atual = _chave(atual, campo)
        j = i - 1
        while j >= 0:
            comparacoes += 1
            chave_j = _chave(lista[j], campo)
            fora_de_ordem = (chave_j < chave_atual) if decrescente else (chave_j > chave_atual)
            if not fora_de_ordem:
                break
            lista[j + 1] = lista[j]   # desloca para a direita
            j -= 1
        lista[j + 1] = atual          # insere na posição correta
    return lista, comparacoes


def merge_sort(sessoes: list, campo: str, decrescente: bool = False):
    """
    MERGE SORT — O(n log n) em todos os casos.
    Divide a lista ao meio recursivamente (~log n níveis) e, em cada nível,
    intercala as metades ordenadas percorrendo n elementos.
    Retorna (lista_ordenada, comparacoes).
    """
    contador = {"comparacoes": 0}

    def intercalar(esquerda, direita):
        resultado = []
        i = j = 0
        while i < len(esquerda) and j < len(direita):
            contador["comparacoes"] += 1
            a = _chave(esquerda[i], campo)
            b = _chave(direita[j], campo)
            pegar_esquerda = (a >= b) if decrescente else (a <= b)
            if pegar_esquerda:
                resultado.append(esquerda[i])
                i += 1
            else:
                resultado.append(direita[j])
                j += 1
        resultado.extend(esquerda[i:])
        resultado.extend(direita[j:])
        return resultado

    def ordenar(lista):
        if len(lista) <= 1:
            return lista
        meio = len(lista) // 2
        return intercalar(ordenar(lista[:meio]), ordenar(lista[meio:]))

    return ordenar(list(sessoes)), contador["comparacoes"]


# ─────────────────────────────────────────────────────────────────────────────
# ESTATÍSTICAS E RELATÓRIO — um único percurso pela lista: O(n)
# ─────────────────────────────────────────────────────────────────────────────
def calcular_estatisticas(sessoes: list) -> dict:
    if not sessoes:
        return {
            "total_sessoes": 0, "energia_total_kWh": 0, "energia_media_kWh": 0,
            "receita_total": 0, "ticket_medio": 0, "tempo_total_min": 0,
            "concluidas": 0, "parciais": 0, "maior_consumo": None, "menor_consumo": None,
        }
    energia_total = receita_total = 0.0
    tempo_total = concluidas = parciais = 0
    maior = menor = sessoes[0]

    for s in sessoes:
        energia_total += s.energia_kWh
        receita_total += s.custo_total
        tempo_total += s.tempo_min
        if s.status == "CONCLUIDO":
            concluidas += 1
        else:
            parciais += 1
        if s.energia_kWh > maior.energia_kWh:
            maior = s
        if s.energia_kWh < menor.energia_kWh:
            menor = s

    n = len(sessoes)
    return {
        "total_sessoes": n,
        "energia_total_kWh": round(energia_total, 2),
        "energia_media_kWh": round(energia_total / n, 2),
        "receita_total": round(receita_total, 2),
        "ticket_medio": round(receita_total / n, 2),
        "tempo_total_min": tempo_total,
        "concluidas": concluidas,
        "parciais": parciais,
        "maior_consumo": maior.to_dict(),
        "menor_consumo": menor.to_dict(),
    }


def gerar_relatorio_texto(sessoes: list) -> str:
    e = calcular_estatisticas(sessoes)
    if e["total_sessoes"] == 0:
        return "Nenhuma sessão registrada."
    mai, men = e["maior_consumo"], e["menor_consumo"]
    return "\n".join([
        "RELATÓRIO FINAL — GOODWE",
        "-" * 32,
        f'Sessões: {e["total_sessoes"]} ({e["concluidas"]} concluídas, {e["parciais"]} parciais)',
        f'Energia total: {e["energia_total_kWh"]:.2f} kWh (média {e["energia_media_kWh"]:.2f})',
        f'Receita total: R$ {e["receita_total"]:.2f} (ticket médio R$ {e["ticket_medio"]:.2f})',
        f'Tempo total de recarga: {e["tempo_total_min"]} min',
        f'Maior consumo: #{mai["id_sessao"]} {mai["veiculo"]} ({mai["energia_kWh"]:.2f} kWh)',
        f'Menor consumo: #{men["id_sessao"]} {men["veiculo"]} ({men["energia_kWh"]:.2f} kWh)',
    ])