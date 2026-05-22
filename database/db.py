import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "auditoria.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS auditorias (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa     TEXT NOT NULL,
            cnpj        TEXT,
            modulo      TEXT NOT NULL,
            data_inicio TEXT NOT NULL,
            data_fim    TEXT,
            status      TEXT DEFAULT 'em_andamento'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS respostas (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            auditoria_id INTEGER NOT NULL,
            controle_id  TEXT NOT NULL,
            tema_id      TEXT NOT NULL,
            status       TEXT NOT NULL,
            observacao   TEXT,
            FOREIGN KEY (auditoria_id) REFERENCES auditorias(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS normas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT NOT NULL,
            versao        TEXT,
            origem        TEXT DEFAULT 'importado',
            data_ingestao TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS controles_norma (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            norma_id    INTEGER NOT NULL,
            controle_id TEXT NOT NULL,
            tema_id     TEXT NOT NULL,
            tema_nome   TEXT,
            nome        TEXT NOT NULL,
            descricao   TEXT,
            FOREIGN KEY (norma_id) REFERENCES normas(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS empresa (
            id            INTEGER PRIMARY KEY CHECK (id = 1),
            nome          TEXT NOT NULL,
            cnpj          TEXT,
            razao_social  TEXT,
            setor         TEXT,
            porte         TEXT,
            responsavel   TEXT,
            atualizado_em TEXT NOT NULL
        )
    """)
    conn.commit()
    _migrar_empresa(conn)
    conn.close()


def _migrar_empresa(conn):
    colunas = {row[1] for row in conn.execute("PRAGMA table_info(empresa)")}
    remover = {"endereco", "cidade", "estado", "telefone", "email", "site"}
    for col in remover & colunas:
        conn.execute(f"ALTER TABLE empresa DROP COLUMN {col}")
    conn.commit()


def salvar_norma(nome: str, versao: str, controles: list[dict]) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    data_ingestao = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO normas (nome, versao, origem, data_ingestao) VALUES (?, ?, 'importado', ?)",
        (nome, versao, data_ingestao),
    )
    norma_id = cursor.lastrowid
    for c in controles:
        cursor.execute(
            """INSERT INTO controles_norma
               (norma_id, controle_id, tema_id, tema_nome, nome, descricao)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                norma_id,
                c["id"],
                c["tema"],
                c.get("tema_nome", ""),
                c["nome"],
                c.get("descricao", ""),
            ),
        )
    conn.commit()
    conn.close()
    return norma_id


def get_normas() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM normas ORDER BY data_ingestao DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_controles_norma(norma_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM controles_norma WHERE norma_id = ? ORDER BY controle_id",
        (norma_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_empresa() -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM empresa WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else None


def salvar_empresa(dados: dict):
    conn = get_connection()
    atualizado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existe = conn.execute("SELECT id FROM empresa WHERE id = 1").fetchone()
    if existe:
        conn.execute(
            """UPDATE empresa SET
                   nome=:nome, cnpj=:cnpj, razao_social=:razao_social,
                   setor=:setor, porte=:porte, responsavel=:responsavel,
                   atualizado_em=:atualizado_em
               WHERE id = 1""",
            {**dados, "atualizado_em": atualizado_em},
        )
    else:
        conn.execute(
            """INSERT INTO empresa
                   (id, nome, cnpj, razao_social, setor, porte, responsavel, atualizado_em)
               VALUES (1, :nome, :cnpj, :razao_social, :setor, :porte, :responsavel, :atualizado_em)""",
            {**dados, "atualizado_em": atualizado_em},
        )
    conn.commit()
    conn.close()


def get_auditorias() -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM auditorias ORDER BY data_inicio DESC"
    ).fetchall()
    result = []
    for row in rows:
        a = dict(row)
        a["total_respostas"] = conn.execute(
            "SELECT COUNT(*) FROM respostas WHERE auditoria_id = ?", (a["id"],)
        ).fetchone()[0]
        norma = conn.execute(
            "SELECT id FROM normas WHERE nome = ?", (a["modulo"],)
        ).fetchone()
        if norma:
            a["total_controles"] = conn.execute(
                "SELECT COUNT(*) FROM controles_norma WHERE norma_id = ?", (norma[0],)
            ).fetchone()[0]
        else:
            a["total_controles"] = 0
        result.append(a)
    conn.close()
    return result


def deletar_auditoria(auditoria_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM respostas WHERE auditoria_id = ?", (auditoria_id,))
    conn.execute("DELETE FROM auditorias WHERE id = ?", (auditoria_id,))
    conn.commit()
    conn.close()


def deletar_norma(norma_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM controles_norma WHERE norma_id = ?", (norma_id,))
    conn.execute("DELETE FROM normas WHERE id = ?", (norma_id,))
    conn.commit()
    conn.close()


def criar_auditoria(empresa: str, cnpj: str, modulo: str) -> int:
    """Cria uma nova auditoria e retorna o ID."""
    conn = get_connection()
    cursor = conn.cursor()
    data_inicio = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO auditorias (empresa, cnpj, modulo, data_inicio) VALUES (?, ?, ?, ?)",
        (empresa, cnpj, modulo, data_inicio),
    )
    auditoria_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return auditoria_id


def salvar_resposta(
    auditoria_id: int, controle_id: str, tema_id: str, status: str, observacao: str = ""
):
    """Salva ou atualiza a resposta de um controle."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT id FROM respostas WHERE auditoria_id = ? AND controle_id = ?",
        (auditoria_id, controle_id),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE respostas SET status = ?, observacao = ? WHERE id = ?",
            (status, observacao, existing["id"]),
        )
    else:
        conn.execute(
            "INSERT INTO respostas (auditoria_id, controle_id, tema_id, status, observacao) VALUES (?, ?, ?, ?, ?)",
            (auditoria_id, controle_id, tema_id, status, observacao),
        )
    conn.commit()
    conn.close()


def finalizar_auditoria(auditoria_id: int):
    """Marca a auditoria como concluída."""
    conn = get_connection()
    data_fim = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE auditorias SET status = 'concluida', data_fim = ? WHERE id = ?",
        (data_fim, auditoria_id),
    )
    conn.commit()
    conn.close()


def get_progresso_auditoria(auditoria_id: int, total_controles: int) -> dict:
    """Retorna quantos controles já foram respondidos."""
    conn = get_connection()
    respondidos = conn.execute(
        "SELECT COUNT(*) as cnt FROM respostas WHERE auditoria_id = ?",
        (auditoria_id,),
    ).fetchone()["cnt"]
    conn.close()
    return {
        "respondidos": respondidos,
        "total": total_controles,
        "percentual": (
            round(respondidos / total_controles * 100, 1) if total_controles else 0
        ),
    }


def get_respostas_auditoria(auditoria_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM respostas WHERE auditoria_id = ? ORDER BY controle_id",
        (auditoria_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


init_db()
