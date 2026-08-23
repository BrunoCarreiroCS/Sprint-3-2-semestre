"""Persistencia SQLite com isolamento por usuario."""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Sequence

from config import DB_PATH, ensure_directories


class ClosingConnection(sqlite3.Connection):
    """Conexao que tambem fecha o arquivo ao sair de um bloco ``with``."""

    def __exit__(self, exc_type, exc_value, traceback):
        resultado = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return resultado


def agora_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def conectar(caminho: str | Path = DB_PATH) -> sqlite3.Connection:
    ensure_directories()
    conn = sqlite3.connect(str(caminho), factory=ClosingConnection)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transacao(caminho: str | Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    conn = conectar(caminho)
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def inicializar_banco(caminho: str | Path = DB_PATH) -> None:
    schema = """
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        apelido TEXT NOT NULL COLLATE NOCASE UNIQUE,
        nivel TEXT NOT NULL CHECK (nivel IN ('iniciante','intermediario','avancado')),
        estilo_preferido TEXT NOT NULL CHECK (estilo_preferido IN ('natural','equilibrado','vibrante')),
        consentimento_api INTEGER NOT NULL DEFAULT 0 CHECK (consentimento_api IN (0,1)),
        criado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS analises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        imagem_hash TEXT NOT NULL,
        nome_arquivo TEXT NOT NULL,
        objetivo TEXT NOT NULL,
        intencao TEXT NOT NULL,
        estilo TEXT NOT NULL,
        modo_execucao TEXT NOT NULL CHECK (modo_execucao IN ('hibrido','offline')),
        metricas_json TEXT NOT NULL,
        analise_ia_json TEXT,
        pontuacao_geral REAL NOT NULL CHECK (pontuacao_geral BETWEEN 0 AND 100),
        eh_simulacao INTEGER NOT NULL DEFAULT 0 CHECK (eh_simulacao IN (0,1)),
        criado_em TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS recomendacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        analise_id INTEGER NOT NULL REFERENCES analises(id) ON DELETE CASCADE,
        codigo_acao TEXT NOT NULL,
        posicao_ranking INTEGER NOT NULL,
        ganho_previsto REAL NOT NULL,
        risco TEXT NOT NULL,
        esforco TEXT NOT NULL,
        confianca TEXT NOT NULL,
        explicacao TEXT NOT NULL,
        evidencias_json TEXT NOT NULL,
        peso_aprendido REAL NOT NULL DEFAULT 1.0,
        selecionada INTEGER NOT NULL DEFAULT 0 CHECK (selecionada IN (0,1)),
        marcado_em TEXT,
        UNIQUE (analise_id, posicao_ranking)
    );
    CREATE TABLE IF NOT EXISTS comparacoes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        analise_antes_id INTEGER NOT NULL REFERENCES analises(id) ON DELETE CASCADE,
        analise_depois_id INTEGER NOT NULL REFERENCES analises(id) ON DELETE CASCADE,
        recomendacao_id INTEGER NOT NULL REFERENCES recomendacoes(id) ON DELETE CASCADE,
        ganho_real REAL NOT NULL,
        resultado TEXT NOT NULL CHECK (resultado IN ('sucesso','misto','falha','inconclusivo')),
        avaliacao INTEGER NOT NULL CHECK (avaliacao BETWEEN 1 AND 5),
        comentario TEXT,
        peso_aplicado INTEGER NOT NULL DEFAULT 0 CHECK (peso_aplicado IN (0,1)),
        criado_em TEXT NOT NULL,
        UNIQUE (analise_antes_id, analise_depois_id, recomendacao_id)
    );
    CREATE TABLE IF NOT EXISTS pesos_aprendizado (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
        contexto_chave TEXT NOT NULL,
        codigo_acao TEXT NOT NULL,
        peso REAL NOT NULL DEFAULT 1.0 CHECK (peso BETWEEN 0.5 AND 1.5),
        sucessos INTEGER NOT NULL DEFAULT 0,
        falhas INTEGER NOT NULL DEFAULT 0,
        atualizado_em TEXT NOT NULL,
        UNIQUE (usuario_id, contexto_chave, codigo_acao)
    );
    CREATE INDEX IF NOT EXISTS idx_analises_usuario ON analises(usuario_id, criado_em DESC);
    CREATE INDEX IF NOT EXISTS idx_comparacoes_usuario ON comparacoes(usuario_id, criado_em DESC);
    """
    with transacao(caminho) as conn:
        conn.executescript(schema)
        colunas = {row["name"] for row in conn.execute("PRAGMA table_info(recomendacoes)")}
        if "peso_aprendido" not in colunas:
            conn.execute("ALTER TABLE recomendacoes ADD COLUMN peso_aprendido REAL NOT NULL DEFAULT 1.0")
        if "marcado_em" not in colunas:
            conn.execute("ALTER TABLE recomendacoes ADD COLUMN marcado_em TEXT")


def _row_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def criar_usuario(
    apelido: str,
    nivel: str,
    estilo: str,
    consentimento_api: bool,
    caminho: str | Path = DB_PATH,
) -> dict:
    with transacao(caminho) as conn:
        cursor = conn.execute(
            "INSERT INTO usuarios(apelido,nivel,estilo_preferido,consentimento_api,criado_em) VALUES(?,?,?,?,?)",
            (apelido, nivel, estilo, int(consentimento_api), agora_iso()),
        )
        row = conn.execute("SELECT * FROM usuarios WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return dict(row)


def listar_usuarios(caminho: str | Path = DB_PATH) -> list[dict]:
    with conectar(caminho) as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM usuarios ORDER BY apelido")]


def buscar_usuario(usuario_id: int, caminho: str | Path = DB_PATH) -> dict | None:
    with conectar(caminho) as conn:
        return _row_dict(conn.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone())


def atualizar_consentimento(usuario_id: int, consentimento: bool, caminho: str | Path = DB_PATH) -> None:
    with transacao(caminho) as conn:
        cursor = conn.execute(
            "UPDATE usuarios SET consentimento_api = ? WHERE id = ?",
            (int(consentimento), usuario_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Usuario nao encontrado.")


def salvar_analise_com_recomendacoes(
    analise: dict,
    recomendacoes: Sequence[dict],
    caminho: str | Path = DB_PATH,
) -> int:
    with transacao(caminho) as conn:
        cursor = conn.execute(
            """INSERT INTO analises(
                usuario_id,imagem_hash,nome_arquivo,objetivo,intencao,estilo,modo_execucao,
                metricas_json,analise_ia_json,pontuacao_geral,eh_simulacao,criado_em
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                analise["usuario_id"], analise["imagem_hash"], Path(analise["nome_arquivo"]).name,
                analise["objetivo"], analise["intencao"], analise["estilo"], analise["modo_execucao"],
                json.dumps(analise["metricas"], ensure_ascii=False),
                json.dumps(analise.get("analise_ia"), ensure_ascii=False) if analise.get("analise_ia") else None,
                float(analise["pontuacao_geral"]), int(analise.get("eh_simulacao", False)), agora_iso(),
            ),
        )
        analise_id = int(cursor.lastrowid)
        for posicao, rec in enumerate(recomendacoes, start=1):
            conn.execute(
                """INSERT INTO recomendacoes(
                    analise_id,codigo_acao,posicao_ranking,ganho_previsto,risco,esforco,
                    confianca,explicacao,evidencias_json,peso_aprendido
                ) VALUES(?,?,?,?,?,?,?,?,?,?)""",
                (
                    analise_id, rec["codigo_acao"], posicao, float(rec["ganho_previsto"]),
                    rec["risco"], rec["esforco"], rec["confianca"], rec["explicacao"],
                    json.dumps(rec.get("evidencias", []), ensure_ascii=False),
                    float(rec.get("peso_aprendido", 1.0)),
                ),
            )
    return analise_id


def buscar_analise(analise_id: int, caminho: str | Path = DB_PATH) -> dict | None:
    with conectar(caminho) as conn:
        row = conn.execute("SELECT * FROM analises WHERE id = ?", (analise_id,)).fetchone()
    if row is None:
        return None
    result = dict(row)
    result["metricas"] = json.loads(result.pop("metricas_json"))
    raw_ia = result.pop("analise_ia_json")
    result["analise_ia"] = json.loads(raw_ia) if raw_ia else None
    return result


def listar_analises(usuario_id: int, caminho: str | Path = DB_PATH) -> list[dict]:
    with conectar(caminho) as conn:
        rows = conn.execute(
            "SELECT id,nome_arquivo,objetivo,intencao,modo_execucao,pontuacao_geral,criado_em FROM analises WHERE usuario_id = ? ORDER BY id DESC",
            (usuario_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def listar_recomendacoes(analise_id: int, caminho: str | Path = DB_PATH) -> list[dict]:
    with conectar(caminho) as conn:
        rows = conn.execute(
            "SELECT * FROM recomendacoes WHERE analise_id = ? ORDER BY posicao_ranking",
            (analise_id,),
        ).fetchall()
    result = []
    for row in rows:
        item = dict(row)
        item["evidencias"] = json.loads(item.pop("evidencias_json"))
        result.append(item)
    return result


def marcar_recomendacao(recomendacao_id: int, analise_id: int, caminho: str | Path = DB_PATH) -> None:
    with transacao(caminho) as conn:
        conn.execute("UPDATE recomendacoes SET selecionada = 0 WHERE analise_id = ?", (analise_id,))
        cursor = conn.execute(
            "UPDATE recomendacoes SET selecionada = 1, marcado_em = ? WHERE id = ? AND analise_id = ?",
            (agora_iso(), recomendacao_id, analise_id),
        )
        if cursor.rowcount != 1:
            raise ValueError("Recomendacao nao encontrada para esta analise.")


def buscar_recomendacao_pendente(usuario_id: int, caminho: str | Path = DB_PATH) -> dict | None:
    """Recomendacao marcada mais recentemente que ainda nao tem uma recaptura comparada."""
    with conectar(caminho) as conn:
        row = conn.execute(
            """SELECT r.*, a.nome_arquivo, a.objetivo, a.intencao, a.estilo, a.imagem_hash
            FROM recomendacoes r
            JOIN analises a ON a.id = r.analise_id
            WHERE a.usuario_id = ?
              AND r.marcado_em IS NOT NULL
              AND NOT EXISTS (SELECT 1 FROM comparacoes c WHERE c.recomendacao_id = r.id)
            ORDER BY r.marcado_em DESC
            LIMIT 1""",
            (usuario_id,),
        ).fetchone()
    if row is None:
        return None
    item = dict(row)
    item["evidencias"] = json.loads(item.pop("evidencias_json"))
    return item


def obter_pesos(usuario_id: int, contexto: str, caminho: str | Path = DB_PATH) -> dict[str, float]:
    with conectar(caminho) as conn:
        rows = conn.execute(
            "SELECT codigo_acao,peso FROM pesos_aprendizado WHERE usuario_id = ? AND contexto_chave = ?",
            (usuario_id, contexto),
        ).fetchall()
    return {row["codigo_acao"]: float(row["peso"]) for row in rows}


def excluir_usuario(usuario_id: int, caminho: str | Path = DB_PATH) -> None:
    with transacao(caminho) as conn:
        cursor = conn.execute("DELETE FROM usuarios WHERE id = ?", (usuario_id,))
        if cursor.rowcount != 1:
            raise ValueError("Usuario nao encontrado.")
