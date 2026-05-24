"""Funções de análise de conformidade reutilizadas pelas páginas de comparativo e relatórios."""

STATUS_LABEL = {
    "conforme": "Conforme",
    "nao_conforme": "Não Conforme",
    "em_andamento": "Em Andamento",
    "nao_se_aplica": "Não se Aplica",
}

STATUS_COR = {
    "conforme": "#22c55e",
    "nao_conforme": "#ef4444",
    "em_andamento": "#f59e0b",
    "nao_se_aplica": "#94a3b8",
}


def calcular_stats(respostas: list[dict]) -> dict:
    """
    Recebe a lista de respostas de uma auditoria e retorna estatísticas
    de conformidade geral e por tipo de controle (tema).

    Regra: 'nao_se_aplica' é excluído do denominador da conformidade.
    """
    aplicaveis = [r for r in respostas if r["status"] != "nao_se_aplica"]
    contagem: dict[str, int] = {}
    for r in respostas:
        contagem[r["status"]] = contagem.get(r["status"], 0) + 1

    conformes = contagem.get("conforme", 0)
    pct_geral = round(conformes / len(aplicaveis) * 100, 1) if aplicaveis else 0.0

    temas: dict[str, dict] = {}
    for r in respostas:
        tid = r["tema_id"]
        if tid not in temas:
            temas[tid] = {"nome": r["tema_nome"] or tid, "respostas": []}
        temas[tid]["respostas"].append(r)

    temas_stats = []
    for tid, data in sorted(temas.items()):
        t_resps = data["respostas"]
        t_ap = [r for r in t_resps if r["status"] != "nao_se_aplica"]
        t_conf = sum(1 for r in t_ap if r["status"] == "conforme")
        t_nc = sum(1 for r in t_ap if r["status"] == "nao_conforme")
        t_and = sum(1 for r in t_ap if r["status"] == "em_andamento")
        pct = round(t_conf / len(t_ap) * 100, 1) if t_ap else 0.0
        temas_stats.append({
            "id": tid,
            "nome": data["nome"],
            "total": len(t_resps),
            "aplicaveis": len(t_ap),
            "conformes": t_conf,
            "nao_conformes": t_nc,
            "em_andamento": t_and,
            "nao_se_aplica": len(t_resps) - len(t_ap),
            "pct": pct,
        })

    return {
        "pct_geral": pct_geral,
        "total": len(respostas),
        "aplicaveis": len(aplicaveis),
        "contagem": contagem,
        "temas": temas_stats,
    }


def label_auditoria(a: dict) -> str:
    data = a["data_fim"][:10] if a.get("data_fim") else a["data_inicio"][:10]
    return f"#{a['id']} — {a['empresa']} · {a['modulo']} · {data}"
