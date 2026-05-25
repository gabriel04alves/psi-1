"""
Populate de dados falsos para testes da aplicação PSI.

Cria:
  - 3 empresas de setores distintos
  - 2 normas: ISO 27002:2022 (93 controles) e ISO 27701:2019 (78 controles)
    carregadas de data/27002_2026.json e data/27701_2026.json
  - Múltiplas auditorias por empresa em datas distintas, simulando
    evolução de conformidade ao longo do tempo

Uso:
  python utils/populate.py           # insere sem apagar dados existentes
  python utils/populate.py --reset   # limpa o banco e recria tudo
"""

import argparse
import json
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db import get_connection, init_db

ROOT = Path(__file__).parent.parent
RNG = random.Random(42)

# ── Normas (JSONs) ────────────────────────────────────────────────────────────
def _carregar_json(caminho: Path) -> list[dict]:
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)

CONTROLES_27002 = _carregar_json(ROOT / "data" / "27002_2026.json")
CONTROLES_27701 = _carregar_json(ROOT / "data" / "27701_2026.json")

NORMAS_DEF = [
    {
        "nome": "ISO 27002",
        "versao": "2022",
        "controles": CONTROLES_27002,
    },
    {
        "nome": "ISO 27701",
        "versao": "2019",
        "controles": CONTROLES_27701,
    },
]

# ── Empresas ──────────────────────────────────────────────────────────────────
EMPRESAS = [
    {
        "nome": "TechCorp Soluções Ltda.",
        "cnpj": "12.345.678/0001-99",
        "razao_social": "TechCorp Soluções em Tecnologia Ltda.",
        "setor": "Tecnologia da Informação",
        "porte": "Médio",
        "responsavel": "João Silva (CISO)",
    },
    {
        "nome": "Saúde Digital S.A.",
        "cnpj": "98.765.432/0001-11",
        "razao_social": "Saúde Digital Sistemas Hospitalares S.A.",
        "setor": "Saúde",
        "porte": "Grande",
        "responsavel": "Ana Oliveira (DPO)",
    },
    {
        "nome": "Fintech Pagamentos Ltda.",
        "cnpj": "55.444.333/0001-22",
        "razao_social": "Fintech Soluções em Pagamentos Digitais Ltda.",
        "setor": "Financeiro",
        "porte": "Pequeno",
        "responsavel": "Carlos Mendes (CTO)",
    },
]

# ── Auditorias por empresa ────────────────────────────────────────────────────
# Cada entrada: (norma_nome, data_inicio, data_fim|None, maturidade_inicial, maturidade_final)
# maturidade: 0.0–1.0 — % alvo aproximado de conformidade nessa auditoria

_D = datetime(2025, 5, 24)  # data de referência

PLANO_AUDITORIAS = {
    "TechCorp Soluções Ltda.": [
        # ISO 27002 — 3 rodadas com evolução clara
        ("ISO 27002", _D - timedelta(days=540), _D - timedelta(days=480), 0.30),
        ("ISO 27002", _D - timedelta(days=360), _D - timedelta(days=300), 0.52),
        ("ISO 27002", _D - timedelta(days=150), _D - timedelta(days=90),  0.71),
        # ISO 27701 — em andamento, parcialmente respondido (~75%)
        ("ISO 27701", _D - timedelta(days=60),  None,                    0.48),
    ],
    "Saúde Digital S.A.": [
        # ISO 27002 — 2 rodadas (empresa mais madura na 1ª)
        ("ISO 27002", _D - timedelta(days=480), _D - timedelta(days=420), 0.45),
        ("ISO 27002", _D - timedelta(days=240), _D - timedelta(days=180), 0.68),
        # ISO 27701 — concluída (setor de saúde, foco em privacidade)
        ("ISO 27701", _D - timedelta(days=300), _D - timedelta(days=240), 0.62),
        # 2ª rodada ISO 27701
        ("ISO 27701", _D - timedelta(days=120), _D - timedelta(days=60),  0.78),
    ],
    "Fintech Pagamentos Ltda.": [
        # ISO 27002 — 1 rodada concluída (empresa pequena, baixa maturidade)
        ("ISO 27002", _D - timedelta(days=300), _D - timedelta(days=240), 0.38),
        # ISO 27701 — em andamento, 50% respondido
        ("ISO 27701", _D - timedelta(days=90),  None,                    0.29),
    ],
}

# ── Observações de exemplo ────────────────────────────────────────────────────
_OBS = {
    "conforme": [
        "Implementado e operacional conforme o requisito.",
        "Documentação revisada e aprovada pela direção.",
        "Controle auditado; evidências coletadas e arquivadas.",
        "Processo formalizado e comunicado a todos os colaboradores.",
        "Ferramenta implementada e monitorada continuamente.",
        "Política publicada e reconhecida pelo pessoal relevante.",
    ],
    "nao_conforme": [
        "Política ainda não formalmente aprovada pela direção.",
        "Processo identificado mas não documentado.",
        "Controle inexistente — implantação necessária.",
        "Evidências insuficientes para comprovação.",
        "Responsável não designado para este controle.",
        "Implementação iniciada mas incompleta.",
        "Treinamento não realizado para este tema.",
    ],
    "em_andamento": [
        "Em implementação — previsão de conclusão no próximo trimestre.",
        "Projeto aprovado; execução iniciada.",
        "Revisão da política em andamento com equipe jurídica.",
        "Ferramenta em fase de homologação.",
        "Treinamento da equipe agendado.",
        "Procedimento rascunhado; aguardando aprovação.",
    ],
}

def _obs(status: str) -> str:
    pool = _OBS.get(status, [])
    if not pool:
        return ""
    return RNG.choice(pool) if RNG.random() < 0.75 else ""


# ── Geração de respostas ──────────────────────────────────────────────────────

def _gerar_respostas(controles: list[dict], alvo: float) -> dict[str, str]:
    """
    Gera {controle_id: status} com conformidade aproximada = alvo.
    Distribui os controles não-conformes entre nao_conforme/em_andamento/nao_se_aplica.
    """
    opcoes = ["conforme", "nao_conforme", "em_andamento", "nao_se_aplica"]

    nsa_frac  = 0.07                       # ~7% não se aplica
    conf_frac = alvo * (1 - nsa_frac)      # conformes sobre aplicáveis
    nc_frac   = (1 - alvo) * 0.55 * (1 - nsa_frac)
    ea_frac   = (1 - alvo) * 0.45 * (1 - nsa_frac)

    pesos = [conf_frac, nc_frac, ea_frac, nsa_frac]

    resultado: dict[str, str] = {}
    for c in controles:
        resultado[c["id"]] = RNG.choices(opcoes, weights=pesos)[0]
    return resultado


def _evoluir(anterior: dict[str, str], controles: list[dict], alvo: float) -> dict[str, str]:
    """
    Evolui respostas da rodada anterior em direção a `alvo`,
    com raras regressões para tornar o comparativo mais realista.
    """
    novo: dict[str, str] = {}
    progressao ={"nao_conforme": "em_andamento", "em_andamento": "conforme", "conforme": "conforme"}
    regressao  = {"conforme": "em_andamento", "em_andamento": "nao_conforme", "nao_conforme": "nao_conforme"}

    # Estima conformidade atual e ajusta probabilidade de melhora
    conf_atual = sum(1 for s in anterior.values() if s == "conforme")
    aplic_atual = sum(1 for s in anterior.values() if s != "nao_se_aplica")
    pct_atual = conf_atual / aplic_atual if aplic_atual else 0
    gap = max(0, alvo - pct_atual)
    p_melhora = min(0.70, 0.25 + gap * 1.5)
    p_piora   = 0.04

    for c in controles:
        s = anterior.get(c["id"], "nao_conforme")
        if s == "nao_se_aplica":
            novo[c["id"]] = "nao_se_aplica"
            continue
        r = RNG.random()
        if r < p_melhora:
            novo[c["id"]] = progressao[s]
        elif r < p_melhora + p_piora:
            novo[c["id"]] = regressao[s]
        else:
            novo[c["id"]] = s
    return novo


# ── Operações no banco ────────────────────────────────────────────────────────

def _reset(conn):
    conn.executescript("""
        DELETE FROM respostas;
        DELETE FROM auditorias;
        DELETE FROM controles_norma;
        DELETE FROM normas;
        DELETE FROM empresa;
    """)
    conn.commit()
    print("Banco limpo.")


def _inserir_norma(conn, nome: str, versao: str, controles: list[dict]) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        "INSERT INTO normas (nome, versao, origem, data_ingestao) VALUES (?, ?, 'importado', ?)",
        (nome, versao, now),
    )
    norma_id = cur.lastrowid
    for c in controles:
        conn.execute(
            """INSERT INTO controles_norma
               (norma_id, controle_id, tema_id, tema_nome, nome, descricao)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (norma_id, c["id"], c["tema"], c.get("tema_nome", ""), c["nome"], c.get("descricao", "")),
        )
    conn.commit()
    return norma_id


def _inserir_empresa(conn, dados: dict) -> int:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.execute(
        """INSERT INTO empresa (nome, cnpj, razao_social, setor, porte, responsavel, atualizado_em)
           VALUES (:nome, :cnpj, :razao_social, :setor, :porte, :responsavel, :atualizado_em)""",
        {**dados, "atualizado_em": now},
    )
    conn.commit()
    return cur.lastrowid


def _inserir_auditoria(
    conn,
    empresa_id: int,
    norma_id: int,
    controles: list[dict],
    data_inicio: datetime,
    data_fim: datetime | None,
    respostas: dict[str, str],
    cobertura: float = 1.0,   # fração de controles respondidos (para auditorias em andamento)
) -> int:
    fmt = "%Y-%m-%d %H:%M:%S"
    status = "concluida" if data_fim else "em_andamento"
    cur = conn.execute(
        "INSERT INTO auditorias (empresa_id, norma_id, data_inicio, data_fim, status) VALUES (?, ?, ?, ?, ?)",
        (empresa_id, norma_id, data_inicio.strftime(fmt), data_fim.strftime(fmt) if data_fim else None, status),
    )
    aud_id = cur.lastrowid

    # Para auditorias em andamento, responde apenas `cobertura` % dos controles
    cids = [c["id"] for c in controles]
    if cobertura < 1.0:
        k = max(1, int(len(cids) * cobertura))
        cids_resp = set(RNG.sample(cids, k=k))
    else:
        cids_resp = set(cids)

    for c in controles:
        if c["id"] not in cids_resp:
            continue
        s = respostas.get(c["id"], "nao_conforme")
        conn.execute(
            "INSERT INTO respostas (auditoria_id, controle_id, tema_id, status, observacao)"
            " VALUES (?, ?, ?, ?, ?)",
            (aud_id, c["id"], c["tema"], s, _obs(s)),
        )
    conn.commit()
    return aud_id


def _pct(respostas: dict[str, str]) -> float:
    aplic = [s for s in respostas.values() if s != "nao_se_aplica"]
    if not aplic:
        return 0.0
    return round(sum(1 for s in aplic if s == "conforme") / len(aplic) * 100, 1)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Limpa o banco antes de inserir.")
    args = parser.parse_args()

    init_db()
    conn = get_connection()

    if args.reset:
        _reset(conn)

    # ── Normas ────────────────────────────────────────────────────────────────
    norma_ids: dict[str, int] = {}
    for n in NORMAS_DEF:
        nid = _inserir_norma(conn, n["nome"], n["versao"], n["controles"])
        norma_ids[n["nome"]] = nid
        print(f"Norma: {n['nome']} {n['versao']} → id={nid} ({len(n['controles'])} controles)")

    # Mapa norma_nome → controles
    ctrl_map = {n["nome"]: n["controles"] for n in NORMAS_DEF}

    print()

    # ── Empresas e auditorias ─────────────────────────────────────────────────
    for emp_dados in EMPRESAS:
        emp_id = _inserir_empresa(conn, emp_dados)
        print(f"Empresa: {emp_dados['nome']} (id={emp_id})")

        plano = PLANO_AUDITORIAS[emp_dados["nome"]]

        # Agrupa auditorias por norma para calcular evolução encadeada
        historico: dict[str, dict[str, str]] = {}  # norma_nome → respostas anteriores

        for norma_nome, d_inicio, d_fim, alvo in plano:
            controles = ctrl_map[norma_nome]
            norma_id  = norma_ids[norma_nome]

            # Gera respostas (primeira vez ou evoluindo da anterior)
            if norma_nome not in historico:
                resps = _gerar_respostas(controles, alvo)
            else:
                resps = _evoluir(historico[norma_nome], controles, alvo)

            historico[norma_nome] = resps

            # Auditorias em andamento têm cobertura parcial
            cobertura = RNG.uniform(0.50, 0.78) if d_fim is None else 1.0

            aud_id = _inserir_auditoria(
                conn, emp_id, norma_id, controles,
                d_inicio, d_fim, resps, cobertura,
            )

            n_resp = int(len(controles) * cobertura) if d_fim is None else len(controles)
            status_txt = "em andamento" if d_fim is None else "concluída"
            print(
                f"  #{aud_id} {norma_nome} | {d_inicio.strftime('%Y-%m-%d')} → "
                f"{'—' if d_fim is None else d_fim.strftime('%Y-%m-%d')} | "
                f"{status_txt} | {_pct(resps)}% conf. | {n_resp}/{len(controles)} ctrl"
            )

        print()

    conn.close()
    print("Populate concluído.")
    print("Para testar: selecione qualquer empresa na página Empresas.")


if __name__ == "__main__":
    main()
