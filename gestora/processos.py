"""Processos da empresa no GitHub: cada alerta ativo é uma issue aberta, e vice-versa.

A sincronização é idempotente: cria o que falta, reabre o que foi fechado cedo demais, comenta
mudanças e fecha o que deixou de valer. A chave do alerta fica num comentário HTML no corpo.
"""
from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

CORES = {"simulacao": "5319e7", "area:extracao": "0e8a16", "area:dashboards": "1d76db", "area:executivos": "b60205",
         "area:fundo": "fbca04", "sev:alta": "d93f0b", "sev:media": "fbca04", "sev:baixa": "c2e0c6",
         "conselho": "000000", "dia": "bfdadc"}
MARCA = re.compile(r"<!-- chave:(\S+) -->")
MAX_NOVAS = 8


class GitHub:
    def __init__(self, repo: str, token: str):
        self.repo, self.token = repo, token

    def req(self, metodo: str, caminho: str, corpo: dict | None = None):
        url = caminho if caminho.startswith("http") else f"https://api.github.com/repos/{self.repo}{caminho}"
        dados = json.dumps(corpo).encode() if corpo is not None else None
        r = urllib.request.Request(url, data=dados, method=metodo, headers={
            "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "capivara-asset"})
        try:
            with urllib.request.urlopen(r, timeout=30) as resp:
                texto = resp.read()
                return json.loads(texto) if texto else None
        except urllib.error.HTTPError as e:
            if e.code == 422 and caminho == "/labels":
                return None  # rótulo já existe
            raise


def _issues_da_simulacao(gh) -> list[dict]:
    todas = []
    for pagina in range(1, 11):
        lote = gh.req("GET", f"/issues?labels=simulacao&state=all&per_page=100&page={pagina}")
        todas += [i for i in lote if "pull_request" not in i]
        if len(lote) < 100:
            break
    return todas


def sincronizar(gh, alertas: dict, data_ref: str, anterior: dict | None = None) -> dict:
    anterior = anterior or {}
    detalhes_ant = anterior.get("detalhes", {})
    for nome, cor in CORES.items():
        gh.req("POST", "/labels", {"name": nome, "color": cor})
    por_chave: dict[str, dict] = {}
    for issue in sorted(_issues_da_simulacao(gh), key=lambda i: i["number"]):
        m = MARCA.search(issue.get("body") or "")
        if m:
            por_chave[m.group(1)] = issue  # a mais recente vence
    criadas = 0
    log = []
    for chave, a in sorted(alertas.items(), key=lambda kv: (kv[1].get("sev") != "alta", kv[0])):
        issue = por_chave.get(chave)
        corpo = (f"{a.get('corpo', '')}\n\n---\nAberto pela simulação no fechamento de {a['aberto_em']}. "
                 f"A issue fecha sozinha quando o alerta deixar de valer.\n<!-- chave:{chave} -->")
        rotulos = ["simulacao", f"area:{a['area']}", f"sev:{a['sev']}"]
        if issue is None:
            if criadas >= MAX_NOVAS:
                log.append(f"limite de {MAX_NOVAS} issues novas: {chave} fica para amanhã")
                continue
            issue = gh.req("POST", "/issues", {"title": a["titulo"], "body": corpo, "labels": rotulos})
            por_chave[chave] = issue
            criadas += 1
            log.append(f"aberta #{issue['number']} {chave}")
        elif issue["state"] == "closed":
            gh.req("PATCH", f"/issues/{issue['number']}", {"state": "open"})
            gh.req("POST", f"/issues/{issue['number']}/comments",
                   {"body": f"Reaberta no fechamento de {data_ref}: o alerta continua ativo."})
            issue["state"] = "open"
            log.append(f"reaberta #{issue['number']} {chave}")
        elif a.get("detalhe") and a["detalhe"] != detalhes_ant.get(chave):
            gh.req("POST", f"/issues/{issue['number']}/comments",
                   {"body": f"Fechamento de {data_ref}: {a['detalhe']}."})
            log.append(f"comentada #{issue['number']} {chave}")
    for chave, issue in por_chave.items():
        if chave not in alertas and issue["state"] == "open":
            gh.req("POST", f"/issues/{issue['number']}/comments",
                   {"body": f"Resolvido no fechamento de {data_ref}. Fechando."})
            gh.req("PATCH", f"/issues/{issue['number']}", {"state": "closed", "state_reason": "completed"})
            issue["state"] = "closed"
            log.append(f"fechada #{issue['number']} {chave}")
    # a listagem da API demora a enxergar issues recém-criadas: as que acabamos de tocar entram direto
    abertas = [{"numero": i["number"], "titulo": i["title"], "url": i["html_url"],
                "rotulos": [lb["name"] if isinstance(lb, dict) else lb for lb in i.get("labels", [])],
                "criada_em": i.get("created_at")} for k, i in por_chave.items() if k in alertas and i["state"] == "open"]
    for rotulo in ("simulacao", "conselho"):
        for i in gh.req("GET", f"/issues?labels={rotulo}&state=open&per_page=50") or []:
            if "pull_request" not in i and all(x["numero"] != i["number"] for x in abertas):
                abertas.append({"numero": i["number"], "titulo": i["title"], "url": i["html_url"],
                                "rotulos": [lb["name"] for lb in i.get("labels", [])],
                                "criada_em": i.get("created_at")})
    return {
        "data_ref": data_ref,
        "issues": {k: {"numero": i["number"], "url": i["html_url"], "estado": i["state"]} for k, i in por_chave.items()
                   if k in alertas},
        "abertas": abertas,
        "detalhes": {k: a.get("detalhe") for k, a in alertas.items()},
        "log": log,
    }


def cliente_do_ambiente():
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if not token or not repo:
        return None
    return GitHub(repo, token)
