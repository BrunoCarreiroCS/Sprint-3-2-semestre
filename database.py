"""Persistencia em arquivos JSON com isolamento por usuario.

Estrutura gravada em ``pasta`` (por padrao, ``data/``):

- ``usuarios.json``: lista de perfis e contadores de identificadores.
- ``perfis/perfil_<id>.json``: analises, recomendacoes, comparacoes e pesos
  de um unico perfil. Excluir um perfil apaga apenas o arquivo dele.

Cada gravacao escreve primeiro em um arquivo temporario e so depois o move
para o lugar definitivo, para que uma falha no meio nao corrompa os dados.
"""

from __future__ import annotations

import copy
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from config import DADOS_DIR, VERSAO_ARMAZENAMENTO

NIVEIS_VALIDOS = {"iniciante", "intermediario", "avancado"}
ESTILOS_VALIDOS = {"natural", "equilibrado", "vibrante"}
MODOS_VALIDOS = {"hibrido", "offline"}
RESULTADOS_VALIDOS = {"sucesso", "misto", "falha", "inconclusivo"}

CAMPOS_RESUMO_ANALISE = ("id", "nome_arquivo", "objetivo", "intencao", "modo_execucao", "pontuacao_geral", "criado_em")

INDICE_VAZIO = {
    "versao": VERSAO_ARMAZENAMENTO,
    "proximo_id": {"usuario": 1, "analise": 1, "recomendacao": 1, "comparacao": 1},
    "usuarios": [],
}


class ArmazenamentoError(ValueError):
    """Arquivo de dados ilegivel, corrompido ou com formato inesperado."""


class RegistroDuplicadoError(ValueError):
    """Tentativa de gravar um registro que precisa ser unico."""


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- arquivos

def _arquivo_indice(pasta: str | Path) -> Path:
    return Path(pasta) / "usuarios.json"


def _arquivo_perfil(pasta: str | Path, usuario_id: int) -> Path:
    return Path(pasta) / "perfis" / f"perfil_{int(usuario_id)}.json"


def _perfil_vazio(usuario_id: int) -> dict:
    return {
        "versao": VERSAO_ARMAZENAMENTO, "usuario_id": int(usuario_id),
        "analises": [], "recomendacoes": [], "comparacoes": [], "pesos_aprendizado": [],
    }


def _ler_json(arquivo: Path, padrao: dict) -> dict:
    if not arquivo.exists():
        return copy.deepcopy(padrao)
    try:
        with open(arquivo, encoding="utf-8") as stream:
            dados = json.load(stream)
    except json.JSONDecodeError as exc:
        raise ArmazenamentoError(
            f"O arquivo de dados {arquivo.name} está corrompido (linha {exc.lineno}). "
            "Restaure uma cópia ou apague-o para recomeçar."
        ) from exc
    except OSError as exc:
        raise ArmazenamentoError(f"Não foi possível ler {arquivo.name}: {exc.strerror}.") from exc
    if not isinstance(dados, dict):
        raise ArmazenamentoError(f"O arquivo {arquivo.name} não tem o formato esperado.")
    for chave, valor in padrao.items():
        dados.setdefault(chave, copy.deepcopy(valor))
    return dados


def _gravar_json(arquivo: Path, dados: dict) -> None:
    arquivo.parent.mkdir(parents=True, exist_ok=True)
    temporario = arquivo.with_name(arquivo.name + ".tmp")
    try:
        with open(temporario, "w", encoding="utf-8") as stream:
            json.dump(dados, stream, ensure_ascii=False, indent=2)
        os.replace(temporario, arquivo)
    except OSError as exc:
        if temporario.exists():
            temporario.unlink()
        raise ArmazenamentoError(f"Não foi possível gravar {arquivo.name}: {exc.strerror}.") from exc


def _ler_indice(pasta: str | Path) -> dict:
    indice = _ler_json(_arquivo_indice(pasta), INDICE_VAZIO)
    for nome, valor in INDICE_VAZIO["proximo_id"].items():
        indice["proximo_id"].setdefault(nome, valor)
    return indice


def _ler_perfil(pasta: str | Path, usuario_id: int) -> dict:
    return _ler_json(_arquivo_perfil(pasta, usuario_id), _perfil_vazio(usuario_id))


def _reservar_ids(pasta: str | Path, tipo: str, quantidade: int = 1) -> list[int]:
    """Reserva identificadores unicos em todo o armazenamento."""
    indice = _ler_indice(pasta)
    inicio = int(indice["proximo_id"][tipo])
    indice["proximo_id"][tipo] = inicio + quantidade
    _gravar_json(_arquivo_indice(pasta), indice)
    return list(range(inicio, inicio + quantidade))


def _ids_usuarios(pasta: str | Path) -> list[int]:
    return [int(usuario["id"]) for usuario in _ler_indice(pasta)["usuarios"]]


def _localizar_analise(pasta: str | Path, analise_id: int) -> tuple[dict, dict] | None:
    """Encontra o perfil dono de uma analise; devolve (perfil, analise)."""
    for usuario_id in _ids_usuarios(pasta):
        perfil = _ler_perfil(pasta, usuario_id)
        for analise in perfil["analises"]:
            if analise["id"] == analise_id:
                return perfil, analise
    return None


# ---------------------------------------------------------------- perfis

def inicializar_armazenamento(pasta: str | Path = DADOS_DIR) -> None:
    """Cria a estrutura de pastas e valida o indice existente."""
    Path(pasta, "perfis").mkdir(parents=True, exist_ok=True)
    if not _arquivo_indice(pasta).exists():
        _gravar_json(_arquivo_indice(pasta), copy.deepcopy(INDICE_VAZIO))
    else:
        _ler_indice(pasta)


def criar_usuario(
    apelido: str,
    nivel: str,
    estilo: str,
    consentimento_api: bool,
    pasta: str | Path = DADOS_DIR,
) -> dict:
    apelido = str(apelido).strip()
    if nivel not in NIVEIS_VALIDOS or estilo not in ESTILOS_VALIDOS:
        raise ValueError("Nível ou estilo inválido.")
    indice = _ler_indice(pasta)
    if any(item["apelido"].casefold() == apelido.casefold() for item in indice["usuarios"]):
        raise RegistroDuplicadoError(f"O apelido '{apelido}' já está em uso.")
    usuario = {
        "id": int(indice["proximo_id"]["usuario"]), "apelido": apelido, "nivel": nivel,
        "estilo_preferido": estilo, "consentimento_api": bool(consentimento_api), "criado_em": agora_iso(),
    }
    indice["proximo_id"]["usuario"] = usuario["id"] + 1
    indice["usuarios"].append(usuario)
    _gravar_json(_arquivo_perfil(pasta, usuario["id"]), _perfil_vazio(usuario["id"]))
    _gravar_json(_arquivo_indice(pasta), indice)
    return dict(usuario)


def listar_usuarios(pasta: str | Path = DADOS_DIR) -> list[dict]:
    usuarios = _ler_indice(pasta)["usuarios"]
    return [dict(item) for item in sorted(usuarios, key=lambda item: item["apelido"].casefold())]


def buscar_usuario(usuario_id: int, pasta: str | Path = DADOS_DIR) -> dict | None:
    return next((dict(item) for item in _ler_indice(pasta)["usuarios"] if item["id"] == usuario_id), None)


def buscar_usuario_por_apelido(apelido: str, pasta: str | Path = DADOS_DIR) -> dict | None:
    alvo = str(apelido).strip().casefold()
    return next((dict(item) for item in _ler_indice(pasta)["usuarios"] if item["apelido"].casefold() == alvo), None)


def atualizar_consentimento(usuario_id: int, consentimento: bool, pasta: str | Path = DADOS_DIR) -> None:
    indice = _ler_indice(pasta)
    usuario = next((item for item in indice["usuarios"] if item["id"] == usuario_id), None)
    if usuario is None:
        raise ValueError("Usuário não encontrado.")
    usuario["consentimento_api"] = bool(consentimento)
    _gravar_json(_arquivo_indice(pasta), indice)


def excluir_usuario(usuario_id: int, pasta: str | Path = DADOS_DIR) -> None:
    """Remove o perfil e todo o historico dele (o arquivo inteiro do perfil)."""
    indice = _ler_indice(pasta)
    restantes = [item for item in indice["usuarios"] if item["id"] != usuario_id]
    if len(restantes) == len(indice["usuarios"]):
        raise ValueError("Usuário não encontrado.")
    indice["usuarios"] = restantes
    _gravar_json(_arquivo_indice(pasta), indice)
    arquivo = _arquivo_perfil(pasta, usuario_id)
    if arquivo.exists():
        arquivo.unlink()


# ---------------------------------------------------------------- analises

def salvar_analise_com_recomendacoes(
    analise: dict,
    recomendacoes: Sequence[dict],
    pasta: str | Path = DADOS_DIR,
) -> int:
    usuario_id = int(analise["usuario_id"])
    if buscar_usuario(usuario_id, pasta) is None:
        raise ValueError("Usuário não encontrado.")
    pontuacao = float(analise["pontuacao_geral"])
    if not 0 <= pontuacao <= 100:
        raise ValueError("Pontuação geral fora do intervalo 0-100.")
    if analise["modo_execucao"] not in MODOS_VALIDOS:
        raise ValueError("Modo de execução inválido.")

    perfil = _ler_perfil(pasta, usuario_id)
    analise_id = _reservar_ids(pasta, "analise")[0]
    ids_recomendacoes = _reservar_ids(pasta, "recomendacao", len(recomendacoes)) if recomendacoes else []
    perfil["analises"].append({
        "id": analise_id, "usuario_id": usuario_id, "imagem_hash": analise["imagem_hash"],
        "nome_arquivo": Path(analise["nome_arquivo"]).name, "objetivo": analise["objetivo"],
        "intencao": analise["intencao"], "estilo": analise["estilo"],
        "modo_execucao": analise["modo_execucao"], "metricas": analise["metricas"],
        "analise_ia": analise.get("analise_ia") or None, "pontuacao_geral": pontuacao,
        "eh_simulacao": bool(analise.get("eh_simulacao", False)), "criado_em": agora_iso(),
    })
    for posicao, (rec_id, rec) in enumerate(zip(ids_recomendacoes, recomendacoes), start=1):
        perfil["recomendacoes"].append({
            "id": rec_id, "analise_id": analise_id, "codigo_acao": rec["codigo_acao"],
            "posicao_ranking": posicao, "ganho_previsto": float(rec["ganho_previsto"]),
            "risco": rec["risco"], "esforco": rec["esforco"], "confianca": rec["confianca"],
            "explicacao": rec["explicacao"], "evidencias": list(rec.get("evidencias", [])),
            "peso_aprendido": float(rec.get("peso_aprendido", 1.0)),
            "selecionada": False, "marcado_em": None,
        })
    _gravar_json(_arquivo_perfil(pasta, usuario_id), perfil)
    return analise_id


def buscar_analise(analise_id: int, pasta: str | Path = DADOS_DIR) -> dict | None:
    encontrado = _localizar_analise(pasta, analise_id)
    return copy.deepcopy(encontrado[1]) if encontrado else None


def listar_analises(usuario_id: int, pasta: str | Path = DADOS_DIR) -> list[dict]:
    """Resumo das analises do perfil, da mais recente para a mais antiga."""
    analises = _ler_perfil(pasta, usuario_id)["analises"]
    resumo = [{campo: item.get(campo) for campo in CAMPOS_RESUMO_ANALISE} for item in analises]
    return sorted(resumo, key=lambda item: item["id"], reverse=True)


def listar_recomendacoes(analise_id: int, pasta: str | Path = DADOS_DIR) -> list[dict]:
    encontrado = _localizar_analise(pasta, analise_id)
    if not encontrado:
        return []
    perfil = encontrado[0]
    recomendacoes = [copy.deepcopy(item) for item in perfil["recomendacoes"] if item["analise_id"] == analise_id]
    return sorted(recomendacoes, key=lambda item: item["posicao_ranking"])


def marcar_recomendacao(recomendacao_id: int, analise_id: int, pasta: str | Path = DADOS_DIR) -> None:
    encontrado = _localizar_analise(pasta, analise_id)
    if not encontrado:
        raise ValueError("Recomendação não encontrada para esta análise.")
    perfil = encontrado[0]
    da_analise = [item for item in perfil["recomendacoes"] if item["analise_id"] == analise_id]
    alvo = next((item for item in da_analise if item["id"] == recomendacao_id), None)
    if alvo is None:
        raise ValueError("Recomendação não encontrada para esta análise.")
    for item in da_analise:
        item["selecionada"] = False
    alvo["selecionada"] = True
    alvo["marcado_em"] = agora_iso()
    _gravar_json(_arquivo_perfil(pasta, perfil["usuario_id"]), perfil)


def buscar_recomendacao_pendente(usuario_id: int, pasta: str | Path = DADOS_DIR) -> dict | None:
    """Recomendacao marcada mais recentemente que ainda nao tem uma recaptura comparada."""
    perfil = _ler_perfil(pasta, usuario_id)
    comparadas = {item["recomendacao_id"] for item in perfil["comparacoes"]}
    marcadas = [
        item for item in perfil["recomendacoes"]
        if item.get("marcado_em") and item["id"] not in comparadas
    ]
    if not marcadas:
        return None
    pendente = copy.deepcopy(max(marcadas, key=lambda item: (item["marcado_em"], item["id"])))
    analise = next(item for item in perfil["analises"] if item["id"] == pendente["analise_id"])
    for campo in ("nome_arquivo", "objetivo", "intencao", "estilo", "imagem_hash"):
        pendente[campo] = analise[campo]
    return pendente


# ---------------------------------------------------------------- aprendizado

def obter_pesos(usuario_id: int, contexto: str, pasta: str | Path = DADOS_DIR) -> dict[str, float]:
    pesos = _ler_perfil(pasta, usuario_id)["pesos_aprendizado"]
    return {item["codigo_acao"]: float(item["peso"]) for item in pesos if item["contexto_chave"] == contexto}


def obter_registro_peso(
    usuario_id: int, contexto: str, codigo_acao: str, pasta: str | Path = DADOS_DIR
) -> dict | None:
    pesos = _ler_perfil(pasta, usuario_id)["pesos_aprendizado"]
    registro = next(
        (item for item in pesos if item["contexto_chave"] == contexto and item["codigo_acao"] == codigo_acao),
        None,
    )
    return dict(registro) if registro else None


def registrar_comparacao(
    usuario_id: int,
    comparacao: dict,
    contexto: str,
    novo_peso: float,
    sucesso: bool,
    falha: bool,
    pasta: str | Path = DADOS_DIR,
) -> int:
    """Grava a comparacao e o peso atualizado na mesma escrita do arquivo do perfil."""
    if comparacao["resultado"] not in RESULTADOS_VALIDOS:
        raise ValueError("Resultado de comparação inválido.")
    if not 1 <= int(comparacao["avaliacao"]) <= 5:
        raise ValueError("A avaliação deve estar entre 1 e 5.")
    if not 0.5 <= float(novo_peso) <= 1.5:
        raise ValueError("O peso aprendido deve ficar entre 0,50 e 1,50.")

    perfil = _ler_perfil(pasta, usuario_id)
    chave = (comparacao["analise_antes_id"], comparacao["analise_depois_id"], comparacao["recomendacao_id"])
    if any((item["analise_antes_id"], item["analise_depois_id"], item["recomendacao_id"]) == chave
           for item in perfil["comparacoes"]):
        raise RegistroDuplicadoError("Essa comparação já foi registrada.")

    comparacao_id = _reservar_ids(pasta, "comparacao")[0]
    perfil["comparacoes"].append({
        "id": comparacao_id, "usuario_id": usuario_id,
        "analise_antes_id": comparacao["analise_antes_id"],
        "analise_depois_id": comparacao["analise_depois_id"],
        "recomendacao_id": comparacao["recomendacao_id"],
        "ganho_real": float(comparacao["ganho_real"]), "resultado": comparacao["resultado"],
        "avaliacao": int(comparacao["avaliacao"]), "comentario": str(comparacao.get("comentario", ""))[:500],
        "peso_aplicado": True, "criado_em": agora_iso(),
    })
    codigo_acao = comparacao["codigo_acao"]
    registro = next(
        (item for item in perfil["pesos_aprendizado"]
         if item["contexto_chave"] == contexto and item["codigo_acao"] == codigo_acao),
        None,
    )
    if registro is None:
        registro = {"contexto_chave": contexto, "codigo_acao": codigo_acao, "peso": 1.0, "sucessos": 0, "falhas": 0}
        perfil["pesos_aprendizado"].append(registro)
    registro["peso"] = round(float(novo_peso), 2)
    registro["sucessos"] += int(bool(sucesso))
    registro["falhas"] += int(bool(falha))
    registro["atualizado_em"] = agora_iso()
    _gravar_json(_arquivo_perfil(pasta, usuario_id), perfil)
    return comparacao_id


def listar_comparacoes(usuario_id: int, pasta: str | Path = DADOS_DIR) -> list[dict]:
    comparacoes = _ler_perfil(pasta, usuario_id)["comparacoes"]
    return sorted((dict(item) for item in comparacoes), key=lambda item: item["id"])


def listar_pesos(usuario_id: int, pasta: str | Path = DADOS_DIR) -> list[dict]:
    """Pesos aprendidos do perfil, do mais forte para o mais fraco."""
    pesos = [dict(item) for item in _ler_perfil(pasta, usuario_id)["pesos_aprendizado"]]
    return sorted(pesos, key=lambda item: (-item["peso"], -item["sucessos"]))
