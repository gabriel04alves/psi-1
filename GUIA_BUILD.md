# Guia de Compilação — PSI

Este guia explica como empacotar a aplicação PSI em um executável standalone
usando **PyInstaller**. O resultado é uma pasta `dist/PSI/` que contém tudo
que o usuário final precisa — nenhum Python instalado é necessário para rodar.

> **Importante:** o build deve ser feito **no sistema operacional de destino**.
> Um build feito no Linux não gera um executável para Windows ou macOS.

---

## Visão geral do processo

```
código-fonte  →  PyInstaller  →  dist/PSI/
                                  ├── PSI            (executável)
                                  ├── _internal/     (Python + dependências)
                                  └── ...
```

Quando o usuário executa `PSI`, o programa:

1. Inicia um servidor Streamlit local (porta 8501 por padrão).
2. Abre automaticamente o navegador em `http://localhost:8501`.
3. O banco de dados é armazenado em um diretório do usuário (não no bundle):
   - **Linux:** `~/.local/share/PSI/auditoria.db`
   - **macOS:** `~/Library/Application Support/PSI/auditoria.db`
   - **Windows:** `%APPDATA%\PSI\auditoria.db`

---

## 1. Fedora Linux

### 1.1 Pré-requisitos

```bash
# Dependências do sistema
sudo dnf install -y python3 python3-pip python3-virtualenv \
                    graphviz graphviz-devel \
                    upx

# Confirme que o Graphviz está acessível
dot -V
```

### 1.2 Preparar ambiente Python

```bash
cd /caminho/para/psi-1

# Criar e ativar virtualenv (se ainda não existir)
python3 -m venv venv
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
pip install pyinstaller
```

### 1.3 Compilar

```bash
# Opção A — script automatizado
chmod +x build.sh
./build.sh

# Opção B — comando direto
pyinstaller PSI.spec --clean --noconfirm
```

### 1.4 Testar o executável

```bash
./dist/PSI/PSI
# O navegador deve abrir em http://localhost:8501
```

### 1.5 Distribuir

Comprima a pasta `dist/PSI/` e envie ao usuário:

```bash
tar -czvf PSI-linux.tar.gz -C dist PSI
```

O usuário descomprime e executa `./PSI/PSI` — nenhuma instalação adicional necessária.

---

## 2. Windows

### 2.1 Pré-requisitos

| Ferramenta                            | Download                                                                                  |
| ------------------------------------- | ----------------------------------------------------------------------------------------- |
| Python 3.11+                          | [python.org/downloads](https://www.python.org/downloads/) — marque **Add Python to PATH** |
| Graphviz                              | [graphviz.org/download](https://graphviz.org/download/) — baixe o instalador `.exe`       |
| UPX (opcional, comprime o executável) | [github.com/upx/upx/releases](https://github.com/upx/upx/releases)                        |

**Após instalar o Graphviz**, adicione o diretório `bin` ao PATH do sistema ou
defina a variável de ambiente antes do build:

```cmd
set GRAPHVIZ_BIN=C:\Program Files\Graphviz\bin
```

### 2.2 Preparar ambiente Python

Abra o **Prompt de Comando** ou **PowerShell** na pasta do projeto:

```cmd
cd C:\caminho\para\psi-1

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
pip install pyinstaller
```

### 2.3 Compilar

```cmd
REM Opção A — script automatizado
build.bat

REM Opção B — comando direto
pyinstaller PSI.spec --clean --noconfirm
```

### 2.4 Testar o executável

```cmd
dist\PSI\PSI.exe
```

O navegador padrão deve abrir em `http://localhost:8501`.

### 2.5 Distribuir

Comprima `dist\PSI\` com o Explorador de Arquivos ou:

```powershell
Compress-Archive -Path dist\PSI -DestinationPath PSI-windows.zip
```

O usuário descomprime e executa `PSI.exe` — sem instalação de Python necessária.

---

## 3. macOS

### 3.1 Pré-requisitos

```bash
# Instale o Homebrew se ainda não tiver
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Dependências
brew install python@3.11 graphviz upx
```

### 3.2 Preparar ambiente Python

```bash
cd /caminho/para/psi-1

python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
pip install pyinstaller
```

### 3.3 Compilar

```bash
chmod +x build.sh
./build.sh
```

### 3.4 Criar um `.app` (opcional)

Para uma experiência mais nativa no macOS, você pode criar um bundle `.app`
adicionando a seção `BUNDLE` ao `PSI.spec`:

```python
# Adicione ao final de PSI.spec (após o COLLECT):
app = BUNDLE(
    coll,
    name="PSI.app",
    icon=None,
    bundle_identifier="br.com.psi.app",
    info_plist={
        "CFBundleShortVersionString": "1.0.0",
        "NSHighResolutionCapable": True,
    },
)
```

Então execute o build normalmente — a pasta `dist/` conterá tanto `PSI/`
quanto `PSI.app`.

### 3.5 Testar

```bash
./dist/PSI/PSI
# ou, se criou o .app:
open dist/PSI.app
```

### 3.6 Distribuir

```bash
# Pasta simples
tar -czvf PSI-macos.tar.gz -C dist PSI

# .app (se criado)
zip -r PSI-macos.zip dist/PSI.app
```

> **Nota macOS:** na primeira execução, o sistema pode bloquear o app com
> "desenvolvedor não identificado". Para liberar:
> `System Settings → Privacy & Security → Open Anyway`
> ou via terminal: `xattr -dr com.apple.quarantine dist/PSI/PSI`

## Referência rápida

| Plataforma | Pré-requisito extra             | Script de build | Executável gerado  |
| ---------- | ------------------------------- | --------------- | ------------------ |
| Fedora     | `graphviz graphviz-devel` (dnf) | `./build.sh`    | `dist/PSI/PSI`     |
| Windows    | Graphviz installer + PATH       | `build.bat`     | `dist\PSI\PSI.exe` |
| macOS      | `brew install graphviz`         | `./build.sh`    | `dist/PSI/PSI`     |
