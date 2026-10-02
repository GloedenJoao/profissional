"""Saídas para quem olha a empresa: painel.json (site e app Android) e briefing.md (conselho)."""
from __future__ import annotations

import csv
import json
import urllib.parse
from datetime import date
from pathlib import Path

from . import armazem, calendario, config

COLUNAS_HISTORICO = ["data", "cota", "bench", "cota_ref", "pl", "fluxo", "retorno_dia", "divida_tecnica",
                     "incidentes_abertos", "credibilidade", "confianca_media", "caixa_gestora", "equipe", "orcamento_dia",
                     "verificacoes_ok", "verificacoes_total", *[f"peso_{a}" for a in config.ATIVOS],
                     *[f"alvo_{a}" for a in config.ATIVOS]]


def registrar_historico(registro: dict, caminho: Path | None = None) -> None:
    caminho = caminho or (config.DADOS / "historico.csv")
    linhas = ler_historico(caminho)
    r = registro["resumo"]
    nova = {"data": registro["data"], **{k: r.get(k) for k in COLUNAS_HISTORICO[1:16]},
            **{f"peso_{a}": w for a, w in r["pesos"].items()},
            **{f"alvo_{a}": w for a, w in (r.get("alvo") or {}).items()}}
    nova["fluxo"] = r["fluxo"]
    nova = {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in nova.items()}  # mesmo formato ao reler
    linhas = [ln for ln in linhas if ln["data"] != registro["data"]] + [nova]
    linhas.sort(key=lambda ln: ln["data"])
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS_HISTORICO, lineterminator="\n", extrasaction="ignore")
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
            v = ln.get(k)
            ln[k] = float(v) if v not in (None, "") else None
    return linhas


def resumo_dos_dias(pasta: Path | None = None) -> dict:
    """Uma passada por todos os dias simulados: calendário (status de cada etapa) e totais das verificações."""
    pasta = pasta or config.DIAS
    calendario_, por_check = [], {}
    for arq in sorted(pasta.glob("*.json")):
        reg = armazem.ler_json(arq)
        r = reg.get("resumo", {})
        mudou = bool((reg.get("decisoes") or {}).get("executivos", {}).get("alocacao"))
        calendario_.append({"data": reg["data"], "n": reg.get("dia_numero"), "status": r.get("status", {}),
                            "retorno": r.get("retorno_dia"), "cota": r.get("cota"), "cota_ref": r.get("cota_ref"),
                            "verif": [r.get("verificacoes_ok"), r.get("verificacoes_total")],
                            "incidentes": r.get("incidentes_abertos"), "alocacao": mudou,
                            "conselho": bool((reg.get("decisao") or {}).get("intervencao")),
                            "eventos": len(reg.get("eventos", []))})
        for c in reg.get("verificacoes", []):
            agg = por_check.setdefault(c["id"], {"id": c["id"], "nome": c["nome"], "ok": 0, "falhas": 0, "ultima_falha": None})
            if c["ok"]:
                agg["ok"] += 1
            else:
                agg["falhas"] += 1
                agg["ultima_falha"] = {"data": reg["data"], "detalhe": c["detalhe"]}
    return {"calendario": calendario_, "verificacoes": list(por_check.values())}


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
    cen = config.cenario()
    proximo = calendario.proximo_dia_util(d)
    return {
        "empresa": config.NOME, "fundo": config.FUNDO, "aviso": config.AVISO,
        "cenario": {k: cen.get(k) for k in ("id", "nome", "descricao", "modo")} | {"inicio": estado["inicio"]},
        "data_referencia": d.isoformat(),
        "proximo_dia_util": proximo.isoformat(),
        # o fechamento do próximo dia útil roda na manhã do dia útil seguinte (só vale para o ao vivo)
        "proximo_fechamento_em": calendario.proximo_dia_util(proximo).isoformat() if cen["modo"] == "diario" else None,
        "feriados": sorted(f.isoformat() for ano in range(date.fromisoformat(estado["inicio"]).year, d.year + 2)
                           for f in calendario.feriados(ano)),
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
            "incidentes": [{k: i.get(k) for k in ("id", "fonte", "tipo", "aberto_em", "estado", "dias", "acao", "detalhe",
                                                  "resolvido_em", "historico", "origem")} | {"issue": issues.get(i["id"])}
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
        # a reunião do último dia (o site toca as outras a partir de dias/AAAA-MM-DD.json)
        "ata": (dias[-1].get("ata") or []) if dias else [],
        "datas": [ln["data"] for ln in historico],
        "historico": [{k: ln[k] for k in ("data", "cota", "bench", "cota_ref", "pl", "fluxo", "divida_tecnica",
                                         "credibilidade", "confianca_media", "incidentes_abertos", "caixa_gestora",
                                         "equipe", "orcamento_dia")}
                      | {"pesos": {a: ln[f"peso_{a}"] for a in config.ATIVOS},
                         "alvo": {a: ln.get(f"alvo_{a}") for a in config.ATIVOS}} for ln in historico],
        "versao_motor": estado.get("versao", 1),
        "produto": "experimento" if cen["modo"] == "diario" else "simulacao",
        "fundacao": estado.get("fundacao"),
        "referencia": {"cota": estado.get("referencia", {}).get("cota"),
                       "valor_decisoes": (fundo["cota"] / estado["referencia"]["cota"] - 1) if estado.get("referencia") else None},
        "metricas": estado.get("metricas"),
        "series": {s: {"nome": config.SERIES_INFO[s][0], "unidade": config.SERIES_INFO[s][1],
                       "publicacao": config.REGRA_PUBLICACAO[config.PUBLICACAO[s]],
                       "fonte": next(f for f, m in config.FONTES.items() if s in m["series"])} for s in config.PUBLICACAO},
        "nomes": {"ativos": config.ATIVOS, "acoes_extracao": config.ACOES_EXTRACAO,
                  "estrategias": config.ESTRATEGIAS_DASHBOARD, "tipos_incidente": config.TIPOS_INCIDENTE},
        "processos": {"issues_abertas": (processos or {}).get("abertas", []),
                      "controle": (processos or {}).get("controle"),
                      "repositorio": config.REPO},
    }


# ====================================================================== status e tarefas
def _br(iso: str | None) -> str:
    return "—" if not iso else "/".join(reversed(iso[:10].split("-")))


def _pct_br(v: float) -> str:
    return f"{v:+.2%}".replace(".", ",")


def _alertas_com_prefixo(painel: dict, *prefixos: str) -> list[dict]:
    return [a for a in painel["alertas"] if a["chave"].startswith(prefixos)]


def status_areas(painel: dict, politicas: dict) -> dict:
    """Semáforo de cada área (ok / aviso / ruim) com uma frase curta: o que a Central mostra primeiro."""
    r, ex, db, exe = painel["resumo"], painel["extracao"], painel["dashboards"], painel["executivos"]
    abertos = [i for i in ex["incidentes"] if i["estado"] == "aberto"]
    graves = [i for i in abertos if i["tipo"] in ("falha_real", "mudanca_formato") or i["dias"] >= 3]
    if graves:
        st_ex = ("ruim", f"{len(abertos)} incidente(s) aberto(s), {len(graves)} grave(s)")
    elif abertos:
        st_ex = ("aviso", f"{len(abertos)} incidente(s) aberto(s): " + ", ".join(i["fonte"] for i in abertos))
    elif ex["divida_tecnica"] > 60:
        st_ex = ("aviso", f"todas as fontes no ar, mas dívida técnica em {ex['divida_tecnica']:.0f}/100")
    else:
        st_ex = ("ok", f"todas as fontes no ar · dívida técnica {ex['divida_tecnica']:.0f}/100")

    suspensos = [i["id"] for i in db["indicadores"] if i["valor"] is None]
    defasados = [i["id"] for i in db["indicadores"] if i["defasagem"] > 0]
    if suspensos or db["credibilidade"] < 0.6:
        st_db = ("ruim", f"credibilidade {db['credibilidade']:.0%}" + (f" · sem número: {', '.join(suspensos)}" if suspensos else ""))
    elif defasados or db["credibilidade"] < 0.8:
        st_db = ("aviso", f"credibilidade {db['credibilidade']:.0%}" + (f" · defasados: {', '.join(defasados)}" if defasados else ""))
    else:
        st_db = ("ok", f"todos os números em dia · credibilidade {db['credibilidade']:.0%}")

    if _alertas_com_prefixo(painel, "DESENQ-", "CRISE-CAIXA"):
        st_exe = ("ruim", "; ".join(a["titulo"] for a in _alertas_com_prefixo(painel, "DESENQ-", "CRISE-CAIXA")))
    elif exe["dias_sem_decisao"] >= 3 or exe["congelados"]:  # dias sem decisão só acontece sem os times
        partes = []
        if exe["dias_sem_decisao"] >= 3:
            partes.append(f"{exe['dias_sem_decisao']} dias sem decisão")
        if exe["congelados"]:
            partes.append("congelados: " + ", ".join(exe["congelados"]))
        st_exe = ("aviso", " · ".join(partes))
    else:
        st_exe = ("ok", f"último ajuste do comitê em {_br(exe['ultima_decisao'])}" if exe["ultima_decisao"]
                  else "comitê mantém a alocação inicial")

    vs = "—" if r["retorno_mes"] is None else f"21d {_pct_br(r['retorno_mes'])} vs CDI {_pct_br(r['cdi_mes'])}"
    if _alertas_com_prefixo(painel, "RESGATE-"):
        st_fu = ("ruim", f"resgate relevante · {vs}")
    elif r["retorno_mes"] is not None and r["retorno_mes"] < r["cdi_mes"]:
        st_fu = ("aviso", f"abaixo do CDI · {vs}")
    else:
        st_fu = ("ok", vs)
    return {area: {"nivel": n, "texto": t} for area, (n, t) in
            {"extracao": st_ex, "dashboards": st_db, "executivos": st_exe, "fundo": st_fu}.items()}


def modelo_decisao(painel: dict, politicas: dict) -> dict:
    """Diretriz do conselho para o próximo dia, já preenchida com o que vale hoje: é só editar e salvar.
    Os times decidem sozinhos; o que estiver aqui vale por cima da decisão deles (apague o que não quiser impor)."""
    ex, db, exe = painel["extracao"], painel["dashboards"], painel["executivos"]
    dec: dict = {"data": painel["proximo_dia_util"], "autor": "conselho"}
    acoes = {i["id"]: i["acao"] for i in ex["incidentes"] if i["estado"] == "aberto"}
    if acoes:
        dec["extracao"] = {"acoes": acoes}
    estrategias = {i["id"]: i["estrategia"] for i in db["indicadores"] if i["defasagem"] > 0 and i["estrategia"]}
    if estrategias:
        dec["dashboards"] = {"estrategias": estrategias}
    dec["executivos"] = {"alocacao": {a: round(w, 4) for a, w in exe["alvo"].items()},
                         "equipe_extracao": ex["equipe"], "orcamento_extracao_dia": ex["orcamento_dia"],
                         "justificativa": ""}
    dec["observacoes"] = ""
    return dec


def _link_novo_arquivo(pasta: str, nome: str, conteudo: str) -> str:
    q = urllib.parse.urlencode({"filename": nome, "value": conteudo}, quote_via=urllib.parse.quote)
    return f"https://github.com/{config.REPO}/new/main/{pasta}?{q}"


def decisao_proxima(painel: dict, politicas: dict) -> dict:
    pasta = config.caminho_repo(config.DECISOES)
    nome = f"{painel['proximo_dia_util']}.json"
    modelo = modelo_decisao(painel, politicas)
    return {
        "data": painel["proximo_dia_util"], "caminho": f"{pasta}/{nome}",
        "existe": (config.DECISOES / nome).exists(), "modelo": modelo,
        "link_criar": _link_novo_arquivo(pasta, nome, json.dumps(modelo, ensure_ascii=False, indent=2) + "\n"),
        "link_ver": f"https://github.com/{config.REPO}/blob/main/{pasta}/{nome}",
        "link_pasta": f"https://github.com/{config.REPO}/tree/main/{pasta}",
    }


ORDEM_NIVEL = {"ruim": 0, "aviso": 1, "info": 2}


def tarefas(painel: dict) -> list[dict]:
    """O que alguém precisa fazer agora, com o link que leva direto ao lugar de fazer."""
    repo = f"https://github.com/{config.REPO}"
    dec = painel["decisao_proxima"]
    manual = painel["cenario"]["modo"] != "diario"
    out = []
    if dec["existe"]:
        out.append({"id": "DIRETRIZ", "area": "executivos", "nivel": "info",
                    "titulo": f"Diretriz do conselho para {_br(dec['data'])} registrada",
                    "detalhe": f"{dec['caminho']} vale por cima da decisão dos times no próximo "
                               f"{'avanço' if manual else 'fechamento'}.", "link": dec["link_ver"], "acao": "Ver"})
    for f in painel["extracao"]["fontes"]:
        if f["real"] == "erro":
            out.append({"id": f"CONECTOR-{f['id']}", "area": "extracao", "nivel": "ruim",
                        "titulo": f"Conector {f['nome']} falhou de verdade", "detalhe": f["erro_real"] or "",
                        "link": f"{repo}/blob/main/gestora/fontes.py", "acao": "Corrigir conector"})
    for a in painel["alertas"]:
        sev = {"alta": "ruim", "media": "aviso", "baixa": "info"}.get(a["sev"], "info")
        acao = "Ver alerta"
        link = (a.get("issue") or {}).get("url")
        out.append({"id": a["chave"], "area": a["area"], "nivel": sev, "titulo": a["titulo"],
                    "detalhe": a.get("detalhe") or "", "link": link or f"{repo}/issues", "acao": acao,
                    "issue": a.get("issue")})
    for i in painel["processos"]["issues_abertas"]:
        if "conselho" in i["rotulos"]:
            out.append({"id": f"CONSELHO-{i['numero']}", "area": "executivos", "nivel": "aviso",
                        "titulo": f"Diretriz do conselho #{i['numero']}: {i['titulo']}", "detalhe": "",
                        "link": i["url"], "acao": "Responder"})
    out.sort(key=lambda t: ORDEM_NIVEL[t["nivel"]])
    return out


def briefing(painel: dict) -> str:
    """Resumo curto do último dia, com as decisões dos times, para quem acompanha (ou quer intervir)."""
    r, ex, db, exe = painel["resumo"], painel["extracao"], painel["dashboards"], painel["executivos"]
    pct = lambda v: "—" if v is None else f"{v:+.2%}"  # noqa: E731
    cen = painel.get("cenario") or {}
    titulo = "" if cen.get("id", config.CENARIO_PADRAO) == config.CENARIO_PADRAO else f" · cenário {cen['nome']}"
    caminho = (painel.get("decisao_proxima") or {}).get("caminho") or f"empresa/decisoes/{painel['proximo_dia_util']}.json"
    linhas = [
        f"# Briefing · fechamento de {painel['data_referencia']}{titulo}",
        "",
        f"Os times decidem sozinhos. Diretriz do conselho (opcional): `{caminho}` vale por cima deles nesse dia.",
        "",
        "## Fundo",
        f"- Cota {r['cota']:.6f} · PL R$ {r['pl']:,.0f} · dia {pct(r['retorno_dia'])} · 21d {pct(r['retorno_mes'])} "
        f"vs CDI {pct(r['cdi_mes'])} · desde o início {pct(r['retorno_total'])} vs CDI {pct(r['cdi_total'])}",
        f"- Fluxo de cotistas no dia: R$ {r['fluxo_dia']:,.0f} · caixa da gestora R$ {r['caixa_gestora']:,.0f}",
        f"- Carteira de referência (sem o comitê): {(painel.get('referencia') or {}).get('cota') or 0:.6f} · valor das "
        f"decisões {pct((painel.get('referencia') or {}).get('valor_decisoes'))}",
        f"- Verificações do motor: {(painel.get('metricas') or {}).get('verificacoes_ok', 0)} ok, "
        f"{(painel.get('metricas') or {}).get('verificacoes_falha', 0)} falha(s) desde a fundação",
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
    decididas = [f"- {f['hora']} · {f['quem']} ({f['papel']}): {f['texto']}" for f in painel.get("ata", [])
                 if f["tipo"] in ("decisao", "conselho")]
    linhas += ["", "## Decisões dos times no último dia"] + (decididas or ["- nenhuma mudança: os times mantiveram tudo"])
    linhas += ["", "## Últimos eventos"]
    eventos = [f"- {dia['data']} · {e['area']} · {e['texto']}" for dia in painel["dias"][:5] for e in dia["eventos"]]
    linhas += eventos[:12] or ["- nenhum nos últimos 5 dias úteis"]
    conselho = [i for i in painel["processos"]["issues_abertas"] if "conselho" in i["rotulos"]]
    if conselho:
        linhas += ["", "## Diretrizes do conselho (issues `conselho`)"]
        linhas += [f"- #{i['numero']} {i['titulo']} — {i['url']}" for i in conselho]
    return "\n".join(linhas) + "\n"


def completar(painel: dict, politicas: dict) -> dict:
    from . import regras  # import tardio: regras importa simulacao
    painel.update(resumo_dos_dias())
    painel["regras"] = regras.descrever(politicas)
    painel["status_areas"] = status_areas(painel, politicas)
    painel["decisao_proxima"] = decisao_proxima(painel, politicas)
    painel["tarefas"] = tarefas(painel)
    return painel


def gravar_saidas(painel: dict) -> None:
    armazem.gravar_json(config.DADOS / "painel.json", painel)
    (config.DADOS / "briefing.md").write_text(briefing(painel), encoding="utf-8")
