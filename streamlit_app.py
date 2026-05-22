import streamlit as st

st.set_page_config(
    page_title="PSI - Ferramenta para Auditoria",
    layout="wide",
)

st.title("PSI - Ferramenta para Auditoria")
st.markdown("**Ferramenta de Diagnóstico de Conformidade ISO 27001 / ISO 27701**")
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### Nova Auditoria
    Inicie um novo diagnóstico de conformidade para uma empresa.
    Selecione o módulo (ISO 27001 ou 27701) e responda controle por controle.
    """)
    st.page_link("pages/1_Nova_Auditoria.py", label="Auditoria")

with col2:
    st.markdown("""
    ### Dashboard
    Visualize os resultados de uma auditoria concluída.
    Gráficos de pizza, barras e gauge com conformidade geral e por tema.
    """)
    st.page_link("pages/2_Dashboard.py", label="Dashboard")


with col3:
    st.markdown("""
    ### Comparativo & Relatórios
    Compare auditorias anteriores e gere relatórios
    completos ou por tipo de controle.
    """)
    st.page_link("pages/3_Comparativo.py", label="Comparativo")
    st.page_link("pages/4_Relatorios.py", label="Relatórios")
