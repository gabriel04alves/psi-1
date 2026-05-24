import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / "data" / "auditoria.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _criar_tabelas(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS empresa (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT NOT NULL,
            cnpj          TEXT,
            razao_social  TEXT,
            setor         TEXT,
            porte         TEXT,
            responsavel   TEXT,
            atualizado_em TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS normas (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nome          TEXT NOT NULL,
            versao        TEXT,
            origem        TEXT DEFAULT 'importado',
            data_ingestao TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS controles_norma (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            norma_id    INTEGER NOT NULL,
            controle_id TEXT NOT NULL,
            tema_id     TEXT NOT NULL,
            tema_nome   TEXT,
            nome        TEXT NOT NULL,
            descricao   TEXT,
            FOREIGN KEY (norma_id) REFERENCES normas(id)
        );

        CREATE TABLE IF NOT EXISTS auditorias (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id  INTEGER NOT NULL,
            norma_id    INTEGER NOT NULL,
            data_inicio TEXT NOT NULL,
            data_fim    TEXT,
            status      TEXT DEFAULT 'em_andamento',
            FOREIGN KEY (empresa_id) REFERENCES empresa(id),
            FOREIGN KEY (norma_id)   REFERENCES normas(id)
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


def _migrar(conn):
    """Detecta schema antigo e descarta tabelas incompatíveis."""
    cols_aud = {row[1] for row in conn.execute("PRAGMA table_info(auditorias)")}
    if "empresa_id" not in cols_aud:
        conn.executescript("""
            DROP TABLE IF EXISTS respostas;
            DROP TABLE IF EXISTS auditorias;
            DROP TABLE IF EXISTS empresa;
        """)
        conn.commit()
        _criar_tabelas(conn)


def init_db():
    conn = get_connection()
    _criar_tabelas(conn)
    _migrar(conn)
    conn.close()


# ── Empresa ────────────────────────────────────────────────────────────────────


def get_empresas() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            e.*,
            COUNT(a.id)                                                        AS total_auditorias,
            COALESCE(SUM(a.status = 'concluida'),   0)                         AS n_concluidas,
            COALESCE(SUM(a.status = 'em_andamento'), 0)                        AS n_andamento
        FROM empresa e
        LEFT JOIN auditorias a ON a.empresa_id = e.id
        GROUP BY e.id
        ORDER BY e.nome
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_empresa_by_id(empresa_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute("SELECT * FROM empresa WHERE id = ?", (empresa_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def criar_empresa(dados: dict) -> int:
    conn = get_connection()
    atualizado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """INSERT INTO empresa (nome, cnpj, razao_social, setor, porte, responsavel, atualizado_em)
           VALUES (:nome, :cnpj, :razao_social, :setor, :porte, :responsavel, :atualizado_em)""",
        {**dados, "atualizado_em": atualizado_em},
    )
    empresa_id = cur.lastrowid
    conn.commit()
    conn.close()
    return empresa_id


def atualizar_empresa(empresa_id: int, dados: dict):
    conn = get_connection()
    atualizado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        """UPDATE empresa SET
               nome=:nome, cnpj=:cnpj, razao_social=:razao_social,
               setor=:setor, porte=:porte, responsavel=:responsavel,
               atualizado_em=:atualizado_em
           WHERE id=:id""",
        {**dados, "id": empresa_id, "atualizado_em": atualizado_em},
    )
    conn.commit()
    conn.close()


def deletar_empresa(empresa_id: int):
    conn = get_connection()
    ids = [
        r["id"]
        for r in conn.execute(
            "SELECT id FROM auditorias WHERE empresa_id = ?", (empresa_id,)
        ).fetchall()
    ]
    for aid in ids:
        conn.execute("DELETE FROM respostas  WHERE auditoria_id = ?", (aid,))
    conn.execute("DELETE FROM auditorias WHERE empresa_id = ?", (empresa_id,))
    conn.execute("DELETE FROM empresa     WHERE id          = ?", (empresa_id,))
    conn.commit()
    conn.close()


def get_empresa() -> dict | None:
    """Get a company profile by name. Returns the company with matching nome."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM empresa LIMIT 1").fetchone()
    conn.close()
    return dict(row) if row else None


def get_empresa_by_name(nome: str) -> dict | None:
    """Get a company by name. Returns company data including ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM empresa WHERE nome = ?", (nome,)).fetchone()
    conn.close()
    return dict(row) if row else None


def salvar_empresa(dados: dict, nome_original: str | None = None) -> int:
    """
    Save or update a company.

    Args:
        dados: Company data dictionary with 'nome', 'cnpj', 'razao_social', 'setor', 'porte', 'responsavel'
        nome_original: If provided and different from dados['nome'], performs an update.
                       If not provided or same as dados['nome'], creates if not exists or updates existing.

    Returns:
        The ID of the saved/updated company
    """
    conn = get_connection()
    nome_novo = dados.get("nome", "")
    atualizado_em = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if nome_original and nome_original != nome_novo:
        existing = conn.execute(
            "SELECT id FROM empresa WHERE nome = ?", (nome_original,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE empresa SET
                       nome=:nome, cnpj=:cnpj, razao_social=:razao_social,
                       setor=:setor, porte=:porte, responsavel=:responsavel,
                       atualizado_em=:atualizado_em
                   WHERE id=:id""",
                {**dados, "id": existing["id"], "atualizado_em": atualizado_em},
            )
            empresa_id = existing["id"]
        else:
            cur = conn.execute(
                """INSERT INTO empresa (nome, cnpj, razao_social, setor, porte, responsavel, atualizado_em)
                   VALUES (:nome, :cnpj, :razao_social, :setor, :porte, :responsavel, :atualizado_em)""",
                {**dados, "atualizado_em": atualizado_em},
            )
            empresa_id = cur.lastrowid
    else:
        existing = conn.execute(
            "SELECT id FROM empresa WHERE nome = ?", (nome_novo,)
        ).fetchone()
        if existing:
            conn.execute(
                """UPDATE empresa SET
                       nome=:nome, cnpj=:cnpj, razao_social=:razao_social,
                       setor=:setor, porte=:porte, responsavel=:responsavel,
                       atualizado_em=:atualizado_em
                   WHERE id=:id""",
                {**dados, "id": existing["id"], "atualizado_em": atualizado_em},
            )
            empresa_id = existing["id"]
        else:
            # Create new company
            cur = conn.execute(
                """INSERT INTO empresa (nome, cnpj, razao_social, setor, porte, responsavel, atualizado_em)
                   VALUES (:nome, :cnpj, :razao_social, :setor, :porte, :responsavel, :atualizado_em)""",
                {**dados, "atualizado_em": atualizado_em},
            )
            empresa_id = cur.lastrowid

    conn.commit()
    conn.close()
    return empresa_id


# ── Normas


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
    rows = conn.execute("SELECT * FROM normas ORDER BY data_ingestao DESC").fetchall()
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


def deletar_norma(norma_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM controles_norma WHERE norma_id = ?", (norma_id,))
    conn.execute("DELETE FROM normas          WHERE id       = ?", (norma_id,))
    conn.commit()
    conn.close()


# ── Auditorias

_AUDITORIAS_SELECT = """
    SELECT
        a.id,
        a.empresa_id,
        a.norma_id,
        a.data_inicio,
        a.data_fim,
        a.status,
        e.nome         AS empresa,
        e.cnpj,
        e.razao_social,
        e.setor,
        e.porte,
        e.responsavel,
        n.nome         AS modulo
    FROM auditorias a
    JOIN empresa e ON e.id = a.empresa_id
    JOIN normas  n ON n.id = a.norma_id
"""


def _enriquecer(conn, rows) -> list[dict]:
    result = []
    for row in rows:
        a = dict(row)
        a["total_respostas"] = conn.execute(
            "SELECT COUNT(*) FROM respostas WHERE auditoria_id = ?", (a["id"],)
        ).fetchone()[0]
        a["total_controles"] = conn.execute(
            "SELECT COUNT(*) FROM controles_norma WHERE norma_id = ?", (a["norma_id"],)
        ).fetchone()[0]
        result.append(a)
    return result


def get_auditorias(empresa_id: int | None = None) -> list[dict]:
    conn = get_connection()
    if empresa_id is not None:
        rows = conn.execute(
            _AUDITORIAS_SELECT + " WHERE a.empresa_id = ? ORDER BY a.data_inicio DESC",
            (empresa_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            _AUDITORIAS_SELECT + " ORDER BY a.data_inicio DESC"
        ).fetchall()
    result = _enriquecer(conn, rows)
    conn.close()
    return result


def criar_auditoria(empresa_id: int, norma_id: int) -> int:
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO auditorias (empresa_id, norma_id, data_inicio) VALUES (?, ?, ?)",
        (empresa_id, norma_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    auditoria_id = cur.lastrowid
    conn.commit()
    conn.close()
    return auditoria_id


def deletar_auditoria(auditoria_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM respostas  WHERE auditoria_id = ?", (auditoria_id,))
    conn.execute("DELETE FROM auditorias WHERE id           = ?", (auditoria_id,))
    conn.commit()
    conn.close()


def finalizar_auditoria(auditoria_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE auditorias SET status = 'concluida', data_fim = ? WHERE id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), auditoria_id),
    )
    conn.commit()
    conn.close()


def get_analise_auditoria(auditoria_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        _AUDITORIAS_SELECT + " WHERE a.id = ?", (auditoria_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    aud = dict(row)
    rows = conn.execute(
        """
        SELECT
            r.controle_id,
            r.tema_id,
            r.status,
            r.observacao,
            COALESCE(cn.tema_nome, r.tema_id)    AS tema_nome,
            COALESCE(cn.nome,      r.controle_id) AS controle_nome,
            COALESCE(cn.descricao, '')             AS descricao
        FROM respostas r
        LEFT JOIN controles_norma cn
               ON cn.norma_id = :norma_id AND cn.controle_id = r.controle_id
        WHERE r.auditoria_id = :aud_id
        ORDER BY r.controle_id
        """,
        {"norma_id": aud["norma_id"], "aud_id": auditoria_id},
    ).fetchall()
    conn.close()
    return {"auditoria": aud, "respostas": [dict(r) for r in rows]}


def get_progresso_auditoria(auditoria_id: int, total_controles: int) -> dict:
    conn = get_connection()
    respondidos = conn.execute(
        "SELECT COUNT(*) AS cnt FROM respostas WHERE auditoria_id = ?", (auditoria_id,)
    ).fetchone()["cnt"]
    conn.close()
    return {
        "respondidos": respondidos,
        "total": total_controles,
        "percentual": (
            round(respondidos / total_controles * 100, 1) if total_controles else 0
        ),
    }


def salvar_resposta(
    auditoria_id: int, controle_id: str, tema_id: str, status: str, observacao: str = ""
):
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
            "INSERT INTO respostas (auditoria_id, controle_id, tema_id, status, observacao)"
            " VALUES (?, ?, ?, ?, ?)",
            (auditoria_id, controle_id, tema_id, status, observacao),
        )
    conn.commit()
    conn.close()


def get_respostas_auditoria(auditoria_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM respostas WHERE auditoria_id = ? ORDER BY controle_id",
        (auditoria_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


init_db()
