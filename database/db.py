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


init_db()
