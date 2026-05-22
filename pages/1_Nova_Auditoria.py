"""
Página: Nova Auditoria
Fluxo completo de diagnóstico de conformidade
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import (
    criar_auditoria,
    deletar_auditoria,
    finalizar_auditoria,
    get_controles_norma,
    get_normas,
    get_progresso_auditoria,
    get_respostas_auditoria,
    salvar_resposta,
)

st.set_page_config(page_title="Nova Auditoria | PSI", page_icon="🔍", layout="wide")

# ── session state ─────────────────────────────────────────────────────────────
for key, default in [
    ("auditoria_id", None),
    ("norma_id", None),
    ("norma_nome", None),
    ("empresa", ""),
    ("cnpj", ""),
    ("controle_index", 0),
    ("fase", "inicio"),
    ("respostas_session", {}),
]:
    if key not in st.session_state:
        st.session_state[key] = default


def reiniciar():
    st.session_state.auditoria_id = None
    st.session_state.norma_id = None
    st.session_state.norma_nome = None
    st.session_state.empresa = ""
    st.session_state.cnpj = ""
    st.session_state.controle_index = 0
    st.session_state.fase = "inicio"
    st.session_state.respostas_session = {}


def _normalizar(raw: list[dict]) -> list[dict]:
    """Mapeia campos do banco para o formato interno usado na página."""
    return [
        {
            "id": c["controle_id"],
            "tema": c["tema_id"],
            "tema_nome": c["tema_nome"] or c["tema_id"],
            "nome": c["nome"],
            "descricao": c["descricao"] or "",
        }
        for c in raw
    ]


def get_controles() -> list[dict]:
    return _normalizar(get_controles_norma(st.session_state.norma_id))


def get_temas(controles: list[dict]) -> dict:
    temas = {}
    for c in controles:
        if c["tema"] not in temas:
            temas[c["tema"]] = c["tema_nome"]
    return temas


STATUS_CORES = {
    "conforme": "#22c55e",
    "nao_conforme": "#ef4444",
    "em_andamento": "#f59e0b",
    "nao_se_aplica": "#94a3b8",
}

# ── 1ª etapa: início ──────────────────────────────────────────────────────────
if st.session_state.fase == "inicio":
    st.title("Nova Auditoria")
    st.markdown("Configure os dados básicos antes de iniciar o diagnóstico.")
    st.markdown("---")

    normas = get_normas()

    if not normas:
        st.warning(
            "Nenhuma norma cadastrada no sistema. "
            "Adicione pelo menos uma norma antes de iniciar uma auditoria."
        )
        st.page_link(
            "pages/0_Injestão_de_Controles.py",
            label="Ir para Ingestão de Controles",
            icon="📥",
        )
        st.stop()

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### 1. Selecionar Norma")

        opcoes_label = []
        opcoes_id = []
        for n in normas:
            label = n["nome"]
            if n["versao"]:
                label += f" ({n['versao']})"
            opcoes_label.append(label)
            opcoes_id.append(n["id"])

        idx_norma = st.selectbox(
            "Qual norma deseja auditar?",
            range(len(opcoes_label)),
            format_func=lambda i: opcoes_label[i],
        )
        norma_selecionada = normas[idx_norma]

        total_controles = len(get_controles_norma(norma_selecionada["id"]))
        st.caption(f"{total_controles} controles disponíveis nesta norma.")

    with col2:
        st.markdown("### 2. Dados da Empresa")
        empresa = st.text_input("Nome da Empresa *", placeholder="Ex: Empresa Exemplo Ltda")
        cnpj = st.text_input("CNPJ (opcional)", placeholder="00.000.000/0001-00")

    st.markdown("---")

    col_btn1, _ = st.columns([1, 5])
    with col_btn1:
        if st.button("Iniciar Auditoria", type="primary", disabled=not empresa.strip()):
            st.session_state.norma_id = norma_selecionada["id"]
            st.session_state.norma_nome = opcoes_label[idx_norma]
            st.session_state.empresa = empresa.strip()
            st.session_state.cnpj = cnpj.strip()
            st.session_state.controle_index = 0
            st.session_state.fase = "auditoria"
            aud_id = criar_auditoria(
                empresa.strip(), cnpj.strip(), norma_selecionada["nome"]
            )
            st.session_state.auditoria_id = aud_id
            st.rerun()

    if not empresa.strip():
        st.caption("Informe o nome da empresa para continuar.")


# ── 2ª etapa: auditoria ───────────────────────────────────────────────────────
elif st.session_state.fase == "auditoria":
    controles = get_controles()
    temas = get_temas(controles)
    total = len(controles)
    idx = st.session_state.controle_index

    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title(f"Auditoria — {st.session_state.norma_nome}")
        st.markdown(
            f"**Empresa:** {st.session_state.empresa} | **Auditoria ID:** #{st.session_state.auditoria_id}"
        )
    with col_h2:
        if st.button("Cancelar Auditoria"):
            if st.session_state.auditoria_id:
                deletar_auditoria(st.session_state.auditoria_id)
            reiniciar()
            st.rerun()

    prog = get_progresso_auditoria(st.session_state.auditoria_id, total)
    st.progress(
        prog["percentual"] / 100,
        text=f"Progresso: {prog['respondidos']}/{total} controles ({prog['percentual']:.0f}%)",
    )
    st.markdown("---")

    if idx >= total:
        st.success("Todos os controles foram respondidos!")
        st.markdown("Revise e finalize a auditoria para gerar o dashboard.")

        respostas = get_respostas_auditoria(st.session_state.auditoria_id)
        contagem = {"conforme": 0, "nao_conforme": 0, "em_andamento": 0, "nao_se_aplica": 0}
        for r in respostas:
            contagem[r["status"]] = contagem.get(r["status"], 0) + 1

        cols = st.columns(4)
        cols[0].metric("Conformes", contagem["conforme"])
        cols[1].metric("Não Conformes", contagem["nao_conforme"])
        cols[2].metric("Em Andamento", contagem["em_andamento"])
        cols[3].metric("Não se aplica", contagem["nao_se_aplica"])

        st.markdown("---")
        col_f1, col_f2 = st.columns([1, 4])
        with col_f1:
            if st.button("Finalizar Auditoria", type="primary"):
                finalizar_auditoria(st.session_state.auditoria_id)
                st.session_state.fase = "concluida"
                st.rerun()
        with col_f2:
            if st.button("Rever último controle"):
                st.session_state.controle_index = max(0, idx - 1)
                st.rerun()

    else:
        controle = controles[idx]
        tema_nome = temas.get(controle["tema"], controle["tema"])

        with st.sidebar:
            st.markdown("### Progresso por Tema")
            respostas_atuais = get_respostas_auditoria(st.session_state.auditoria_id)
            r_map = {r["controle_id"]: r["status"] for r in respostas_atuais}

            for tid, tnome in temas.items():
                controles_tema = [c for c in controles if c["tema"] == tid]
                respondidos_t = sum(1 for c in controles_tema if c["id"] in r_map)
                total_t = len(controles_tema)
                pct_t = respondidos_t / total_t if total_t else 0
                st.markdown(f"**{tid}. {tnome[:25]}{'...' if len(tnome) > 25 else ''}**")
                st.progress(pct_t, text=f"{respondidos_t}/{total_t}")

        st.markdown(
            f"""
        <div style='background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:20px 24px;margin-bottom:16px'>
        <div style='font-size:13px;color:#64748b;font-weight:500;margin-bottom:4px'>
            Controle {idx+1} de {total} &nbsp;|&nbsp; Tema: {controle["tema"]} – {tema_nome}
        </div>
        <div style='font-size:22px;font-weight:700;color:#1e293b;margin-bottom:8px'>
            [{controle["id"]}] {controle["nome"]}
        </div>
        <div style='font-size:18px;color:#475569;line-height:1.6'>
            {controle["descricao"]}
        </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        respostas_atuais = get_respostas_auditoria(st.session_state.auditoria_id)
        r_map = {r["controle_id"]: r["status"] for r in respostas_atuais}
        resp_anterior = r_map.get(controle["id"])

        st.markdown("### Como está este controle na empresa?")
        col_s1, col_s2, col_s3 = st.columns(3)
        status_selecionado = None

        with col_s1:
            if st.button(
                "Conforme",
                use_container_width=True,
                type="primary" if resp_anterior == "conforme" else "secondary",
            ):
                status_selecionado = "conforme"

        with col_s2:
            if st.button(
                "Não Conforme",
                use_container_width=True,
                type=(
                    "primary"
                    if resp_anterior in ("nao_conforme", "em_andamento")
                    else "secondary"
                ),
            ):
                status_selecionado = "_nao_conforme_check"

        with col_s3:
            if st.button(
                "Não se aplica",
                use_container_width=True,
                type="primary" if resp_anterior == "nao_se_aplica" else "secondary",
            ):
                status_selecionado = "nao_se_aplica"

        if status_selecionado == "_nao_conforme_check":
            st.session_state[f"_nc_{controle['id']}"] = True

        if st.session_state.get(f"_nc_{controle['id']}", False) or resp_anterior in (
            "nao_conforme",
            "em_andamento",
        ):
            with st.container():
                st.markdown(
                    """
                <div style='border-left:4px solid #eab308;padding:12px 16px;border-radius:0 8px 8px 0;margin:8px 0'>
                <strong>Controle Não Conforme</strong>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                andamento = st.radio(
                    "Existe trabalho em andamento para adequar este controle?",
                    [
                        "Não — registrar como *Não Conforme*",
                        "Sim — existe trabalho em andamento",
                    ],
                    index=1 if resp_anterior == "em_andamento" else 0,
                    key=f"andamento_{controle['id']}",
                )
                obs = st.text_area(
                    "Observações (opcional)",
                    placeholder="Descreva o contexto, plano de ação, prazo estimado...",
                    key=f"obs_{controle['id']}",
                    value=(
                        ""
                        if not resp_anterior
                        else next(
                            (
                                r["observacao"]
                                for r in respostas_atuais
                                if r["controle_id"] == controle["id"]
                            ),
                            "",
                        )
                    ),
                )

                col_nc1, _ = st.columns([1, 4])
                with col_nc1:
                    if st.button(
                        "Salvar e Próximo",
                        type="primary",
                        key=f"salvar_nc_{controle['id']}",
                    ):
                        status_final = (
                            "em_andamento" if "andamento" in andamento else "nao_conforme"
                        )
                        salvar_resposta(
                            st.session_state.auditoria_id,
                            controle["id"],
                            controle["tema"],
                            status_final,
                            obs,
                        )
                        st.session_state[f"_nc_{controle['id']}"] = False
                        st.session_state.controle_index += 1
                        st.rerun()

        elif status_selecionado in ("conforme", "nao_se_aplica"):
            salvar_resposta(
                st.session_state.auditoria_id,
                controle["id"],
                controle["tema"],
                status_selecionado,
                "",
            )
            st.session_state.controle_index += 1
            st.rerun()

        st.markdown("---")
        col_nav1, col_nav2, _ = st.columns([1, 1, 4])
        with col_nav1:
            if st.button("Anterior", disabled=(idx == 0)):
                st.session_state.controle_index = max(0, idx - 1)
                st.rerun()
        with col_nav2:
            if st.button("Pular"):
                st.session_state.controle_index += 1
                st.rerun()


# ── 3ª etapa: concluída ───────────────────────────────────────────────────────
elif st.session_state.fase == "concluida":
    st.balloons()
    st.success("Auditoria concluída com sucesso!")

    st.markdown(f"""
    **Empresa:** {st.session_state.empresa}
    **Norma:** {st.session_state.norma_nome}
    **Auditoria ID:** #{st.session_state.auditoria_id}
    """)

    st.info("Acesse o **Dashboard** no menu lateral para visualizar os resultados.")

    col_c1, _ = st.columns([1, 4])
    with col_c1:
        if st.button("Nova Auditoria"):
            reiniciar()
            st.rerun()
