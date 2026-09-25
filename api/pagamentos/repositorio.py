"""
Persistência das cobranças em JSON, na mesma pegada do database.json
que o grupo já usa — mas com duas correções que faltavam lá:

1. Lock de escrita. Sem ele, dois requests simultâneos leem a mesma lista
   e um sobrescreve o outro (o salvar-historico atual tem esse problema).
2. Índice por chave de idempotência, para não cobrar duas vezes.

Quando entrar banco de verdade, troque só esta classe: SQLModel ou
SQLAlchemy com a mesma interface pública.
"""

import json
import os
import threading
from pathlib import Path

from api.pagamentos.models import Cobranca

CAMINHO_PADRAO = Path(os.getenv("PAGAMENTOS_DB", "data/pagamentos.json"))


class RepositorioCobrancas:
    def __init__(self, caminho: Path = CAMINHO_PADRAO):
        self.caminho = Path(caminho)
        self._lock = threading.Lock()
        self.caminho.parent.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------- leitura
    def _carregar(self) -> dict[str, dict]:
        if not self.caminho.exists():
            return {}
        try:
            with self.caminho.open(encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            # Arquivo corrompido não pode derrubar a API. Preserva o original
            # para inspeção em vez de sobrescrever silenciosamente.
            corrompido = self.caminho.with_suffix(".corrompido.json")
            self.caminho.replace(corrompido)
            return {}

    def _gravar(self, dados: dict[str, dict]) -> None:
        temporario = self.caminho.with_suffix(".tmp")
        with temporario.open("w", encoding="utf-8") as f:
            json.dump(dados, f, indent=2, ensure_ascii=False, default=str)
        temporario.replace(self.caminho)  # escrita atômica

    # ---------------------------------------------------------------- API
    def salvar(self, cobranca: Cobranca) -> Cobranca:
        with self._lock:
            dados = self._carregar()
            dados[cobranca.id] = json.loads(cobranca.model_dump_json())
            self._gravar(dados)
        return cobranca

    def buscar(self, id_cobranca: str) -> Cobranca | None:
        registro = self._carregar().get(id_cobranca)
        return Cobranca.model_validate(registro) if registro else None

    def buscar_por_idempotencia(self, chave: str) -> Cobranca | None:
        for registro in self._carregar().values():
            if registro.get("chave_idempotencia") == chave:
                return Cobranca.model_validate(registro)
        return None

    def buscar_por_id_provedor(self, id_provedor: str) -> Cobranca | None:
        for registro in self._carregar().values():
            if registro.get("id_provedor") == id_provedor:
                return Cobranca.model_validate(registro)
        return None

    def listar_por_sessao(self, id_sessao: int) -> list[Cobranca]:
        return [
            Cobranca.model_validate(r)
            for r in self._carregar().values()
            if r.get("id_sessao") == id_sessao
        ]

    def listar(self) -> list[Cobranca]:
        return [Cobranca.model_validate(r) for r in self._carregar().values()]
