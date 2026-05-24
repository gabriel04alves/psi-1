"""
Página: Ingestão de Controles
Importa normas/ISOs de fontes externas (JSON, CSV ou .py) para o banco de dados.
"""

import ast
import csv
import io
import json
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import (
    deletar_norma,
    get_controles_norma,
    get_normas,
    salvar_norma,
)

st.set_page_config(page_title="Ingestão de Dados | PSI", page_icon="📥", layout="wide")

st.title("Ingestão de Dados")
st.markdown("Importe controles de normas externas (ISO, NIST, CIS, etc.) para o sistema.")

CAMPOS_OBRIGATORIOS = {"id", "tema", "nome"}


# ── Parsers


def _validar_controles(controles: list[dict]) -> tuple[list[dict], list[str]]:
    erros = []
    validos = []
    for i, c in enumerate(controles):
        faltando = CAMPOS_OBRIGATORIOS - set(c.keys())
        if faltando:
            erros.append(f"Linha {i + 1}: campos obrigatórios ausentes: {faltando}")
            continue
        validos.append(
            {
                "id": str(c["id"]).strip(),
                "tema": str(c["tema"]).strip(),
                "tema_nome": str(c.get("tema_nome", "")).strip(),
                "nome": str(c["nome"]).strip(),
                "descricao": str(c.get("descricao", "")).strip(),
            }
        )
    return validos, erros


def _parse_json(content: bytes) -> list[dict]:
    data = json.loads(content)
    if isinstance(data, dict):
        # aceita {"controles": [...]} ou qualquer chave que contenha lista
        for v in data.values():
            if isinstance(v, list):
                return v
        raise ValueError(
            "JSON deve conter uma lista de controles ou uma chave com lista."
        )
    if isinstance(data, list):
        return data
    raise ValueError("Formato JSON não reconhecido.")


def _parse_csv(content: bytes) -> list[dict]:
    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [row for row in reader]


def _parse_python(content: bytes) -> list[dict]:
    """
    Extrai listas de dicts de um arquivo .py usando o AST (sem exec).
    Procura a primeira atribuição cujo valor seja uma lista de dicts
    com pelo menos as chaves 'id', 'tema', 'nome'.
    """
    tree = ast.parse(content.decode("utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.List):
            continue
        try:
            items = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        if not items or not isinstance(items[0], dict):
            continue
        if CAMPOS_OBRIGATORIOS.issubset(items[0].keys()):
            return items
    raise ValueError(
        "Nenhuma lista de controles válida encontrada no arquivo .py. "
        "Certifique-se de que existe uma variável como CONTROLES = [{...}, ...]"
    )


def parse_arquivo(uploaded_file) -> list[dict]:
    name = uploaded_file.name.lower()
    content = uploaded_file.read()
    if name.endswith(".json"):
        return _parse_json(content)
    if name.endswith(".csv"):
        return _parse_csv(content)
    if name.endswith(".py"):
        return _parse_python(content)
    raise ValueError(f"Extensão não suportada: {Path(name).suffix}")


# ── UI principal

tab_importar, tab_normas = st.tabs(["Importar Norma", "Normas cadastradas"])

with tab_importar:
    st.subheader("1. Metadados da norma")
    col1, col2 = st.columns(2)
    with col1:
        nome_norma = st.text_input("Nome da norma", placeholder="ex: ISO 27001:2022")
    with col2:
        versao_norma = st.text_input("Versão / Ano", placeholder="ex: 2022")

    st.subheader("2. Arquivo de controles")
    st.caption("Formatos aceitos: **JSON**, **CSV** ou **Python (.py)**")

    with st.expander("Ver especificação do formato"):
        col_j, col_c, col_p = st.columns(3)
        with col_j:
            st.markdown("**JSON**")
            st.code(
                '[{\n  "id": "5.1",\n  "tema": "5",\n  "tema_nome": "Organizacional",\n'
                '  "nome": "Políticas de SI",\n  "descricao": "..."\n}]',
                language="json",
            )
        with col_c:
            st.markdown("**CSV**")
            st.code(
                "id,tema,tema_nome,nome,descricao\n5.1,5,Organizacional,Políticas de SI,...",
                language="text",
            )
        with col_p:
            st.markdown("**Python (.py)**")
            st.code(
                'CONTROLES = [\n  {\n    "id": "5.1",\n    "tema": "5",\n'
                '    "nome": "Políticas de SI",\n    "descricao": "..."\n  }\n]',
                language="python",
            )

    uploaded = st.file_uploader(
        "Selecione o arquivo",
        type=["json", "csv", "py"],
        label_visibility="collapsed",
    )

    if uploaded:
        try:
            controles_raw = parse_arquivo(uploaded)
            controles, erros = _validar_controles(controles_raw)
        except Exception as exc:
            st.error(f"Erro ao processar arquivo: {exc}")
            controles, erros = [], []

        if erros:
            with st.expander(f"{len(erros)} erro(s) encontrados"):
                for e in erros:
                    st.warning(e)

        if controles:
            st.subheader("3. Preview")

            temas = {}
            for c in controles:
                tid = c["tema"]
                if tid not in temas:
                    temas[tid] = c["tema_nome"] or tid

            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Controles", len(controles))
            col_m2.metric("Temas / Categorias", len(temas))
            col_m3.metric("Inválidos descartados", len(erros))

            df = pd.DataFrame(controles)[
                ["id", "tema", "tema_nome", "nome", "descricao"]
            ]
            df.columns = ["ID", "Tema", "Nome do Tema", "Controle", "Descrição"]
            st.dataframe(df, use_container_width=True, height=320)

            st.subheader("4. Confirmar ingestão")
            if not nome_norma.strip():
                st.warning("Preencha o nome da norma antes de confirmar.")
            else:
                if st.button("Salvar no banco de dados", type="primary", icon="💾"):
                    norma_id = salvar_norma(
                        nome_norma.strip(), versao_norma.strip(), controles
                    )
                    st.success(
                        f"Norma **{nome_norma}** salva com sucesso! "
                        f"{len(controles)} controles importados (ID da norma: {norma_id})."
                    )
                    st.balloons()

with tab_normas:
    st.subheader("Normas importadas")
    normas = get_normas()

    if not normas:
        st.markdown(
            """
            <div style='
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                padding: 32px 28px;
                text-align: center;
                margin-top: 16px;
            '>
                <div style='font-size: 40px; margin-bottom: 12px'>📭</div>
                <div style='font-size: 18px; font-weight: 600; color: #1e293b; margin-bottom: 8px'>
                    Nenhuma norma cadastrada
                </div>
                <div style='font-size: 14px; color: #64748b'>
                    Acesse a aba <strong>Importar</strong> para adicionar uma norma
                    a partir de um arquivo JSON, CSV ou Python.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        for norma in normas:
            with st.expander(
                f"**{norma['nome']}** — {norma['versao'] or 'versão não informada'} "
                f"· {norma['data_ingestao'][:10]}"
            ):
                controles = get_controles_norma(norma["id"])
                st.caption(f"{len(controles)} controles · origem: {norma['origem']}")

                if controles:
                    df = pd.DataFrame(controles)[
                        ["controle_id", "tema_id", "tema_nome", "nome", "descricao"]
                    ]
                    df.columns = ["ID", "Tema", "Nome do Tema", "Controle", "Descrição"]
                    st.dataframe(df, use_container_width=True, height=280)

                if st.button(
                    "Remover esta norma",
                    key=f"del_{norma['id']}",
                    type="secondary",
                    icon="🗑️",
                ):
                    deletar_norma(norma["id"])
                    st.warning(f"Norma **{norma['nome']}** removida.")
                    st.rerun()
