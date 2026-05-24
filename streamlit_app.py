import streamlit as st

st.set_page_config(
    page_title="PSI - Ferramenta para Auditoria",
    layout="wide",
)

st.title("🔒 PSI - Ferramenta para Auditoria")
st.markdown("**Ferramenta de Diagnóstico de Conformidade ISO 27001 / ISO 27701**")
st.markdown("---")

# Abas principais
tab1, tab2, tab3 = st.tabs(["📋 Guia de Uso", "🚀 Fluxo da Aplicação", "🎯 Módulos"])

# ── TAB 1: GUIA DE USO ────────────────────────────────────────────────────────
with tab1:
    st.header("📖 Guia Completo de Uso")

    st.markdown("""
    ### O que é o PSI?
    
    O **PSI** é uma ferramenta especializada em diagnóstico de conformidade com as normas:
    - **ISO 27001**: Sistema de Gestão da Segurança da Informação (SGSI)
    - **ISO 27701**: Extensão de privacidade do SGSI
    
    A ferramenta permite avaliar o nível de conformidade de sua organização de forma
    sistemática, respondendo controle por controle, e gerar relatórios analíticos para
    orientar suas melhorias.
    """)

    st.divider()

    # Seção de Preparação
    with st.expander("👤 **Passo 1: Preparação Inicial**", expanded=True):
        st.markdown("""
        #### O que você precisa:
        
        1. **Dados da Empresa**: Informações básicas como nome, CNPJ, setor, porte
        2. **Normas**: Importar ISO 27001 ou ISO 27701 na base de dados
        3. **Responsável**: Indicar quem conduzirá a auditoria
        
        #### Onde fazer isso?
        - Acesse **Importar Base de Dados** para carregar as normas
        - Vá para **Empresas** para registrar suas organizações
        - Configure os dados de ingestão em **Ingestão de Dados**
        """)

    # Seção de Auditoria
    with st.expander("📊 **Passo 2: Conduzir a Auditoria**"):
        st.markdown("""
        #### Como funciona:
        
        1. **Selecione a Empresa**: Escolha qual organização será auditada
        2. **Escolha o Módulo**: ISO 27001 ou ISO 27701
        3. **Responda os Controles**: Para cada controle, indique o status:
           - ✅ **Conforme**: O controle está implementado adequadamente
           - ⚠️ **Não Conforme**: O controle não está implementado ou não atende
           - 🔄 **Em Processo**: O controle está sendo implementado
        
        4. **Adicione Observações**: Comente sobre cada controle se necessário
        5. **Finalize**: Marque a auditoria como concluída
        
        #### Dicas:
        - Reúna documentação e evidências antes de iniciar
        - Consulte especialistas em segurança da informação
        - Leve tempo para avaliar cada controle corretamente
        """)

    # Seção de Análise
    with st.expander("📈 **Passo 3: Análise dos Resultados**"):
        st.markdown("""
        #### O Dashboard oferece:
        
        - **Conformidade Geral**: Percentual de conformidade com a norma
        - **Conformidade por Tema**: Detalhamento em cada área temática
        - **Visualizações**: Gráficos para facilitar a compreensão
        - **Métricas Detalhadas**: Informações de controles conformes e não conformes
        
        #### Use para:
        - Identificar áreas críticas de não conformidade
        - Planejar ações corretivas
        - Apresentar resultados para stakeholders
        """)

    # Seção de Comparativo
    with st.expander("🔀 **Passo 4: Comparativo e Relatórios**"):
        st.markdown("""
        #### Funcionalidades disponíveis:
        
        1. **Comparativo Entre Auditorias**:
           - Compare resultados de períodos diferentes
           - Acompanhe evolução da conformidade
           - Identifique tendências
        
        2. **Geração de Relatórios**:
           - Relatórios completos: visão geral + detalhes de cada controle
           - Relatórios por tema: foco em áreas específicas
           - Exportar para diferentes formatos
        
        #### Ideal para:
        - Comunicação com direção
        - Cumprimento de requisitos regulatórios
        - Documentação de conformidade
        """)

# ── TAB 2: FLUXO DA APLICAÇÃO ─────────────────────────────────────────────────
with tab2:
    st.header("🚀 Fluxo da Aplicação")

    st.markdown("""
    ### Jornada Típica de uma Auditoria
    """)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("""
        #### 📥 **Configuração Inicial**
        1. Importar normas ISO
        2. Registrar empresas
        3. Configurar dados de ingestão
        """)

    with col2:
        st.markdown("""
        #### 🎯 **Execução**
        1. Criar nova auditoria
        2. Responder controles
        3. Adicionar observações
        4. Finalizar auditoria
        """)

    with col3:
        st.markdown("""
        #### 📊 **Análise e Decisão**
        1. Visualizar dashboard
        2. Comparar com auditorias anteriores
        3. Gerar relatórios
        4. Planejar ações
        """)

    st.divider()

    st.markdown("### Diagrama de Fluxo")
    st.markdown("""
    ```
    ┌─────────────────────────────────────────────────────────────────┐
    │                    INÍCIO DA AUDITORIA                           │
    └────────────────────────────┬────────────────────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Importar Base de      │
                    │  Dados (Normas)        │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Gerenciar Empresas    │
                    │  (Registrar dados)     │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Ingestão de Dados     │
                    │  (Normas e controles)  │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Nova Auditoria        │
                    │  (Responder controles) │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Dashboard             │
                    │  (Visualizar resultados)│
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  Comparativo &         │
                    │  Relatórios            │
                    └────────────┬────────────┘
                                 │
                ┌────────────────▼─────────────────┐
                │  ANÁLISE E PLANEJAMENTO DE AÇÕES │
                └────────────────────────────────────┘
    ```
    """)

    st.divider()

    st.markdown("### Componentes Principais")

    st.markdown("""
    - **Empresa**: Organização sendo auditada
    - **Norma**: ISO 27001 ou ISO 27701
    - **Controle**: Item específico a ser avaliado (ex: A.5.1)
    - **Auditoria**: Sessão de avaliação para uma empresa e norma
    - **Resposta**: Resultado da avaliação de cada controle
    """)

# ── TAB 3: MÓDULOS ────────────────────────────────────────────────────────────
with tab3:
    st.header("🎯 Módulos Principais")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        ### 📥 Importar Base de Dados
        **Função**: Carregar as normas ISO na aplicação
        
        - Importe ISO 27001 ou ISO 27701
        - Define os controles disponíveis
        - Básico para toda auditoria
        
        [Ir para Importação →](pages/0_Importar_Base_de_Dados.py)
        """)

        st.markdown("---")

        st.markdown("""
        ### 👥 Empresas
        **Função**: Gerenciar dados das organizações
        
        - Cadastrar novas empresas
        - Editar dados existentes
        - Ver histórico de auditorias
        - Deletar registros
        
        [Ir para Empresas →](pages/1_Empresas.py)
        """)

        st.markdown("---")

        st.markdown("""
        ### 📤 Ingestão de Dados
        **Função**: Processar dados de controles
        
        - Importar controles das normas
        - Validar estrutura dos dados
        - Preparar para auditorias
        
        [Ir para Ingestão →](pages/2_Ingestão_de_Dados.py)
        """)

    with col2:
        st.markdown("""
        ### 🎯 Nova Auditoria
        **Função**: Executar auditoria interativa
        
        - Selecionar empresa e norma
        - Responder cada controle
        - Adicionar observações
        - Finalizar avaliação
        
        [Ir para Auditoria →](pages/3_Nova_Auditoria.py)
        """)

        st.markdown("---")

        st.markdown("""
        ### 📊 Dashboard
        **Função**: Visualizar resultados
        
        - Gráficos de conformidade
        - Métricas por tema
        - Análise detalhada
        - Exportar dados
        
        [Ir para Dashboard →](pages/4_Dashboard.py)
        """)

        st.markdown("---")

        st.markdown("""
        ### 🔀 Comparativo & Relatórios
        **Função**: Análise comparativa e geração de documentos
        
        - Comparar auditorias anteriores
        - Gerar relatórios completos
        - Exportar resultados
        - Acompanhar tendências
        
        [Ir para Comparativo →](pages/5_Comparativo.py)
        
        [Ir para Relatórios →](pages/6_Relatorios.py)
        """)

# ── RODAPÉ ────────────────────────────────────────────────────────────────────
st.divider()

st.markdown("""
### 💡 Dicas Importantes

- **Comece pelas normas**: Sempre importe as normas antes de qualquer auditoria
- **Organize os dados**: Mantenha as informações das empresas atualizadas
- **Seja consistente**: Use critérios padronizados ao avaliar controles
- **Documente**: Adicione observações detalhadas em cada controle
- **Revise regularmente**: Conduza auditorias periódicas para acompanhar conformidade

### 📞 Suporte

Para mais informações sobre ISO 27001 e ISO 27701, consulte:
- Site ISO: www.iso.org
- ABNT: www.abnt.org.br
- Comunidades de segurança da informação
""")
