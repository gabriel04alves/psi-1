import streamlit as st

st.set_page_config(
    page_title="PSI — Plataforma de Segurança da Informação",
    page_icon="🛡️",
    layout="wide",
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div style='text-align:center;padding:40px 0 20px'>
        <div style='font-size:56px'>🛡️</div>
        <h1 style='font-size:2.6rem;font-weight:800;color:#1e293b;margin:8px 0 4px'>
            PSI
        </h1>
        <p style='font-size:1.2rem;color:#64748b;font-weight:500;margin:0'>
            Plataforma de Segurança da Informação
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("---")

# ── Descrição ─────────────────────────────────────────────────────────────────
col_desc, col_stats = st.columns([3, 2], gap="large")

with col_desc:
    st.markdown("### O que é o PSI?")
    st.markdown(
        """
        O **PSI** é uma plataforma para gestão e diagnóstico de conformidade com normas de
        segurança da informação, como **ISO 27002** e **ISO 27701**.

        Com ele você pode:
        - Cadastrar empresas e seus perfis de conformidade
        - Importar normas ISO diretamente de PDFs ou bases internas
        - Conduzir auditorias guiadas controle a controle
        - Acompanhar o nível de conformidade em dashboards interativos
        - Comparar auditorias ao longo do tempo e medir evolução
        - Gerar relatórios em PDF prontos para apresentação
        """
    )

with col_stats:
    st.markdown("### Acesso rápido")
    st.page_link("pages/1_Empresas.py",           label="Empresas",            icon="🏢")
    st.page_link("pages/2_Ingestão_de_Normas.py", label="Ingestão de Normas",  icon="📥")
    st.page_link("pages/3_Nova_Auditoria.py",      label="Nova Auditoria",      icon="🔍")
    st.page_link("pages/4_Dashboard.py",           label="Dashboard",           icon="📊")
    st.page_link("pages/5_Comparativo.py",         label="Comparativo",         icon="📈")
    st.page_link("pages/6_Relatorios.py",          label="Relatórios",          icon="📄")

st.markdown("---")

# ── Fluxograma ────────────────────────────────────────────────────────────────
st.markdown("### Fluxo de uso da plataforma")

st.graphviz_chart(
    """
    digraph fluxo {
        graph [rankdir=LR, bgcolor="#f8fafc", pad="0.5", nodesep="0.6", ranksep="0.9"]
        node  [fontname="Helvetica", fontsize=13, style="filled,rounded", shape=box,
               width=1.8, height=0.55]
        edge  [fontname="Helvetica", fontsize=11, color="#94a3b8", arrowsize=0.8]

        // Etapas principais
        A [label="1. Cadastrar\nEmpresa",    fillcolor="#dbeafe", color="#3b82f6", fontcolor="#1e3a5f"]
        B [label="2. Importar\nNorma",       fillcolor="#ede9fe", color="#7c3aed", fontcolor="#2e1065"]
        C [label="3. Iniciar\nAuditoria",    fillcolor="#dcfce7", color="#16a34a", fontcolor="#14532d"]
        D [label="4. Responder\nControles",  fillcolor="#dcfce7", color="#16a34a", fontcolor="#14532d"]
        E [label="5. Finalizar\nAuditoria",  fillcolor="#fef9c3", color="#ca8a04", fontcolor="#713f12"]
        F [label="6. Dashboard",             fillcolor="#ffedd5", color="#ea580c", fontcolor="#7c2d12"]
        G [label="7. Comparativo",           fillcolor="#fce7f3", color="#db2777", fontcolor="#831843"]
        H [label="8. Relatório PDF",         fillcolor="#e0f2fe", color="#0284c7", fontcolor="#0c4a6e"]

        // Fluxo principal
        A -> B [label="empresa\ncriada"]
        B -> C [label="norma\ndisponível"]
        C -> D [label="auditoria\ncriada"]
        D -> D [label="próximo\ncontrole" style=dashed]
        D -> E [label="todos\nrespondidos"]
        E -> F
        F -> G [label="≥ 2 auditorias"]
        F -> H
        G -> H

        // Reutilização
        E -> C [label="nova\nauditoria" style=dashed color="#cbd5e1"]
    }
    """,
    use_container_width=True,
)

st.markdown("---")

# ── Legenda dos status ─────────────────────────────────────────────────────────
st.markdown("### Status de conformidade")

cols = st.columns(4)
status = [
    ("#22c55e", "Conforme",       "O controle está plenamente implementado."),
    ("#ef4444", "Não Conforme",   "O controle não foi implementado."),
    ("#f59e0b", "Em Andamento",   "Existe trabalho em curso para adequação."),
    ("#94a3b8", "Não se Aplica",  "O controle não é relevante para o contexto."),
]
for col, (cor, label, descricao) in zip(cols, status):
    with col:
        st.markdown(
            f"""
            <div style='border-left:5px solid {cor};padding:10px 14px;
                        border-radius:0 8px 8px 0;background:#f8fafc'>
                <strong style='color:{cor}'>{label}</strong>
                <p style='font-size:13px;color:#475569;margin:4px 0 0'>{descricao}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
