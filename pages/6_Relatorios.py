import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_analise_auditoria, get_auditorias, get_empresa_by_name
from utils.analytics import STATUS_LABEL, calcular_stats
from utils.pdf_report import (
    gerar_pdf_auditoria,
    gerar_pdf_comparativo,
    gerar_pdf_evolucao,
)

st.set_page_config(page_title="Relatórios | PSI", page_icon="📄", layout="wide")

st.title("Relatórios de Conformidade")
st.markdown("---")

empresa_selecionada = st.session_state.get("empresa_selecionada")

if not empresa_selecionada:
    st.warning("Nenhuma empresa selecionada.")
    st.page_link("pages/1_Empresas.py", label="Selecionar Empresa", icon="🏢")
    st.stop()

st.markdown(f"Empresa: **{empresa_selecionada}**")
st.markdown("---")

# Dados da empresa (para o PDF)
empresa_db = get_empresa_by_name(empresa_selecionada) or {}
todas_auds = [a for a in get_auditorias() if a["empresa"] == empresa_selecionada]

if not todas_auds:
    st.info("Nenhuma auditoria encontrada para esta empresa.")
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


def _delta_ctrl(sb, sa) -> str:
    if sb is None:
        return "— Novo"
    ordem = {"nao_conforme": 0, "em_andamento": 1, "conforme": 2, "nao_se_aplica": -1}
    if ordem.get(sa, -1) > ordem.get(sb, -1):
        return "↑ Melhorou"
    if ordem.get(sa, -1) < ordem.get(sb, -1):
        return "↓ Piorou"
    return "= Igual"


@st.cache_data(ttl=60)
def _carregar(aud_id: int):
    an = get_analise_auditoria(aud_id)
    if not an or not an["respostas"]:
        return [], None
    return an["respostas"], calcular_stats(an["respostas"])


def _botoes_download(csv_bytes: bytes, pdf_bytes: bytes, prefixo: str):
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇ Baixar CSV",
            csv_bytes,
            f"{prefixo}.csv",
            "text/csv",
            width="stretch",
        )
    with c2:
        st.download_button(
            "⬇ Baixar PDF",
            pdf_bytes,
            f"{prefixo}.pdf",
            "application/pdf",
            width="stretch",
        )


# ── Tipo de relatório
tipo = st.radio(
    "Tipo de relatório",
    ["Auditoria", "Comparativo", "Evolução"],
    horizontal=True,
    help=(
        "**Auditoria**: snapshot de uma única auditoria.  "
        "**Comparativo**: base vs atual, controle a controle.  "
        "**Evolução**: linha do tempo com N auditorias."
    ),
)

st.markdown("---")

# relatório

if tipo == "Auditoria":
    st.subheader("Relatório de Auditoria")

    auds_ord = sorted(todas_auds, key=_data_ref, reverse=True)
    opcoes = {_label(a): a for a in auds_ord}

    col_s1, col_s2 = st.columns([3, 1])
    with col_s1:
        label_sel = st.selectbox("Auditoria", list(opcoes.keys()))
    aud = opcoes[label_sel]
    resps, stats = _carregar(aud["id"])

    if not stats:
        st.warning("Esta auditoria não possui respostas registradas.")
        st.stop()

    # Filtro por tema (opcional)
    temas_map = {}
    for r in resps:
        temas_map[r["tema_id"]] = r.get("tema_nome") or r["tema_id"]

    with col_s2:
        tema_opts = ["Todos"] + list(temas_map.keys())
        tema_sel = st.selectbox(
            "Filtrar por tipo de controle",
            tema_opts,
            format_func=lambda x: temas_map.get(x, x),
        )

    tema_filtro = None if tema_sel == "Todos" else tema_sel
    resps_vis = (
        resps if not tema_filtro else [r for r in resps if r["tema_id"] == tema_filtro]
    )
    stats_vis = stats if not tema_filtro else calcular_stats(resps_vis)

    # ── Preview
    st.markdown("#### Prévia")

    # Metadados
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Norma", aud["modulo"])
    m2.metric("Início", aud["data_inicio"][:10])
    m3.metric("Fim", aud["data_fim"][:10] if aud["data_fim"] else "—")
    m4.metric("Status", "Concluída" if aud["status"] == "concluida" else "Em andamento")

    # Métricas de conformidade
    c1, c2, c3, c4, c5 = st.columns(5)
    cnt = stats_vis["contagem"]
    c1.metric("Conformidade Geral", f"{stats_vis['pct_geral']}%")
    c2.metric("Conformes", cnt.get("conforme", 0))
    c3.metric("Não Conformes", cnt.get("nao_conforme", 0))
    c4.metric("Em Andamento", cnt.get("em_andamento", 0))
    c5.metric("Não se Aplica", cnt.get("nao_se_aplica", 0))

    # Tabela por tema
    with st.expander("Por Tipo de Controle", expanded=True):
        df_temas = pd.DataFrame(
            [
                {
                    "Tipo de Controle": t["nome"],
                    "Aplicáveis": t["aplicaveis"],
                    "Conformes": t["conformes"],
                    "Não Conf.": t["nao_conformes"],
                    "Em And.": t["em_andamento"],
                    "N/A": t["nao_se_aplica"],
                    "% Conf.": f"{t['pct']}%",
                }
                for t in stats_vis["temas"]
            ]
        )
        st.dataframe(df_temas, width="stretch", hide_index=True)

    # Tabela de controles
    with st.expander("Controles", expanded=False):
        df_ctrl = pd.DataFrame(
            [
                {
                    "Tipo de Controle": r.get("tema_nome") or r["tema_id"],
                    "Controle": r["controle_id"],
                    "Nome": r.get("controle_nome", r["controle_id"]),
                    "Status": STATUS_LABEL.get(r["status"], r["status"]),
                    "Observação": r.get("observacao") or "",
                }
                for r in resps_vis
            ]
        )
        st.dataframe(
            df_ctrl.style.map(_estilo_status, subset=["Status"]),
            width="stretch",
            hide_index=True,
        )

    st.markdown("---")

    # ── Downloads
    st.markdown("#### Download")

    with st.spinner("Gerando arquivos…"):
        # CSV
        df_csv = pd.DataFrame(
            [
                {
                    "Tipo de Controle": r.get("tema_nome") or r["tema_id"],
                    "Controle": r["controle_id"],
                    "Nome": r.get("controle_nome", r["controle_id"]),
                    "Status": STATUS_LABEL.get(r["status"], r["status"]),
                    "Observação": r.get("observacao") or "",
                }
                for r in resps_vis
            ]
        )
        csv_bytes = df_csv.to_csv(index=False).encode("utf-8")

        # PDF
        pdf_bytes = gerar_pdf_auditoria(
            empresa=empresa_db,
            auditoria=aud,
            stats=stats_vis,
            respostas=resps_vis,
            tema_filtro=tema_filtro,
        )

    sufixo = f"aud{aud['id']}" + (f"_{tema_filtro}" if tema_filtro else "")
    _botoes_download(csv_bytes, pdf_bytes, f"relatorio_{sufixo}")


# comparativo

elif tipo == "Comparativo":
    st.subheader("Relatório Comparativo")

    if len(todas_auds) < 2:
        st.info("São necessárias pelo menos 2 auditorias para o relatório comparativo.")
        st.stop()

    # Filtro por norma
    normas = sorted({a["modulo"] for a in todas_auds})
    norma_fil = st.selectbox("Norma", ["Todas"] + normas)
    auds_fil = sorted(
        [a for a in todas_auds if norma_fil == "Todas" or a["modulo"] == norma_fil],
        key=_data_ref,
    )
    opcoes = {_label(a): a for a in auds_fil}

    cb, ca = st.columns(2)
    with cb:
        lb = st.selectbox("Auditoria base", list(opcoes.keys()), index=0)
    with ca:
        opts_a = [l for l in opcoes if l != lb]
        la = st.selectbox("Auditoria atual", opts_a, index=len(opts_a) - 1)

    aud_b = opcoes[lb]
    aud_a = opcoes[la]
    resps_b, stats_b = _carregar(aud_b["id"])
    resps_a, stats_a = _carregar(aud_a["id"])

    if not stats_b or not stats_a:
        st.warning("Uma das auditorias não possui respostas.")
        st.stop()

    # ── Preview
    st.markdown("#### Prévia")

    delta_g = round(stats_a["pct_geral"] - stats_b["pct_geral"], 1)
    sinal = "+" if delta_g >= 0 else ""

    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Conf. Base", f"{stats_b['pct_geral']}%")
    mc2.metric("Conf. Atual", f"{stats_a['pct_geral']}%", delta=f"{sinal}{delta_g} pp")
    mc3.metric("Variação", f"{sinal}{delta_g} pp")

    # Por tema
    temas_b_m = {t["nome"]: t for t in stats_b["temas"]}
    temas_a_m = {t["nome"]: t for t in stats_a["temas"]}
    todos_t = sorted(set(temas_b_m) | set(temas_a_m))

    with st.expander("Por Tipo de Controle", expanded=True):
        df_comp_t = pd.DataFrame(
            [
                {
                    "Tipo de Controle": nome,
                    f"Base #{aud_b['id']}": (
                        f"{temas_b_m[nome]['pct']}%" if nome in temas_b_m else "—"
                    ),
                    f"Atual #{aud_a['id']}": (
                        f"{temas_a_m[nome]['pct']}%" if nome in temas_a_m else "—"
                    ),
                    "Δ (pp)": (
                        f"{'+'if round(temas_a_m.get(nome,{}).get('pct',0)-temas_b_m.get(nome,{}).get('pct',0),1)>=0 else ''}"
                        f"{round(temas_a_m.get(nome,{}).get('pct',0)-temas_b_m.get(nome,{}).get('pct',0),1)}"
                    ),
                }
                for nome in todos_t
            ]
        )

        def _cor_d(val):
            try:
                v = float(val.replace("+", ""))
                return (
                    "color:#2A6041;font-weight:600"
                    if v > 0
                    else ("color:#991b1b;font-weight:600" if v < 0 else "color:#94a3b8")
                )
            except ValueError:
                return ""

        st.dataframe(
            df_comp_t.style.map(_cor_d, subset=["Δ (pp)"]),
            width="stretch",
            hide_index=True,
        )

    # Mudanças por controle
    with st.expander("Mudanças por Controle", expanded=False):
        map_b = {r["controle_id"]: r for r in resps_b}
        map_a = {r["controle_id"]: r for r in resps_a}
        df_mud = pd.DataFrame(
            [
                {
                    "Tipo de Controle": (map_a.get(cid) or map_b.get(cid, {})).get(
                        "tema_nome", ""
                    ),
                    "Controle": cid,
                    "Nome": (map_a.get(cid) or map_b.get(cid, {})).get(
                        "controle_nome", cid
                    ),
                    "Base": (
                        STATUS_LABEL.get(map_b[cid]["status"]) if cid in map_b else "—"
                    ),
                    "Atual": (
                        STATUS_LABEL.get(map_a[cid]["status"]) if cid in map_a else "—"
                    ),
                    "Mudança": _delta_ctrl(
                        map_b[cid]["status"] if cid in map_b else None,
                        map_a[cid]["status"] if cid in map_a else None,
                    ),
                }
                for cid in sorted(set(map_b) | set(map_a))
            ]
        )
        st.dataframe(
            df_mud.style.map(_estilo_status, subset=["Base", "Atual"]).map(
                _estilo_delta, subset=["Mudança"]
            ),
            width="stretch",
            hide_index=True,
        )

    st.markdown("---")

    # ── Downloads
    st.markdown("#### Download")

    with st.spinner("Gerando arquivos…"):
        # CSV (mudanças completas)
        map_b2 = {r["controle_id"]: r for r in resps_b}
        map_a2 = {r["controle_id"]: r for r in resps_a}
        df_csv_c = pd.DataFrame(
            [
                {
                    "Tipo de Controle": (map_a2.get(cid) or map_b2.get(cid, {})).get(
                        "tema_nome", ""
                    ),
                    "Controle": cid,
                    "Nome": (map_a2.get(cid) or map_b2.get(cid, {})).get(
                        "controle_nome", cid
                    ),
                    f"Base #{aud_b['id']}": (
                        STATUS_LABEL.get(map_b2[cid]["status"])
                        if cid in map_b2
                        else "—"
                    ),
                    f"Atual #{aud_a['id']}": (
                        STATUS_LABEL.get(map_a2[cid]["status"])
                        if cid in map_a2
                        else "—"
                    ),
                    "Mudança": _delta_ctrl(
                        map_b2[cid]["status"] if cid in map_b2 else None,
                        map_a2[cid]["status"] if cid in map_a2 else None,
                    ),
                }
                for cid in sorted(set(map_b2) | set(map_a2))
            ]
        )
        csv_bytes_c = df_csv_c.to_csv(index=False).encode("utf-8")

        pdf_bytes_c = gerar_pdf_comparativo(
            empresa=empresa_db,
            aud_base=aud_b,
            aud_atual=aud_a,
            stats_base=stats_b,
            stats_atual=stats_a,
            resps_base=resps_b,
            resps_atual=resps_a,
        )

    _botoes_download(
        csv_bytes_c, pdf_bytes_c, f"comparativo_aud{aud_b['id']}_vs_{aud_a['id']}"
    )


# evolução

else:
    st.subheader("Relatório de Evolução")

    normas_e = sorted({a["modulo"] for a in todas_auds})
    norma_e = st.selectbox("Norma", ["Todas"] + normas_e, key="ev_norma")
    auds_e = sorted(
        [a for a in todas_auds if norma_e == "Todas" or a["modulo"] == norma_e],
        key=_data_ref,
    )
    opcoes_e = {_label(a): a for a in auds_e}

    sel_e = st.multiselect(
        "Auditorias (ordem cronológica)",
        list(opcoes_e.keys()),
        default=list(opcoes_e.keys()),
    )

    if len(sel_e) < 2:
        st.warning("Selecione pelo menos 2 auditorias.")
        st.stop()

    auds_sel_e = [opcoes_e[l] for l in sel_e]

    # Carregar stats
    auds_com_stats = []
    for a in auds_sel_e:
        resps, stats = _carregar(a["id"])
        if stats:
            auds_com_stats.append((a, stats))

    if len(auds_com_stats) < 2:
        st.warning("Auditorias selecionadas sem respostas suficientes.")
        st.stop()

    # ── Preview
    st.markdown("#### Prévia")

    # Tabela resumo
    df_ev = pd.DataFrame(
        [
            {
                "ID": f"#{a['id']}",
                "Norma": a["modulo"],
                "Início": a["data_inicio"][:10],
                "Fim": a["data_fim"][:10] if a["data_fim"] else "—",
                "Status": "Concluída" if a["status"] == "concluida" else "Em andamento",
                "Respondidos": f"{a['total_respostas']}/{a['total_controles']}",
                "% Conf. Geral": f"{st['pct_geral']}%",
            }
            for a, st in auds_com_stats
        ]
    )

    def _cor_status_ev(val):
        if val == "Concluída":
            return "color:#2A6041;font-weight:600"
        if val == "Em andamento":
            return "color:#92400e;font-weight:600"
        return ""

    st.dataframe(
        df_ev.style.map(_cor_status_ev, subset=["Status"]),
        width="stretch",
        hide_index=True,
    )

    # Tabela evolução por tema
    todos_temas_e: list[str] = []
    for _, st2 in auds_com_stats:
        for t in st2["temas"]:
            if t["nome"] not in todos_temas_e:
                todos_temas_e.append(t["nome"])

    with st.expander("Por Tipo de Controle", expanded=False):
        colunas_e = {"Tipo de Controle": [n for n in todos_temas_e]}
        for a, st2 in auds_com_stats:
            t_map = {t["nome"]: f"{t['pct']}%" for t in st2["temas"]}
            colunas_e[f"#{a['id']} · {_data_ref(a)}"] = [
                t_map.get(n, "—") for n in todos_temas_e
            ]
        st.dataframe(pd.DataFrame(colunas_e), width="stretch", hide_index=True)

    st.markdown("---")

    # ── Downloads
    st.markdown("#### Download")

    with st.spinner("Gerando arquivos…"):
        # CSV
        csv_rows = []
        for a, st2 in auds_com_stats:
            data = _data_ref(a)
            for t in st2["temas"]:
                csv_rows.append(
                    {
                        "ID Auditoria": a["id"],
                        "Norma": a["modulo"],
                        "Data Referência": data,
                        "Tipo de Controle": t["nome"],
                        "Aplicáveis": t["aplicaveis"],
                        "Conformes": t["conformes"],
                        "Não Conformes": t["nao_conformes"],
                        "Em Andamento": t["em_andamento"],
                        "N/A": t["nao_se_aplica"],
                        "% Conformidade": t["pct"],
                    }
                )
        csv_bytes_e = pd.DataFrame(csv_rows).to_csv(index=False).encode("utf-8")

        pdf_bytes_e = gerar_pdf_evolucao(
            empresa=empresa_db,
            auds_com_stats=auds_com_stats,
        )

    ids_str = "_".join(str(a["id"]) for a, _ in auds_com_stats)
    _botoes_download(csv_bytes_e, pdf_bytes_e, f"evolucao_{ids_str}")
