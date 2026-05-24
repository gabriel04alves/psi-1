import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import (
    deletar_empresa,
    get_auditorias,
    get_connection,
    get_empresa,
    get_empresas,
    salvar_empresa,
)

st.set_page_config(page_title="Empresa | PSI", page_icon="🏢", layout="wide")

PORTES = ["", "Microempresa (ME)", "Pequena", "Média", "Grande", "Multinacional"]


# ── Helpers locais


@st.dialog("Empresa")
def _form_empresa():
    modo = st.session_state.get("_emp_modo", "nova")
    v = st.session_state.get("_emp_dados", {})
    nome_original = v.get("nome", "")

    st.subheader("Editar empresa" if modo == "editar" else "Cadastrar nova empresa")

    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input(
            "Nome fantasia *", value=v.get("nome", ""), placeholder="Ex: Acme Corp"
        )
        cnpj = st.text_input(
            "CNPJ", value=v.get("cnpj", ""), placeholder="00.000.000/0001-00"
        )
    with col2:
        razao_social = st.text_input(
            "Razão social",
            value=v.get("razao_social", ""),
            placeholder="Ex: Acme Tecnologia Ltda",
        )
        setor = st.text_input(
            "Setor / Ramo",
            value=v.get("setor", ""),
            placeholder="Ex: Tecnologia da Informação",
        )

    col3, col4 = st.columns(2)
    with col3:
        porte_idx = (
            PORTES.index(v.get("porte", "")) if v.get("porte", "") in PORTES else 0
        )
        porte = st.selectbox("Porte", PORTES, index=porte_idx)
    with col4:
        responsavel = st.text_input(
            "Responsável pelo SGSI",
            value=v.get("responsavel", ""),
            placeholder="Nome do gestor",
        )

    if not nome.strip():
        st.caption("Nome fantasia é obrigatório.")

    st.markdown("---")
    col_s, col_c = st.columns(2)
    with col_s:
        if st.button(
            "Salvar",
            type="primary",
            disabled=not nome.strip(),
            use_container_width=True,
            icon="💾",
        ):
            nome_novo = nome.strip()
            salvar_empresa(
                {
                    "nome": nome_novo,
                    "cnpj": cnpj.strip(),
                    "razao_social": razao_social.strip(),
                    "setor": setor.strip(),
                    "porte": porte,
                    "responsavel": responsavel.strip(),
                },
                nome_original=nome_original if modo == "editar" else None,
            )
            if nome_original and nome_novo != nome_original:
                # Update session state if company name changed
                if st.session_state.get("empresa_selecionada") == nome_original:
                    st.session_state["empresa_selecionada"] = nome_novo
            if not st.session_state.get("empresa_selecionada"):
                st.session_state["empresa_selecionada"] = nome_novo
            st.session_state.pop("_emp_modo", None)
            st.session_state.pop("_emp_dados", None)
            st.rerun()
    with col_c:
        if st.button("Cancelar", use_container_width=True):
            st.session_state.pop("_emp_modo", None)
            st.session_state.pop("_emp_dados", None)
            st.rerun()


# ── Dados base
st.title("Empresa")
st.markdown("---")

todas_auditorias = get_auditorias()
perfil = get_empresa()
empresa_atual = st.session_state.get("empresa_selecionada")

# Get all companies from database (not just those with audits)
todas_empresas_db = get_empresas()
todas_empresas = [emp["nome"] for emp in todas_empresas_db]

# ── Alertas de topo
col_status, col_nova = st.columns([6, 1])
with col_status:
    if not todas_empresas:
        st.warning(
            "Nenhuma empresa cadastrada. Clique em **Nova empresa** para começar."
        )
    elif not empresa_atual:
        st.info("Selecione uma empresa abaixo para ativar as análises.")
    else:
        st.success(f"Empresa ativa: **{empresa_atual}**")

with col_nova:
    if st.button("Nova empresa", type="primary", use_container_width=True, icon="➕"):
        st.session_state["_emp_modo"] = "nova"
        st.session_state["_emp_dados"] = {}

st.markdown("---")

# ── Lista de empresas
for emp in todas_empresas_db:
    nome_emp = emp["nome"]
    empresa_id = emp["id"]
    aud_emp = [a for a in todas_auditorias if a["empresa"] == nome_emp]
    n_concluidas = sum(1 for a in aud_emp if a["status"] == "concluida")
    n_andamento = sum(1 for a in aud_emp if a["status"] == "em_andamento")
    is_ativa = nome_emp == empresa_atual
    has_profile = perfil is not None and perfil["nome"] == nome_emp
    confirm_key = f"_del_{nome_emp}"

    with st.container(border=True):
        col_info, col_acoes = st.columns([6, 2])

        # ── Informações da empresa
        with col_info:
            badge = "  ·  **[AUDITORIA ATUAL]**" if is_ativa else ""
            st.markdown(f"**{nome_emp}**{badge}")

            if has_profile:
                detalhes = []
                if perfil.get("razao_social"):
                    detalhes.append(perfil["razao_social"])
                if perfil.get("cnpj"):
                    detalhes.append(f"CNPJ: {perfil['cnpj']}")
                if perfil.get("setor"):
                    detalhes.append(f"Setor: {perfil['setor']}")
                if perfil.get("porte"):
                    detalhes.append(f"Porte: {perfil['porte']}")
                if perfil.get("responsavel"):
                    detalhes.append(f"Resp.: {perfil['responsavel']}")
                if detalhes:
                    st.caption(" · ".join(detalhes))
                st.caption(f"Atualizado em: {perfil['atualizado_em'][:16]}")
            else:
                st.caption("Sem perfil cadastrado")

            partes = [f"{len(aud_emp)} auditoria(s)"] if aud_emp else ["Sem auditorias"]
            if n_concluidas:
                partes.append(f"{n_concluidas} concluída(s)")
            if n_andamento:
                partes.append(f"{n_andamento} em andamento")
            st.caption(" · ".join(partes))

        # ── Ações
        with col_acoes:
            if not is_ativa:
                if st.button(
                    "Selecionar",
                    key=f"sel_{nome_emp}",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state["empresa_selecionada"] = nome_emp
                    st.rerun()

            if st.button(
                "Editar", key=f"edit_{nome_emp}", use_container_width=True, icon="✏️"
            ):
                dados = {"nome": nome_emp}
                if has_profile:
                    dados.update(
                        {
                            k: perfil.get(k, "")
                            for k in [
                                "cnpj",
                                "razao_social",
                                "setor",
                                "porte",
                                "responsavel",
                            ]
                        }
                    )
                st.session_state["_emp_modo"] = "editar"
                st.session_state["_emp_dados"] = dados

            if st.session_state.get(confirm_key):
                st.warning("Apagar empresa e todos os registros relacionados?")
                cy, cn = st.columns(2)
                if cy.button(
                    "Confirmar",
                    key=f"del_y_{nome_emp}",
                    type="primary",
                    use_container_width=True,
                ):
                    deletar_empresa(empresa_id)
                    if empresa_atual == nome_emp:
                        st.session_state.pop("empresa_selecionada", None)
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
                if cn.button(
                    "Cancelar", key=f"del_n_{nome_emp}", use_container_width=True
                ):
                    st.session_state.pop(confirm_key, None)
                    st.rerun()
            else:
                if st.button(
                    "Apagar", key=f"del_{nome_emp}", use_container_width=True, icon="🗑️"
                ):
                    st.session_state[confirm_key] = True
                    st.rerun()

# ── Abrir modal quando solicitado
if st.session_state.get("_emp_modo"):
    _form_empresa()
