import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import deletar_auditoria, get_auditorias

st.set_page_config(page_title="Dashboard | PSI", page_icon="📊", layout="wide")

# ── Header
st.title("Dashboard de Auditorias")
st.markdown("---")

empresa_selecionada = st.session_state.get("empresa_selecionada")

if not empresa_selecionada:
    st.warning("Nenhuma empresa selecionada.")
    st.page_link("pages/1_Empresa.py", label="Selecionar Empresa", icon="🏢")
    st.stop()

st.markdown(f"Empresa: **{empresa_selecionada}**")
st.markdown("---")

# ── Dados
if "confirmar_exclusao" not in st.session_state:
    st.session_state.confirmar_exclusao = None

auditorias = [a for a in get_auditorias() if a["empresa"] == empresa_selecionada]

# ── Métricas de resumo
total = len(auditorias)
concluidas = sum(1 for a in auditorias if a["status"] == "concluida")
em_andamento = sum(1 for a in auditorias if a["status"] == "em_andamento")

col1, col2, col3 = st.columns(3)
col1.metric("Total de auditorias", total)
col2.metric("Concluídas", concluidas)
col3.metric("Em andamento", em_andamento)

st.markdown("---")

# ── Lista de auditorias
st.subheader("Auditorias")

if not auditorias:
    st.markdown(
        """
        <div style='
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 40px 28px;
            text-align: center;
            margin-top: 8px;
        '>
            <div style='font-size: 40px; margin-bottom: 12px'>📋</div>
            <div style='font-size: 18px; font-weight: 600; color: #1e293b; margin-bottom: 8px'>
                Nenhuma auditoria registrada
            </div>
            <div style='font-size: 14px; color: #64748b'>
                Inicie uma nova auditoria na página <strong>Nova Auditoria</strong>
                para visualizar os resultados aqui.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link("pages/3_Nova_Auditoria.py", label="Ir para Nova Auditoria", icon="🔍")
else:
    STATUS_LABEL = {
        "concluida": ("Concluída", "#22c55e", "#f0fdf4"),
        "em_andamento": ("Em andamento", "#f59e0b", "#fffbeb"),
    }

    for aud in auditorias:
        status_txt, status_color, status_bg = STATUS_LABEL.get(
            aud["status"], (aud["status"], "#94a3b8", "#f8fafc")
        )

        total_c = aud["total_controles"]
        respondidos = aud["total_respostas"]
        pct = round(respondidos / total_c * 100) if total_c else 0
        progresso_bar = "█" * (pct // 5) + "░" * (20 - pct // 5)

        data_inicio = aud["data_inicio"][:10]
        data_fim = aud["data_fim"][:10] if aud["data_fim"] else "—"
        cnpj_txt = aud["cnpj"] if aud["cnpj"] else "—"

        with st.container(border=True):
            col_info, col_acoes = st.columns([5, 1])

            with col_info:
                st.markdown(
                    f"""
                    <div style='margin-bottom:4px'>
                        <span style='
                            background:{status_bg};
                            color:{status_color};
                            border:1px solid {status_color}40;
                            border-radius:999px;
                            padding:2px 10px;
                            font-size:12px;
                            font-weight:600;
                        '>{status_txt}</span>
                    </div>
                    <div style='font-size:20px;font-weight:700;color:#1e293b;margin:6px 0 2px'>
                        {aud['empresa']}
                    </div>
                    <div style='font-size:13px;color:#64748b;margin-bottom:10px'>
                        CNPJ: {cnpj_txt} &nbsp;·&nbsp; Norma: <strong>{aud['modulo']}</strong>
                        &nbsp;·&nbsp; ID: #{aud['id']}
                        &nbsp;·&nbsp; Início: {data_inicio} &nbsp;·&nbsp; Fim: {data_fim}
                    </div>
                    <div style='margin-bottom:10px;font-size:13px;color:#475569;font-family:monospace'>
                        {progresso_bar} {pct}%
                        <span style='color:#94a3b8;font-family:sans-serif'>
                            &nbsp;({respondidos}/{total_c} controles respondidos)
                        </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            with col_acoes:
                if st.session_state.confirmar_exclusao == aud["id"]:
                    st.warning("Confirmar exclusão?")
                    if st.button(
                        "Sim, apagar", key=f"confirm_{aud['id']}", type="primary"
                    ):
                        deletar_auditoria(aud["id"])
                        st.session_state.confirmar_exclusao = None
                        st.rerun()
                    if st.button("Cancelar", key=f"cancel_{aud['id']}"):
                        st.session_state.confirmar_exclusao = None
                        st.rerun()
                else:
                    if st.button("Apagar", key=f"del_{aud['id']}", icon="🗑️"):
                        st.session_state.confirmar_exclusao = aud["id"]
                        st.rerun()
