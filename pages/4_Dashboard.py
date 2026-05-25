import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import deletar_auditoria, get_analise_auditoria, get_auditorias
from utils.analytics import STATUS_COR, STATUS_LABEL, calcular_stats

st.set_page_config(page_title="Dashboard | PSI", page_icon="📊", layout="wide")

st.title("Dashboard de Auditorias")
st.markdown("---")

empresa_selecionada = st.session_state.get("empresa_selecionada")

if not empresa_selecionada:
    st.warning("Nenhuma empresa selecionada.")
    st.page_link("pages/1_Empresas.py", label="Selecionar Empresa", icon="🏢")
    st.stop()

st.markdown(f"Empresa: **{empresa_selecionada}**")
st.markdown("---")

if "confirmar_exclusao" not in st.session_state:
    st.session_state.confirmar_exclusao = None

auditorias = [a for a in get_auditorias() if a["empresa"] == empresa_selecionada]

# ── Lista e gerenciamento de auditorias
st.subheader("Gerenciar Auditorias")

AUD_STATUS_LABEL = {
    "concluida": ("Concluída", "#28965A", "#f0fdf4"),
    "em_andamento": ("Em andamento", "#f59e0b", "#fffbeb"),
}

for aud in auditorias:
    status_txt, status_color, status_bg = AUD_STATUS_LABEL.get(
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
                if st.button("Sim, apagar", key=f"confirm_{aud['id']}", type="primary"):
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

# ── Métricas de resumo
total = len(auditorias)
concluidas = sum(1 for a in auditorias if a["status"] == "concluida")
em_andamento_count = sum(1 for a in auditorias if a["status"] == "em_andamento")

col1, col2, col3 = st.columns(3)
col1.metric("Total de auditorias", total)
col2.metric("Concluídas", concluidas)
col3.metric("Em andamento", em_andamento_count)

st.markdown("---")

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
    st.stop()


def _label_aud(a: dict) -> str:
    data = (a["data_fim"] or a["data_inicio"])[:10]
    status_txt = "Concluída" if a["status"] == "concluida" else "Em andamento"
    return f"#{a['id']} — {a['modulo']} · {data} ({status_txt})"


# ── Seletor principal de auditoria
aud_options = {_label_aud(a): a["id"] for a in auditorias}
aud_label_sel = st.selectbox(
    "Auditoria analisada",
    list(aud_options.keys()),
    help="Selecione a auditoria para visualizar o dashboard de conformidade e relatórios.",
)
aud_id_sel = aud_options[aud_label_sel]

st.markdown("---")

# ── Dashboard de Conformidade
st.subheader("Dashboard de Conformidade")

analise = get_analise_auditoria(aud_id_sel)
respostas = analise["respostas"] if analise else []

if not respostas:
    st.info("Esta auditoria ainda não possui respostas registradas.")
else:
    stats = calcular_stats(respostas)

    # Métricas gerais
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Conformidade Geral", f"{stats['pct_geral']}%")
    c2.metric("Conformes", stats["contagem"].get("conforme", 0), delta_color="normal")
    c3.metric("Não Conformes", stats["contagem"].get("nao_conforme", 0))
    c4.metric("Em Andamento", stats["contagem"].get("em_andamento", 0))
    c5.metric("Não se Aplica", stats["contagem"].get("nao_se_aplica", 0))

    col_pie, col_bar = st.columns([1, 2])

    with col_pie:
        contagem = stats["contagem"]
        labels = [STATUS_LABEL.get(k, k) for k in contagem]
        values = list(contagem.values())
        colors = [STATUS_COR.get(k, "#94a3b8") for k in contagem]
        fig_pie = px.pie(
            names=labels,
            values=values,
            title="Distribuição Geral",
            color_discrete_sequence=colors,
            hole=0.45,
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        fig_pie.update_layout(showlegend=False, margin=dict(t=40, b=10, l=10, r=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_bar:
        df_temas = pd.DataFrame(stats["temas"])
        fig_bar = px.bar(
            df_temas,
            x="pct",
            y="nome",
            orientation="h",
            title="Conformidade por Tipo de Controle",
            labels={"pct": "% Conformidade", "nome": "Tipo de Controle"},
            color="pct",
            color_continuous_scale=["#ef4444", "#f59e0b", "#28965A"],
            range_color=[0, 100],
            range_x=[0, 110],
            text="pct",
        )
        fig_bar.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_bar.update_layout(
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(t=40, b=10, l=10, r=40),
            yaxis={"categoryorder": "total ascending"},
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Tabela de detalhamento por tema
    with st.expander("Detalhamento por Tipo de Controle", expanded=False):
        df_detail = pd.DataFrame(
            [
                {
                    "Tipo de Controle": t["nome"],
                    "Total": t["total"],
                    "Aplicáveis": t["aplicaveis"],
                    "Conformes": t["conformes"],
                    "Não Conformes": t["nao_conformes"],
                    "Em Andamento": t["em_andamento"],
                    "N/A": t["nao_se_aplica"],
                    "% Conformidade": t["pct"],
                }
                for t in stats["temas"]
            ]
        )
        st.dataframe(df_detail, use_container_width=True, hide_index=True)

st.markdown("---")

# ── Relatórios
st.subheader("Relatórios de Conformidade")

if not respostas:
    st.info("Selecione uma auditoria com respostas para gerar relatórios.")
else:
    tab_tipo, tab_full = st.tabs(["Por Tipo de Controle", "Relatório Completo"])

    with tab_tipo:
        temas_map: dict[str, str] = {}
        for r in respostas:
            temas_map[r["tema_id"]] = r["tema_nome"] or r["tema_id"]

        tema_sel = st.selectbox(
            "Tipo de Controle",
            options=list(temas_map.keys()),
            format_func=lambda x: temas_map[x],
        )

        resps_tema = [r for r in respostas if r["tema_id"] == tema_sel]
        st_tema = calcular_stats(resps_tema)

        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("Conformidade", f"{st_tema['pct_geral']}%")
        mc2.metric("Conformes", st_tema["contagem"].get("conforme", 0))
        mc3.metric("Não Conformes", st_tema["contagem"].get("nao_conforme", 0))

        df_tipo = pd.DataFrame(
            [
                {
                    "Controle": r["controle_id"],
                    "Nome": r["controle_nome"],
                    "Status": STATUS_LABEL.get(r["status"], r["status"]),
                    "Observação": r["observacao"] or "",
                }
                for r in resps_tema
            ]
        )

        def _style_status(val: str) -> str:
            m = {
                "Conforme": "background-color:#f0fdf4;color:#2A6041",
                "Não Conforme": "background-color:#fef2f2;color:#991b1b",
                "Em Andamento": "background-color:#fffbeb;color:#92400e",
                "Não se Aplica": "background-color:#f8fafc;color:#475569",
            }
            return m.get(val, "")

        st.dataframe(
            df_tipo.style.map(_style_status, subset=["Status"]),
            use_container_width=True,
            hide_index=True,
        )

        csv_tipo = df_tipo.to_csv(index=False).encode("utf-8")

    with tab_full:
        df_full = pd.DataFrame(
            [
                {
                    "Tipo de Controle": r["tema_nome"] or r["tema_id"],
                    "Controle": r["controle_id"],
                    "Nome": r["controle_nome"],
                    "Status": STATUS_LABEL.get(r["status"], r["status"]),
                    "Observação": r["observacao"] or "",
                }
                for r in respostas
            ]
        )

        st.dataframe(
            df_full.style.map(_style_status, subset=["Status"]),
            use_container_width=True,
            hide_index=True,
        )

        csv_full = df_full.to_csv(index=False).encode("utf-8")


st.markdown("---")
