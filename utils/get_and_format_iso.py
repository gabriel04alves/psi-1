#!/usr/bin/env python3
"""
Extrator genérico de controles de normas ISO/IEC (ABNT NBR)
===========================================================
Funciona com qualquer norma ISO que siga o padrão ABNT:
  - Controles marcados por linha "Controle" isolada
  - Estrutura de cabeçalhos hierárquicos (5.1, A.1.2.2, B.3.4 …)

Uso:
    python extrator_iso.py <pdf> [saida.json]

Dependência única:
    pip install pdfplumber

Nenhum dado fixo — tudo é detectado no PDF.
"""

import json
import re
import sys
import pdfplumber
from collections import Counter
from pathlib import Path


# 1 extração e limpeza
def extract_pages(pdf_path: str):
    """Retorna lista de texto por página."""
    with pdfplumber.open(pdf_path) as pdf:
        return [pg.extract_text() or "" for pg in pdf.pages]


def detect_boilerplate(pages: list[str], threshold: float = 0.85) -> set[str]:
    """
    Linhas que aparecem em mais de `threshold` das páginas são
    cabeçalho/rodapé/watermark — devem ser removidas.
    """
    n = len(pages)
    counts: Counter = Counter()
    for page in pages:
        seen = set()
        for line in page.splitlines():
            line = line.strip()
            if line and line not in seen:
                counts[line] += 1
                seen.add(line)
    min_count = max(2, int(n * threshold))
    return {line for line, cnt in counts.items() if cnt >= min_count}


def clean_pages(pages: list[str], boilerplate: set[str]) -> str:
    """
    Remove boilerplate e concatena todas as páginas em texto único.
    Injeta marcador __PB__ nas quebras de página para não fundir
    linhas de páginas adjacentes.
    """
    chunks = []
    for page in pages:
        cleaned = []
        for line in page.splitlines():
            if line.strip() not in boilerplate:
                cleaned.append(line)
        chunks.append("\n".join(cleaned))
    return "\n__PB__\n".join(chunks)


def remove_page_markers(text: str) -> str:
    """Remove os marcadores __PB__ após o uso."""
    return text.replace("__PB__\n", "").replace("\n__PB__", "")


# 2. cabeçalhos

# Padrão genérico de ID — cobre dois formatos:
#   • Numérico puro:  5.1  8.34  6.1.1
#   • Letra-ponto:   A.1  B.3.31  A.1.2.2  (Anexos, ISO 27701 Annex B…)
_ID_RE = re.compile(
    r"(?m)^"
    r"([A-Z]\.\d+(?:\.\d+){0,3}"  # B.1.2.2, A.3.31, A.1 …
    r"|\d+\.\d+(?:\.\d+){0,2})"  # 5.1, 8.34, 6.1.1 …
    r"[ \t]+"
    r"([^\n]{3,100})"  # nome (resto da linha)
    r"(?:\n|$)"
)

# Padrão de bloco "Controle" isolado numa linha
_CTRL_MARKER = re.compile(r"\nControle\n")


def find_nearest_heading(text: str, pos: int) -> tuple[str, str] | tuple[None, None]:
    """
    Busca retroativamente o cabeçalho hierárquico mais recente
    antes da posição `pos`. Ignora números soltos (sem ponto).
    """
    chunk = text[max(0, pos - 800) : pos]
    # Remove marcadores de página antes de buscar
    chunk = chunk.replace("__PB__", "")
    matches = list(_ID_RE.finditer(chunk))
    if not matches:
        return None, None
    m = matches[-1]
    ctrl_id = m.group(1).strip()
    nome = re.sub(r"\s+", " ", m.group(2)).strip()
    # Descarta IDs sem ponto (números soltos como "28", "2022" etc.)
    if "." not in ctrl_id:
        return None, None
    return ctrl_id, nome


def extract_controle_block(text: str, marker_end: int) -> str:
    """
    Extrai o texto normativo logo após o marcador 'Controle',
    até o próximo marcador de seção conhecido.
    """
    STOP = re.compile(
        r"\n(?:Propósito|Orienta(?:ção|ções)"  # Orientação ou Orientações
        r"|Outras\s+informações?"
        r"|NOTA\b"
        r"|Tipo de controle"
        r"|\d+\s+Controles"
        r"|__PB__)"
    )
    end_match = STOP.search(text, marker_end)
    end = end_match.start() if end_match else marker_end + 600
    block = text[marker_end:end]
    block = block.replace("__PB__", "")
    return re.sub(r"\s+", " ", block).strip()


def extract_proposito(text: str, marker_end: int) -> str:
    """Extrai o Propósito se presente logo após a descrição."""
    m = re.search(
        r"\nPropósito\n(.*?)(?=\nOrientação|\nOutras\s*informações?|\n\d|\n[A-Z]\.|__PB__|\Z)",
        text[marker_end : marker_end + 1200],
        re.DOTALL,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1).replace("__PB__", "")).strip()
    return ""


# 3. inferencia de temas


def infer_theme_id(ctrl_id: str) -> str:
    """
    Tema = segmento pai do ID.
    5.1  → 5   |   8.34  → 8
    A.1.2.2 → A.1   |   B.3.10 → B.3
    """
    parts = ctrl_id.split(".")
    if parts[0].isdigit():
        return parts[0]  # 5, 6, 7, 8
    return f"{parts[0]}.{parts[1]}"  # A.1, B.3 …


def find_theme_names(text: str) -> dict[str, str]:
    """
    Detecta nomes de temas a partir de cabeçalhos de seção de nível
    superior encontrados no texto — sem qualquer conhecimento prévio
    da norma.

    Reconhece dois formatos de seção-pai:
      • Numérico simples:  "5 Controles organizacionais"
      • Letra-ponto:       "B.1 Orientações para controladores de DP"

    Ignora seções de nível folha (5.1, B.1.2, B.1.2.2…).
    """
    names: dict[str, str] = {}

    # Cabeçalhos de seção pai
    #   "5 Controles organizacionais"  → key="5"
    #   "B.1 Orientações..."           → key="B.1"
    sec_pat = re.compile(
        r"(?m)^"
        r"([A-Z]\.\d+|\d+)"  # "B.1" ou "5"
        r"\s+"
        r"([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ][^\n]{4,100})"
        r"(?:\n|$)"
    )
    for m in sec_pat.finditer(text):
        key = m.group(1).strip()
        name = re.sub(r"\s+", " ", m.group(2)).strip()
        # Remove artefato de índice remissivo: "Nome ....... 28" → "Nome"
        name = re.sub(r"\s*\.{3,}.*$", "", name).strip()
        # Só registra como tema se for "pai":
        #   "5"   → 0 pontos, dígito          → ✓
        #   "B.1" → 1 ponto, letra seguida de dígito → ✓
        #   "5.1" → 1 ponto, dígito-dígito    → ✗ (é controle, não tema)
        parts = key.split(".")
        is_parent = (len(parts) == 1 and parts[0].isdigit()) or (  # "5", "8"
            len(parts) == 2 and parts[0].isalpha()
        )  # "B.1", "A.3"
        if is_parent and key not in names:
            names[key] = name

    # Cabeçalhos de tabela: "Tabela A.1 – … para XYZ"
    tbl_pat = re.compile(r"(?m)Tabela\s+([A-Z]\.\d+)\s+[–—-]+\s*([^\n]{5,100})")
    for m in tbl_pat.finditer(text):
        key = m.group(1).strip()
        name = re.sub(r"\s+", " ", m.group(2)).strip()
        if key not in names:
            names[key] = name

    return names


# 4. core pipeline


def extract(pdf_path: str) -> list[dict]:
    print(f"[*] Lendo {pdf_path}")

    # 4.1 Texto bruto por página
    pages = extract_pages(pdf_path)
    print(f"    {len(pages)} páginas")

    # 4.2 Detecção e remoção de boilerplate (cabeçalhos/rodapés)
    boiler = detect_boilerplate(pages)
    print(f"    {len(boiler)} linhas de boilerplate detectadas e removidas")

    # 4.3 Texto limpo (com marcadores de quebra de página)
    text_with_pb = clean_pages(pages, boiler)

    # 4.4 Nomes de temas (antes de remover PB para contexto de página)
    text_clean = remove_page_markers(text_with_pb)
    theme_names = find_theme_names(text_clean)
    print(f"    {len(theme_names)} temas detectados: {list(theme_names)[:8]}")

    # 4.5 Localiza todos os marcadores "Controle"
    markers = list(_CTRL_MARKER.finditer(text_with_pb))
    print(f"    {len(markers)} marcadores 'Controle' encontrados")

    if not markers:
        print(
            "    AVISO: nenhum marcador encontrado — verifique se o PDF "
            "segue o padrão ABNT com 'Controle' em linha própria."
        )
        return []

    # 4.6 Para cada marcador: heading + bloco de texto
    controles: list[dict] = []
    seen_ids: set[str] = set()

    for m in markers:
        marker_end = m.end()  # posição após "\nControle\n"

        ctrl_id, nome = find_nearest_heading(text_with_pb, m.start())
        if ctrl_id is None:
            continue
        if ctrl_id in seen_ids:
            continue
        seen_ids.add(ctrl_id)

        descricao = extract_controle_block(text_with_pb, marker_end)
        proposito = extract_proposito(text_with_pb, marker_end)

        if not descricao:
            continue

        tema_id = infer_theme_id(ctrl_id)
        tema_nome = theme_names.get(tema_id, tema_id)

        entry: dict = {
            "id": ctrl_id,
            "tema": tema_id,
            "tema_nome": tema_nome,
            "nome": nome,
            "descricao": descricao,
        }
        if proposito:
            entry["proposito"] = proposito

        controles.append(entry)

    # 4.7 Ordena por ID (numericamente quando possível)
    def sort_key(c: dict):
        parts = re.split(r"[.\-]", c["id"])
        key = []
        for p in parts:
            try:
                key.append((0, int(p)))
            except:
                key.append((1, p))
        return key

    controles.sort(key=sort_key)
    return controles


# 5. relatório e saída na cli


def report(controles: list[dict]):
    sep = "=" * 55
    print(f"\n{sep}")
    print(f" {len(controles)} controles extraídos")
    print(sep)

    by_tema = Counter(c["tema_nome"] for c in controles)
    for tema, n in sorted(by_tema.items(), key=lambda x: -x[1]):
        print(f"  {tema:<45} {n:>3}")

    sem_desc = [c["id"] for c in controles if not c.get("descricao")]
    if sem_desc:
        print(f"\n  ⚠  Sem descrição ({len(sem_desc)}): {', '.join(sem_desc[:8])}")
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    pdf_path = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "controles.json"

    if not Path(pdf_path).exists():
        sys.exit(f"Arquivo não encontrado: {pdf_path}")

    controles = extract(pdf_path)
    report(controles)

    if not controles:
        sys.exit("Nenhum controle extraído.")

    Path(output).parent.mkdir(parents=True, exist_ok=True)
    with open(output, "w", encoding="utf-8") as f:
        json.dump(controles, f, ensure_ascii=False, indent=2)

    print(f"✓ Salvo em: {output}")
    print("\nAmostra (primeiros 3 registros):")
    for c in controles[:3]:
        print(json.dumps(c, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
