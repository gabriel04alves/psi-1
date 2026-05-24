import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import DB_PATH, get_auditorias, get_normas, init_db

st.set_page_config(
    page_title="Importar / Exportar Base de Dados | PSI",
    page_icon="🗄️",
    layout="wide",
)
st.title("Gerenciar Base de Dados")
st.markdown("---")

TABELAS_ESPERADAS = {"auditorias", "respostas", "normas", "controles_norma", "empresa"}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _validar(data: bytes) -> tuple[bool, str, dict]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp = Path(f.name)
    tmp.write_bytes(data)
    try:
        conn = sqlite3.connect(str(tmp))
        tabelas = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        faltando = TABELAS_ESPERADAS - tabelas
        if faltando:
            conn.close()
            return False, f"Tabelas ausentes: {', '.join(sorted(faltando))}", {}
        stats = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABELAS_ESPERADAS}
        conn.close()
        return True, "OK", stats
    except Exception as e:
        return False, str(e), {}
    finally:
        tmp.unlink(missing_ok=True)


def _substituir(data: bytes):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        bk = DB_PATH.parent / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(DB_PATH, bk)
        st.info(f"Backup salvo: `{bk.name}`")
    DB_PATH.write_bytes(data)
    init_db()
    st.cache_data.clear()


def _mesclar(data: bytes) -> dict:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        tmp = Path(f.name)
    tmp.write_bytes(data)
    try:
        src = sqlite3.connect(str(tmp))
        src.row_factory = sqlite3.Row
        dst = sqlite3.connect(str(DB_PATH))
        dst.row_factory = sqlite3.Row

        contagem = {"normas": 0, "controles": 0, "auditorias": 0, "respostas": 0}

        # Normas — só insere se (nome, versao) não existe
        norma_map: dict[int, int] = {}
        for norma in src.execute("SELECT * FROM normas").fetchall():
            n = dict(norma)
            existe = dst.execute(
                "SELECT id FROM normas WHERE nome = ? AND versao = ?",
                (n["nome"], n.get("versao")),
            ).fetchone()
            if existe:
                norma_map[n["id"]] = existe[0]
            else:
                cur = dst.execute(
                    "INSERT INTO normas (nome, versao, origem, data_ingestao) VALUES (?, ?, ?, ?)",
                    (n["nome"], n.get("versao"), n.get("origem", "importado"), n["data_ingestao"]),
                )
                novo_id = cur.lastrowid
                norma_map[n["id"]] = novo_id
                contagem["normas"] += 1
                for ctrl in src.execute(
                    "SELECT * FROM controles_norma WHERE norma_id = ?", (n["id"],)
                ).fetchall():
                    c = dict(ctrl)
                    dst.execute(
                        """INSERT INTO controles_norma
                           (norma_id, controle_id, tema_id, tema_nome, nome, descricao)
                           VALUES (?, ?, ?, ?, ?, ?)""",
                        (novo_id, c["controle_id"], c["tema_id"], c.get("tema_nome"), c["nome"], c.get("descricao")),
                    )
                    contagem["controles"] += 1

        # Auditorias — sempre insere (gera novo ID)
        aud_map: dict[int, int] = {}
        for aud in src.execute("SELECT * FROM auditorias").fetchall():
            a = dict(aud)
            cur = dst.execute(
                "INSERT INTO auditorias (empresa, cnpj, modulo, data_inicio, data_fim, status) VALUES (?, ?, ?, ?, ?, ?)",
                (a["empresa"], a.get("cnpj"), a["modulo"], a["data_inicio"], a.get("data_fim"), a.get("status", "em_andamento")),
            )
            aud_map[a["id"]] = cur.lastrowid
            contagem["auditorias"] += 1

        # Respostas — remapeia auditoria_id
        for resp in src.execute("SELECT * FROM respostas").fetchall():
            r = dict(resp)
            novo_aud = aud_map.get(r["auditoria_id"])
            if novo_aud:
                dst.execute(
                    "INSERT INTO respostas (auditoria_id, controle_id, tema_id, status, observacao) VALUES (?, ?, ?, ?, ?)",
                    (novo_aud, r["controle_id"], r["tema_id"], r["status"], r.get("observacao", "")),
                )
                contagem["respostas"] += 1

        dst.commit()
        src.close()
        dst.close()
        st.cache_data.clear()
        return contagem
    finally:
        tmp.unlink(missing_ok=True)


# ── Exportar ───────────────────────────────────────────────────────────────────
st.subheader("Exportar Base de Dados")

if DB_PATH.exists():
    c1, c2, c3 = st.columns(3)
    try:
        auditorias = get_auditorias()
        normas = get_normas()
        c1.metric("Auditorias", len(auditorias))
        c2.metric("Normas carregadas", len(normas))
        c3.metric("Tamanho", f"{DB_PATH.stat().st_size / 1024:.1f} KB")
    except Exception:
        st.warning("Base de dados com problema. Verifique ou importe uma nova abaixo.")

    with open(DB_PATH, "rb") as f:
        db_bytes = f.read()
    st.download_button(
        label="Baixar base de dados (.db)",
        data=db_bytes,
        file_name=f"auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db",
        mime="application/octet-stream",
        icon="⬇️",
        use_container_width=True,
    )
else:
    st.info("Nenhuma base de dados encontrada. Uma nova será criada ao iniciar o uso.")

st.markdown("---")

# ── Importar ───────────────────────────────────────────────────────────────────
st.subheader("Importar Base de Dados")
st.caption(
    "Selecione um arquivo `.db` exportado de outra instância do PSI. "
    "Você pode substituir completamente ou mesclar os dados ao banco atual."
)

uploaded = st.file_uploader("Arquivo .db", type=["db"])

if uploaded:
    data = uploaded.read()
    ok, msg, stats = _validar(data)

    if not ok:
        st.error(f"Arquivo inválido: {msg}")
    else:
        st.success("Arquivo validado com sucesso.")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Auditorias", stats["auditorias"])
        c2.metric("Respostas",  stats["respostas"])
        c3.metric("Normas",     stats["normas"])
        c4.metric("Controles",  stats["controles_norma"])
        c5.metric("Empresa",    "Sim" if stats["empresa"] > 0 else "Não")

        st.markdown("**Como deseja importar?**")
        modo = st.radio(
            "Modo de importação",
            ["Substituir (apaga o banco atual)", "Mesclar (combina com o banco atual)"],
            label_visibility="collapsed",
        )
        substituir = modo.startswith("Substituir")

        if substituir:
            st.warning(
                "**Substituir:** a base de dados atual será completamente apagada e substituída. "
                "Um backup automático será criado antes da operação."
            )
        else:
            st.info(
                "**Mesclar:** as auditorias e normas do arquivo serão adicionadas ao banco atual. "
                "Normas com o mesmo nome e versão não serão duplicadas. "
                "Os dados de empresa do banco atual são mantidos."
            )

        if st.button("Confirmar Importação", type="primary", use_container_width=True):
            if substituir:
                _substituir(data)
                st.success("Base de dados substituída com sucesso!")
            else:
                contagem = _mesclar(data)
                st.success(
                    f"Mesclagem concluída: "
                    f"**{contagem['auditorias']}** auditoria(s), "
                    f"**{contagem['normas']}** norma(s) e "
                    f"**{contagem['respostas']}** resposta(s) adicionadas."
                )
            st.balloons()
            st.rerun()
