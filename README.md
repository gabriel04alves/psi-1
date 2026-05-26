# PSI — Plataforma de Segurança da Informação

> Projeto desenvolvido como atividade da disciplina de Segurança da Informação.  
> Especificação: [PSI.md](https://github.com/mehranmisaghi/cybersecurity/blob/main/projetos/PSI.md)

---

## O que é o PSI?

O **Projeto de Segurança de Informação** é uma plataforma web para gestão e diagnóstico de conformidade com normas de segurança da informação, como **ISO/IEC 27002** e **ISO/IEC 27701**.

### Principais vantagens

- **Local-first e seguro** — toda a aplicação roda na máquina do próprio usuário. Nenhum dado é enviado a servidores externos; o banco de dados (SQLite) fica armazenado localmente.
- **Portável** — funciona para diferentes normas.
- **Sem dependências de nuvem** — funciona completamente offline após a instalação.

### Funcionalidades

| Módulo             | Descrição                                                         |
| ------------------ | ----------------------------------------------------------------- |
| Empresas           | Cadastro e gerenciamento de perfis de conformidade por empresa    |
| Ingestão de Normas | Importação de controles ISO diretamente de PDFs ou bases internas |
| Nova Auditoria     | Diagnóstico guiado controle a controle                            |
| Dashboard          | Acompanhamento do nível de conformidade com gráficos interativos  |
| Comparativo        | Comparação entre auditorias ao longo do tempo para medir evolução |
| Relatórios         | Geração de relatórios em PDF prontos para apresentação            |

![|Fluxograma](./fluxograma.png)

### Status de conformidade

| Status            | Descrição                                  |
| ----------------- | ------------------------------------------ |
| **Conforme**      | O controle está plenamente implementado    |
| **Não Conforme**  | O controle não foi implementado            |
| **Em Andamento**  | Existe trabalho em curso para adequação    |
| **Não se Aplica** | O controle não é relevante para o contexto |

---

## Stack tecnológica

- **Python 3.11+** com [Streamlit](https://streamlit.io/) como framework web
- **SQLite** para persistência local de dados
- **Plotly** para visualizações interativas
- **ReportLab** para geração de relatórios PDF
- **pdfplumber / pdfminer** para extração de controles a partir de PDFs ISO
- **PyInstaller** para empacotamento como executável standalone

---

## Instalação (modo desenvolvimento)

### Pré-requisitos

- Python 3.11 ou superior

### Passos

```bash
# 1. Clone o repositório
git clone https://github.com/gabriel04alves/psi-1
cd psi-1

# 2. Instale o Graphviz (requisito do sistema)
# Linux (Fedora/RHEL):
sudo dnf install -y python3 python3-pip python3-virtualenv graphviz graphviz-devel

# Linux (Ubuntu/Debian):
sudo apt install -y python3 python3-pip python3-venv graphviz libgraphviz-dev

# macOS:
brew install python@3.11 graphviz

# Windows: instale o Python e o Graphviz em https://graphviz.org/download/
# e adicione ambos ao PATH
```

> **Atenção:** o Graphviz precisa estar disponível no PATH do sistema operacional — o pacote Python `graphviz` (incluído em `requirements.txt`) é apenas uma interface e depende do binário `dot` instalado nativamente. Verifique com `dot -V` antes de iniciar a aplicação.

```bash
# 3. Crie e ative o ambiente virtual
python3 -m venv venv
source venv/bin/activate      # Linux / macOS
# venv\Scripts\activate       # Windows

# 4. Instale as dependências
pip install -r requirements.txt

# 5. Inicie a aplicação
streamlit run streamlit_app.py
```

A interface abre automaticamente em `http://localhost:8501`.

### Dados de demonstração (opcional)

Para explorar a plataforma sem cadastrar dados manualmente, execute o script de populate. Ele cria 3 empresas, importa as normas ISO 27002 e ISO 27701 e gera múltiplas auditorias com respostas fictícias simulando evolução de conformidade ao longo do tempo.

```bash
# Insere dados sem apagar o que já existe
python utils/populate.py

# Limpa o banco e recria tudo do zero
python utils/populate.py --reset
```

O terminal exibe um resumo do que foi inserido — em seguida basta abrir qualquer empresa na página **Empresas** para explorar dashboards, comparativos e relatórios já populados.

---

## Guia de uso

### Pré-condição: norma ISO atualizada

O sistema não distribui o texto das normas ISO por questões de licenciamento. Antes de iniciar uma auditoria você precisa ter em mãos o **PDF oficial e atualizado** da norma desejada (ex.: ABNT NBR ISO/IEC 27002:2022).

### Passo 1 — Cadastrar a empresa

Acesse **Empresas** e registre o perfil da organização que será auditada (nome, CNPJ, setor, porte, responsável).

### Passo 2 — Formatar a ISO (obrigatório para PDFs novos)

> A plataforma precisa dos controles em formato estruturado. Se você já tiver um arquivo `.json`, `.csv` ou `.py` com os controles, pule para o Passo 3.

1. Acesse **🧰 Formatar ISO a partir de PDF** no menu lateral.
2. Faça upload do PDF da norma.
3. Clique em **Extrair conteúdo do PDF** — o sistema identifica automaticamente os controles no padrão ABNT.
4. Baixe o arquivo **JSON** gerado.

O arquivo exportado segue a estrutura:

```json
[
  {
    "id": "5.1",
    "tema": "5",
    "tema_nome": "Controles Organizacionais",
    "nome": "Políticas para segurança da informação",
    "descricao": "..."
  }
]
```

Também são aceitos **CSV** e **Python (`.py`)** com a mesma estrutura de campos (`id`, `tema`, `nome` são obrigatórios):

```csv
id,tema,tema_nome,nome,descricao
5.1,5,Organizacional,Políticas de SI,...
```

```python
CONTROLES = [
  {"id": "5.1", "tema": "5", "nome": "Políticas de SI", "descricao": "..."}
]
```

### Passo 3 — Importar a norma

1. Acesse **📥 Ingestão de Normas**.
2. Preencha o nome e a versão da norma (ex.: `ISO 27002`, `2022`).
3. Faça upload do arquivo gerado no passo anterior (`.json`, `.csv` ou `.py`).
4. Confira o preview dos controles e clique em **Salvar no banco de dados**.

### Passo 4 — Conduzir a auditoria

1. Acesse **🔍 Nova Auditoria**, selecione a empresa e a norma importada.
2. Responda cada controle com um dos status: **Conforme**, **Não Conforme**, **Em Andamento** ou **Não se Aplica**, adicionando observações quando necessário.
3. Finalize a auditoria ao concluir todos os controles.

### Passo 5 — Acompanhar e exportar resultados

| Página             | O que fazer                                                        |
| ------------------ | ------------------------------------------------------------------ |
| **📊 Dashboard**   | Visualize o nível de conformidade por tema e controle              |
| **📈 Comparativo** | Compare duas ou mais auditorias da mesma empresa ao longo do tempo |
| **📄 Relatórios**  | Gere e baixe o relatório em PDF para apresentação                  |

---

## Estrutura do projeto

```
psi-1/
├── streamlit_app.py        # Página inicial / ponto de entrada
├── pages/                  # Páginas da aplicação (Streamlit multipage)
│   ├── 1_Empresas.py
│   ├── 2_Ingestão_de_Normas.py
│   ├── 3_Nova_Auditoria.py
│   ├── 4_Dashboard.py
│   ├── 5_Comparativo.py
│   └── 6_Relatorios.py
├── database/
│   └── db.py               # Camada de acesso ao banco SQLite
├── data/                   # Bases de controles ISO e banco local
├── utils/                  # Utilitários (PDF, gráficos, relatórios)
├── requirements.txt
```

![Diagrama ER](./diagrama_modelo.png)

---

## Armazenamento de dados

O banco de dados é armazenado localmente, sem nenhuma comunicação com serviços externos e pode ser importado e exportado.
