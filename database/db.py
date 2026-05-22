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
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS auditorias (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa     TEXT NOT NULL,
            cnpj        TEXT,
            modulo      TEXT NOT NULL,
            data_inicio TEXT NOT NULL,
            data_fim    TEXT,
            status      TEXT DEFAULT 'em_andamento'
        );

        CREATE TABLE IF NOT EXISTS respostas (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            auditoria_id INTEGER NOT NULL,
            controle_id  TEXT NOT NULL,
            tema_id      TEXT NOT NULL,
            status       TEXT NOT NULL,
            observacao   TEXT,
            FOREIGN KEY (auditoria_id) REFERENCES auditorias(id)
        );
    """)
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
