import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_analise_auditoria, get_auditorias
from utils.analytics import STATUS_LABEL, calcular_stats

st.set_page_config(page_title="Comparativo | PSI", page_icon="📈", layout="wide")

st.title("Comparativo de Auditorias")
st.markdown("---")

empresa_selecionada = st.session_state.get("empresa_selecionada")

if not empresa_selecionada:
    st.warning("Nenhuma empresa selecionada.")
    st.page_link("pages/1_Empresas.py", label="Selecionar Empresa", icon="🏢")
    st.stop()

st.markdown(f"Empresa: **{empresa_selecionada}**")
st.markdown("---")

todas = [a for a in get_auditorias() if a["empresa"] == empresa_selecionada]

if len(todas) < 2:
    st.info(
        "São necessárias pelo menos 2 auditorias para realizar comparativos. "
        "Crie mais auditorias na página **Nova Auditoria**."
    )
    st.page_link("pages/3_Nova_Auditoria.py", label="Nova Auditoria", icon="🔍")
    st.stop()


# ── Helpers


def _data_ref(a: dict) -> str:
    return (a["data_fim"] or a["data_inicio"])[:10]


def _label(a: dict) -> str:
    status = "Concluída" if a["status"] == "concluida" else "Em andamento"
    return f"#{a['id']} · {a['modulo']} · {_data_ref(a)} ({status})"


def _estilo_status(val: str) -> str:
    return {
        "Conforme": "background-color:#f0fdf4;color:#2A6041",
        "Não Conforme": "background-color:#fef2f2;color:#991b1b",
        "Em Andamento": "background-color:#fffbeb;color:#92400e",
        "Não se Aplica": "background-color:#f8fafc;color:#475569",
    }.get(val, "")


def _estilo_delta(val: str) -> str:
    return {
        "↑ Melhorou": "background-color:#f0fdf4;color:#2A6041;font-weight:600",
        "↓ Piorou": "background-color:#fef2f2;color:#991b1b;font-weight:600",
        "= Igual": "color:#94a3b8",
        "— Novo": "background-color:#eff6ff;color:#1d4ed8",
    }.get(val, "")


def _delta_ctrl(s_ant: str | None, s_at: str | None) -> str:
    if s_ant is None:
        return "— Novo"
    ordem = {"nao_conforme": 0, "em_andamento": 1, "conforme": 2, "nao_se_aplica": -1}
    if ordem.get(s_at, -1) > ordem.get(s_ant, -1):
        return "↑ Melhorou"
    if ordem.get(s_at, -1) < ordem.get(s_ant, -1):
        return "↓ Piorou"
    return "= Igual"


@st.cache_data(ttl=60)
def _carregar(aud_id: int):
    an = get_analise_auditoria(aud_id)
    if not an or not an["respostas"]:
        return [], None
    return an["respostas"], calcular_stats(an["respostas"])


# ── Seleção de norma e auditorias
st.subheader("Seleção de Auditorias")

normas = sorted({a["modulo"] for a in todas})
norma_sel = st.selectbox(
    "Norma",
    ["Todas"] + normas,
    help="Comparar auditorias da mesma norma torna os resultados mais significativos.",
)

auds_filtradas = sorted(
    [a for a in todas if norma_sel == "Todas" or a["modulo"] == norma_sel],
    key=_data_ref,
)

opcoes = {_label(a): a for a in auds_filtradas}

auds_sel_labels = st.multiselect(
    "Auditorias a comparar",
    list(opcoes.keys()),
    default=list(opcoes.keys()),
    help="Selecione 2 ou mais auditorias. A ordem cronológica é mantida automaticamente.",
)

if len(auds_sel_labels) < 2:
    st.warning("Selecione pelo menos 2 auditorias.")
    st.stop()

auds_sel = [opcoes[l] for l in auds_sel_labels]

st.markdown("---")

# ── Resumo das auditorias selecionadas
st.subheader("Resumo das Auditorias")

resumo_rows = []
dados_cache: dict[int, tuple] = {}

for a in auds_sel:
    resps, stats = _carregar(a["id"])
    dados_cache[a["id"]] = (resps, stats)
    resumo_rows.append(
        {
            "ID": f"#{a['id']}",
            "Norma": a["modulo"],
            "Início": a["data_inicio"][:10],
            "Fim": a["data_fim"][:10] if a["data_fim"] else "—",
            "Status": "Concluída" if a["status"] == "concluida" else "Em andamento",
            "Respondidos": f"{a['total_respostas']}/{a['total_controles']}",
            "% Progresso": (
                round(a["total_respostas"] / a["total_controles"] * 100)
                if a["total_controles"]
                else 0
            ),
            "% Conf. Geral": stats["pct_geral"] if stats else "—",
        }
    )

df_resumo = pd.DataFrame(resumo_rows)


def _cor_status_resumo(val):
    if val == "Concluída":
        return "color:#2A6041;font-weight:600"
    if val == "Em andamento":
        return "color:#92400e;font-weight:600"
    return ""


st.dataframe(
    df_resumo.style.map(_cor_status_resumo, subset=["Status"]),
    width="stretch",
    hide_index=True,
)

st.markdown("---")

# ── Evolução de conformidade
st.subheader("Evolução de Conformidade")

evol_geral, evol_tema = [], []

for a in auds_sel:
    resps, stats = dados_cache[a["id"]]
    if not stats:
        continue
    data = _data_ref(a)
    label_curto = f"#{a['id']} · {data}"
    evol_geral.append(
        {
            "Auditoria": label_curto,
            "Data": data,
            "% Conformidade": stats["pct_geral"],
        }
    )
    for t in stats["temas"]:
        evol_tema.append(
            {
                "Auditoria": label_curto,
                "Data": data,
                "Tipo de Controle": t["nome"],
                "% Conformidade": t["pct"],
            }
        )

tab_geral, tab_tema = st.tabs(["Geral", "Por Tipo de Controle"])

with tab_geral:
    df_evol = pd.DataFrame(evol_geral)

    # Linha de evolução
    fig_line = px.line(
        df_evol,
        x="Auditoria",
        y="% Conformidade",
        markers=True,
        text="% Conformidade",
        title="Evolução da Conformidade Geral",
        range_y=[0, 110],
    )
    fig_line.update_traces(
        texttemplate="%{text:.1f}%",
        textposition="top center",
        line=dict(color="#28965A", width=3),
        marker=dict(size=11),
    )
    fig_line.add_hline(
        y=70,
        line_dash="dot",
        line_color="#f59e0b",
        annotation_text="Meta 70%",
        annotation_position="bottom right",
    )
    fig_line.update_layout(margin=dict(t=50, b=20), xaxis_title="")
    st.plotly_chart(fig_line, width="stretch")

    # Tabela de variação entre auditorias consecutivas
    if len(evol_geral) >= 2:
        delta_rows = []
        for i in range(1, len(evol_geral)):
            ant = evol_geral[i - 1]
            at = evol_geral[i]
            diff = round(at["% Conformidade"] - ant["% Conformidade"], 1)
            sinal = "+" if diff >= 0 else ""
            delta_rows.append(
                {
                    "De": ant["Auditoria"],
                    "Para": at["Auditoria"],
                    "% Anterior": ant["% Conformidade"],
                    "% Atual": at["% Conformidade"],
                    "Variação (pp)": f"{sinal}{diff}",
                }
            )
        with st.expander("Variação entre períodos", expanded=False):
            st.dataframe(pd.DataFrame(delta_rows), width="stretch", hide_index=True)

with tab_tema:
    df_tema_evol = pd.DataFrame(evol_tema)
    temas_disp = sorted(df_tema_evol["Tipo de Controle"].unique())
    temas_escolhidos = st.multiselect(
        "Tipos de controle",
        temas_disp,
        default=temas_disp,
        key="evol_temas",
    )
    df_tema_fil = df_tema_evol[df_tema_evol["Tipo de Controle"].isin(temas_escolhidos)]
    fig_tema = px.line(
        df_tema_fil,
        x="Auditoria",
        y="% Conformidade",
        color="Tipo de Controle",
        markers=True,
        title="Evolução por Tipo de Controle",
        range_y=[0, 110],
    )
    fig_tema.update_traces(marker=dict(size=9))
    fig_tema.update_layout(margin=dict(t=50, b=20), xaxis_title="")
    st.plotly_chart(fig_tema, width="stretch")

st.markdown("---")

# ── Comparativo direto: base × atual
st.subheader("Comparativo Direto")

col_b, col_a = st.columns(2)
with col_b:
    label_base = st.selectbox("Auditoria base", auds_sel_labels, index=0, key="base")
with col_a:
    opts_at = [l for l in auds_sel_labels if l != label_base]
    label_at = st.selectbox(
        "Auditoria atual", opts_at, index=len(opts_at) - 1, key="atual"
    )

aud_base = opcoes[label_base]
aud_at = opcoes[label_at]
resps_b, stats_b = dados_cache[aud_base["id"]]
resps_a, stats_a = dados_cache[aud_at["id"]]

if not stats_b or not stats_a:
    st.warning("Uma das auditorias selecionadas não possui respostas.")
else:
    # Métricas
    delta_g = round(stats_a["pct_geral"] - stats_b["pct_geral"], 1)
    sinal_g = "+" if delta_g >= 0 else ""
    mc1, mc2, mc3, mc4, mc5 = st.columns(5)
    mc1.metric(
        "Conf. Base",
        f"{stats_b['pct_geral']}%",
        help=f"Auditoria #{aud_base['id']} · {_data_ref(aud_base)}",
    )
    mc2.metric(
        "Conf. Atual",
        f"{stats_a['pct_geral']}%",
        delta=f"{sinal_g}{delta_g} pp",
        help=f"Auditoria #{aud_at['id']} · {_data_ref(aud_at)}",
    )
    mc3.metric("Conformes Base", stats_b["contagem"].get("conforme", 0))
    mc4.metric(
        "Conformes Atual",
        stats_a["contagem"].get("conforme", 0),
        delta=str(
            stats_a["contagem"].get("conforme", 0)
            - stats_b["contagem"].get("conforme", 0)
        ),
    )
    mc5.metric("Não Conformes Atual", stats_a["contagem"].get("nao_conforme", 0))

    # Tabela comparativa por tema
    temas_b = {t["nome"]: t for t in stats_b["temas"]}
    temas_a = {t["nome"]: t for t in stats_a["temas"]}
    todos_temas = sorted(set(temas_b) | set(temas_a))

    comp_tema_rows = []
    for nome in todos_temas:
        pb = temas_b[nome]["pct"] if nome in temas_b else 0.0
        pa = temas_a[nome]["pct"] if nome in temas_a else 0.0
        dif = round(pa - pb, 1)
        comp_tema_rows.append(
            {
                "Tipo de Controle": nome,
                f"Base #{aud_base['id']}": pb,
                f"Atual #{aud_at['id']}": pa,
                "Δ (pp)": f"{'+'if dif>=0 else ''}{dif}",
            }
        )

    col_chart, col_table = st.columns([3, 2])

    with col_chart:
        df_melt = pd.DataFrame(
            [
                {
                    "Tipo de Controle": r["Tipo de Controle"],
                    "Versão": f"Base #{aud_base['id']}",
                    "% Conformidade": (
                        temas_b[r["Tipo de Controle"]]["pct"]
                        if r["Tipo de Controle"] in temas_b
                        else 0
                    ),
                }
                for r in comp_tema_rows
            ]
            + [
                {
                    "Tipo de Controle": r["Tipo de Controle"],
                    "Versão": f"Atual #{aud_at['id']}",
                    "% Conformidade": (
                        temas_a[r["Tipo de Controle"]]["pct"]
                        if r["Tipo de Controle"] in temas_a
                        else 0
                    ),
                }
                for r in comp_tema_rows
            ]
        )
        fig_barras = px.bar(
            df_melt,
            x="Tipo de Controle",
            y="% Conformidade",
            color="Versão",
            barmode="group",
            text="% Conformidade",
            range_y=[0, 115],
            color_discrete_map={
                f"Base #{aud_base['id']}": "#94a3b8",
                f"Atual #{aud_at['id']}": "#28965A",
            },
            title="Conformidade por Tipo de Controle: Base vs Atual",
        )
        fig_barras.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_barras.update_layout(
            margin=dict(t=50, b=60), xaxis_tickangle=-25, xaxis_title=""
        )
        st.plotly_chart(fig_barras, width="stretch")

    with col_table:
        df_comp_tema = pd.DataFrame(comp_tema_rows)

        def _cor_delta(val: str) -> str:
            try:
                v = float(val.replace("+", ""))
                if v > 0:
                    return "color:#2A6041;font-weight:600"
                if v < 0:
                    return "color:#991b1b;font-weight:600"
            except ValueError:
                pass
            return "color:#94a3b8"

        st.dataframe(
            df_comp_tema.style.map(_cor_delta, subset=["Δ (pp)"]),
            width="stretch",
            hide_index=True,
        )

st.markdown("---")

# ── Análise de mudanças por controle
st.subheader("Mudanças por Controle")
st.caption(f"Comparando: **{label_base}** → **{label_at}**")

if stats_b and stats_a:
    map_b = {r["controle_id"]: r for r in resps_b}
    map_a = {r["controle_id"]: r for r in resps_a}
    todos_cids = sorted(set(map_b) | set(map_a))

    mud_rows = []
    for cid in todos_cids:
        rb = map_b.get(cid)
        ra = map_a.get(cid)
        s_b = rb["status"] if rb else None
        s_a = ra["status"] if ra else None
        ref = ra or rb or {}
        mud_rows.append(
            {
                "Tipo de Controle": ref.get("tema_nome") or ref.get("tema_id", ""),
                "Controle": cid,
                "Nome": ref.get("controle_nome", cid),
                "Base": STATUS_LABEL.get(s_b, "—") if s_b else "—",
                "Atual": STATUS_LABEL.get(s_a, "—") if s_a else "—",
                "Mudança": _delta_ctrl(s_b, s_a),
            }
        )

    df_mud = pd.DataFrame(mud_rows)

    n_melh = (df_mud["Mudança"] == "↑ Melhorou").sum()
    n_pior = (df_mud["Mudança"] == "↓ Piorou").sum()
    n_igual = (df_mud["Mudança"] == "= Igual").sum()
    n_novo = (df_mud["Mudança"] == "— Novo").sum()

    km1, km2, km3, km4 = st.columns(4)
    km1.metric("Melhoraram", n_melh)
    km2.metric("Pioraram", n_pior)
    km3.metric("Sem mudança", n_igual)
    km4.metric("Novos", n_novo)

    # Filtros
    cf1, cf2 = st.columns(2)
    with cf1:
        filtro_mud = st.multiselect(
            "Tipo de mudança",
            ["↑ Melhorou", "↓ Piorou", "= Igual", "— Novo"],
            default=["↑ Melhorou", "↓ Piorou", "— Novo"],
        )
    with cf2:
        temas_mud = sorted(df_mud["Tipo de Controle"].unique())
        filtro_tema_mud = st.multiselect(
            "Tipo de controle",
            temas_mud,
            default=temas_mud,
        )

    df_mud_fil = df_mud[
        df_mud["Mudança"].isin(filtro_mud)
        & df_mud["Tipo de Controle"].isin(filtro_tema_mud)
    ]

    st.dataframe(
        df_mud_fil.style.map(_estilo_status, subset=["Base", "Atual"]).map(
            _estilo_delta, subset=["Mudança"]
        ),
        width="stretch",
        hide_index=True,
    )

    csv_mud = df_mud_fil.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Baixar mudanças (CSV)",
        csv_mud,
        f"mudancas_aud{aud_base['id']}_vs_aud{aud_at['id']}.csv",
        "text/csv",
    )

st.markdown("---")

# ── Relatórios
st.subheader("Relatórios")

tab_tipo, tab_full = st.tabs(["Por Tipo de Controle", "Comparativo Completo"])

if stats_b and stats_a:
    with tab_tipo:
        # Mapa de temas disponíveis (união base + atual)
        temas_rel: dict[str, str] = {}
        for r in resps_b + resps_a:
            temas_rel[r["tema_id"]] = r["tema_nome"] or r["tema_id"]

        tema_rel = st.selectbox(
            "Tipo de controle",
            list(temas_rel.keys()),
            format_func=lambda x: temas_rel[x],
        )

        map_b_t = {r["controle_id"]: r for r in resps_b if r["tema_id"] == tema_rel}
        map_a_t = {r["controle_id"]: r for r in resps_a if r["tema_id"] == tema_rel}
        cids_t = sorted(set(map_b_t) | set(map_a_t))

        # Métricas do tema
        st_b_t = calcular_stats(list(map_b_t.values())) if map_b_t else None
        st_a_t = calcular_stats(list(map_a_t.values())) if map_a_t else None
        rt1, rt2, rt3 = st.columns(3)
        rt1.metric("Conf. Base", f"{st_b_t['pct_geral']}%" if st_b_t else "—")
        rt2.metric(
            "Conf. Atual",
            f"{st_a_t['pct_geral']}%" if st_a_t else "—",
            delta=(
                f"{round(st_a_t['pct_geral']-st_b_t['pct_geral'],1):+.1f} pp"
                if st_b_t and st_a_t
                else None
            ),
        )
        rt3.metric("Controles", len(cids_t))

        df_rel_t = pd.DataFrame(
            [
                {
                    "Controle": cid,
                    "Nome": (map_a_t.get(cid) or map_b_t.get(cid, {})).get(
                        "controle_nome", cid
                    ),
                    f"Base #{aud_base['id']}": (
                        STATUS_LABEL.get(map_b_t[cid]["status"], map_b_t[cid]["status"])
                        if cid in map_b_t
                        else "—"
                    ),
                    f"Atual #{aud_at['id']}": (
                        STATUS_LABEL.get(map_a_t[cid]["status"], map_a_t[cid]["status"])
                        if cid in map_a_t
                        else "—"
                    ),
                    "Mudança": _delta_ctrl(
                        map_b_t[cid]["status"] if cid in map_b_t else None,
                        map_a_t[cid]["status"] if cid in map_a_t else None,
                    ),
                    "Obs. Base": (map_b_t.get(cid) or {}).get("observacao") or "",
                    "Obs. Atual": (map_a_t.get(cid) or {}).get("observacao") or "",
                }
                for cid in cids_t
            ]
        )

        col_b_lbl = f"Base #{aud_base['id']}"
        col_a_lbl = f"Atual #{aud_at['id']}"

        st.dataframe(
            df_rel_t.style.map(_estilo_status, subset=[col_b_lbl, col_a_lbl]).map(
                _estilo_delta, subset=["Mudança"]
            ),
            width="stretch",
            hide_index=True,
        )

    with tab_full:
        map_b_f = {r["controle_id"]: r for r in resps_b}
        map_a_f = {r["controle_id"]: r for r in resps_a}
        cids_f = sorted(set(map_b_f) | set(map_a_f))

        df_full = pd.DataFrame(
            [
                {
                    "Tipo de Controle": (map_a_f.get(cid) or map_b_f.get(cid, {})).get(
                        "tema_nome"
                    )
                    or (map_a_f.get(cid) or map_b_f.get(cid, {})).get("tema_id", ""),
                    "Controle": cid,
                    "Nome": (map_a_f.get(cid) or map_b_f.get(cid, {})).get(
                        "controle_nome", cid
                    ),
                    f"Base #{aud_base['id']}": (
                        STATUS_LABEL.get(map_b_f[cid]["status"], map_b_f[cid]["status"])
                        if cid in map_b_f
                        else "—"
                    ),
                    f"Atual #{aud_at['id']}": (
                        STATUS_LABEL.get(map_a_f[cid]["status"], map_a_f[cid]["status"])
                        if cid in map_a_f
                        else "—"
                    ),
                    "Mudança": _delta_ctrl(
                        map_b_f[cid]["status"] if cid in map_b_f else None,
                        map_a_f[cid]["status"] if cid in map_a_f else None,
                    ),
                }
                for cid in cids_f
            ]
        )

        col_b_lbl_f = f"Base #{aud_base['id']}"
        col_a_lbl_f = f"Atual #{aud_at['id']}"

        st.dataframe(
            df_full.style.map(_estilo_status, subset=[col_b_lbl_f, col_a_lbl_f]).map(
                _estilo_delta, subset=["Mudança"]
            ),
            width="stretch",
            hide_index=True,
        )
