"""Saídas para quem olha a empresa: painel.json (site e app Android) e briefing.md (agente)."""
from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

from . import armazem, calendario, config

COLUNAS_HISTORICO = ["data", "cota", "bench", "pl", "fluxo", "retorno_dia", "divida_tecnica", "incidentes_abertos",
                     "credibilidade", "confianca_media", "caixa_gestora", *[f"peso_{a}" for a in config.ATIVOS]]


def registrar_historico(registro: dict, caminho: Path | None = None) -> None:
    caminho = caminho or (config.DADOS / "historico.csv")
    linhas = ler_historico(caminho)
    r = registro["resumo"]
    nova = {"data": registro["data"], "cota": r["cota"], "bench": r["bench"], "pl": r["pl"], "fluxo": r["fluxo"],
            "retorno_dia": r["retorno_dia"], "divida_tecnica": r["divida_tecnica"],
            "incidentes_abertos": r["incidentes_abertos"], "credibilidade": r["credibilidade"],
            "confianca_media": r["confianca_media"], "caixa_gestora": r["caixa_gestora"],
            **{f"peso_{a}": w for a, w in r["pesos"].items()}}
    linhas = [ln for ln in linhas if ln["data"] != registro["data"]] + [nova]
    linhas.sort(key=lambda ln: ln["data"])
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_HISTORICO, lineterminator="\n")
        w.writeheader()
        w.writerows(linhas)


def ler_historico(caminho: Path | None = None) -> list[dict]:
    caminho = caminho or (config.DADOS / "historico.csv")
    if not caminho.exists():
        return []
    with caminho.open(encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    for ln in linhas:
        for k in COLUNAS_HISTORICO[1:]:
            ln[k] = float(ln[k])
    return linhas


def _ret(hist: list[dict], campo: str, n: int) -> float | None:
    if len(hist) < 2:
        return None
    base = hist[max(0, len(hist) - 1 - n)][campo]
    return hist[-1][campo] / base - 1


def montar_painel(estado: dict, dias: list[dict], historico: list[dict], controle: dict | None,
                  processos: dict | None, politicas: dict) -> dict:
    """Um único JSON com tudo o que o site e o app mostram."""
    d = date.fromisoformat(estado["ultima_data"])
    fundo, ex, db, exe = estado["fundo"], estado["extracao"], estado["dashboards"], estado["executivos"]
    total = sum(p["valor"] for p in fundo["posicoes"].values()) or 1
    abertos = [i for i in estado["incidentes"] if i["estado"] == "aberto"]
    disponibilidade = []
    for reg in dias[-20:]:
        por_fonte = {f: "ok" for f in config.FONTES}
        for inc in reg.get("incidentes_do_dia", []):
            por_fonte[inc["fonte"]] = inc["tipo"]
        disponibilidade.append({"data": reg["data"], "fontes": por_fonte})
    issues = (processos or {}).get("issues", {})
    return {
        "empresa": config.NOME, "fundo": config.FUNDO, "aviso": config.AVISO,
        "data_referencia": d.isoformat(),
        "proximo_dia_util": calendario.proximo_dia_util(d).isoformat(),
        "gerado_em": (controle or {}).get("executado_em"),
        "resumo": {
            "cota": round(fundo["cota"], 6), "pl": fundo["pl"], "retorno_dia": fundo.get("retorno_dia", 0),
            "retorno_mes": _ret(historico, "cota", 21), "cdi_mes": _ret(historico, "bench", 21),
            "retorno_total": fundo["cota"] - 1, "cdi_total": fundo["bench"] - 1, "fluxo_dia": fundo["fluxo_dia"],
            "incidentes_abertos": len(abertos), "credibilidade": db["credibilidade"],
            "confianca_media": db.get("confianca_media"), "divida_tecnica": ex["divida_tecnica"],
            "caixa_gestora": estado["gestora"]["caixa"], "alertas": len(estado["alertas"]),
        },
        "extracao": {
            "divida_tecnica": ex["divida_tecnica"], "equipe": ex["equipe"], "orcamento_dia": ex["orcamento_dia"],
            "fontes": [{
                "id": f, "nome": meta["nome"], "series": meta["series"],
                "real": (controle or {}).get("fontes", {}).get(f, {}).get("status", "?"),
                "erro_real": (controle or {}).get("fontes", {}).get(f, {}).get("erro"),
                "liberado_ate": ex["fontes"][f]["liberado_ate"],
                "alternativa_ligada": ex["fontes"][f]["alternativa_ligada"],
                "incidente": next((i["id"] for i in abertos if i["fonte"] == f), None),
            } for f, meta in config.FONTES.items()],
            "incidentes": [{k: i[k] for k in ("id", "fonte", "tipo", "aberto_em", "estado", "dias", "acao", "detalhe",
                                              "resolvido_em", "historico")} | {"issue": issues.get(i["id"])}
                           for i in sorted(estado["incidentes"], key=lambda i: i["id"], reverse=True)],
            "disponibilidade": disponibilidade,
        },
        "dashboards": {
            "credibilidade": db["credibilidade"], "confianca_media": db.get("confianca_media"),
            "indicadores": [{"id": k, **v} for k, v in db["indicadores"].items()],
            "estimativas_pendentes": db["estimativas"],
            "estrategia_padrao": politicas["dashboards"]["estrategia_padrao"],
        },
        "executivos": {
            "alvo": exe["alvo"], "pesos": {a: p["valor"] / total for a, p in fundo["posicoes"].items()},
            "limites": politicas["fundo"]["limites"], "congelados": exe.get("congelados", []),
            "dias_sem_decisao": exe["dias_sem_decisao"], "ultima_decisao": exe["ultima_decisao"],
            "decisoes_recentes": list(reversed(exe["decisoes_recentes"])),
            "gestora": estado["gestora"],
        },
        "alertas": [{"chave": k, **{c: a.get(c) for c in ("titulo", "area", "sev", "aberto_em", "detalhe")},
                     "issue": issues.get(k)} for k, a in sorted(estado["alertas"].items())],
        "dias": [{"data": r["data"], "eventos": r["eventos"], "decisao": r["decisao"]} for r in reversed(dias[-15:])],
        "historico": [{k: ln[k] for k in ("data", "cota", "bench", "pl", "fluxo", "divida_tecnica", "credibilidade",
                                         "confianca_media", "incidentes_abertos", "caixa_gestora")}
                      | {"pesos": {a: ln[f"peso_{a}"] for a in config.ATIVOS}} for ln in historico],
        "nomes": {"ativos": config.ATIVOS, "acoes_extracao": config.ACOES_EXTRACAO,
                  "estrategias": config.ESTRATEGIAS_DASHBOARD, "tipos_incidente": config.TIPOS_INCIDENTE},
        "processos": {"issues_abertas": (processos or {}).get("abertas", []),
                      "repositorio": "GloedenJoao/profissional"},
    }


def briefing(painel: dict) -> str:
    """Resumo curto para o agente decidir o próximo dia útil sem precisar calcular nada."""
    r, ex, db, exe = painel["resumo"], painel["extracao"], painel["dashboards"], painel["executivos"]
    pct = lambda v: "—" if v is None else f"{v:+.2%}"  # noqa: E731
    linhas = [
        f"# Briefing · fechamento de {painel['data_referencia']}",
        "",
        f"Próxima decisão: `empresa/decisoes/{painel['proximo_dia_util']}.json` (aplicada no fechamento desse dia).",
        "",
        "## Fundo",
        f"- Cota {r['cota']:.6f} · PL R$ {r['pl']:,.0f} · dia {pct(r['retorno_dia'])} · 21d {pct(r['retorno_mes'])} "
        f"vs CDI {pct(r['cdi_mes'])} · desde o início {pct(r['retorno_total'])} vs CDI {pct(r['cdi_total'])}",
        f"- Fluxo de cotistas no dia: R$ {r['fluxo_dia']:,.0f} · caixa da gestora R$ {r['caixa_gestora']:,.0f}",
        "- Alocação (atual → alvo): " + ", ".join(
            f"{a} {exe['pesos'][a]:.1%}→{exe['alvo'][a]:.0%}" for a in exe["alvo"]),
        f"- Limites: " + ", ".join(f"{a} {mn:.0%}–{mx:.0%}" for a, (mn, mx) in exe["limites"].items()),
    ]
    if exe["congelados"]:
        linhas.append(f"- Congelados (sem número confiável): {', '.join(exe['congelados'])}")
    linhas += ["", "## Extração",
               f"- Dívida técnica {ex['divida_tecnica']:.1f}/100 · equipe {ex['equipe']} · orçamento R$ {ex['orcamento_dia']:,.0f}/dia"]
    abertos = [i for i in ex["incidentes"] if i["estado"] == "aberto"]
    if not abertos:
        linhas.append("- Nenhum incidente aberto.")
    for i in abertos:
        linhas.append(f"- **{i['id']}** {i['fonte']} `{i['tipo']}` há {i['dias']} dia(s), ação `{i['acao']}` — {i['detalhe']}")
    falhas = [f for f in ex["fontes"] if f["real"] == "erro"]
    for f in falhas:
        linhas.append(f"- ⚠️ Falha REAL no conector `{f['id']}`: {f['erro_real']} (corrigir em `gestora/fontes.py`)")
    linhas += ["", "## Dashboards", f"- Credibilidade {db['credibilidade']:.0%} · confiança média {db['confianca_media']:.0%}",
               "", "| indicador | valor | ref | defasagem | estratégia | confiança |", "|---|---|---|---|---|---|"]
    for i in db["indicadores"]:
        linhas.append(f"| {i['id']} | {i['valor'] if i['valor'] is not None else '—'} | {i['data_ref']} | "
                      f"{i['defasagem']} | {i['estrategia'] or '—'} | {i['confianca']:.0%} |")
    linhas += ["", "## Alertas ativos"]
    linhas += [f"- [{a['sev']}] {a['chave']} — {a['titulo']}" for a in painel["alertas"]] or ["- nenhum"]
    linhas += ["", "## Últimos eventos"]
    eventos = [f"- {dia['data']} · {e['area']} · {e['texto']}" for dia in painel["dias"][:5] for e in dia["eventos"]]
    linhas += eventos[:12] or ["- nenhum nos últimos 5 dias úteis"]
    conselho = [i for i in painel["processos"]["issues_abertas"] if "conselho" in i["rotulos"]]
    if conselho:
        linhas += ["", "## Diretrizes do conselho (issues `conselho`)"]
        linhas += [f"- #{i['numero']} {i['titulo']} — {i['url']}" for i in conselho]
    return "\n".join(linhas) + "\n"


def gravar_saidas(painel: dict) -> None:
    armazem.gravar_json(config.DADOS / "painel.json", painel)
    (config.DADOS / "briefing.md").write_text(briefing(painel), encoding="utf-8")
