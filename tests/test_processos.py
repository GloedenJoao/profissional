from gestora import processos


class FakeGH:
    def __init__(self):
        self.issues, self.chamadas = [], []

    def req(self, metodo, caminho, corpo=None):
        self.chamadas.append((metodo, caminho))
        if caminho == "/labels":
            return None
        if metodo == "GET":
            estado = "open" if "state=open" in caminho else None
            rot = caminho.split("labels=")[1].split("&")[0]
            return [i for i in self.issues if (estado is None or i["state"] == estado)
                    and rot in [lb["name"] for lb in i["labels"]]] if "page=1" in caminho or estado else []
        if metodo == "POST" and caminho == "/issues":
            i = {"number": len(self.issues) + 1, "title": corpo["title"], "body": corpo["body"], "state": "open",
                 "labels": [{"name": n} for n in corpo["labels"]], "html_url": f"u/{len(self.issues) + 1}"}
            self.issues.append(i)
            return i
        if metodo == "PATCH":
            n = int(caminho.split("/")[2])
            self.issues[n - 1]["state"] = corpo["state"]
        return {}


def alerta(t="x"):
    return {"titulo": t, "area": "extracao", "sev": "alta", "aberto_em": "2026-09-30", "corpo": "c", "detalhe": "d1"}


def test_ciclo_completo():
    gh = FakeGH()
    r = processos.sincronizar(gh, {"INC-0001": alerta()}, "2026-09-30")
    assert r["issues"]["INC-0001"]["numero"] == 1 and len(r["abertas"]) == 1
    # mesmo alerta, mesmo detalhe: nada muda
    r = processos.sincronizar(gh, {"INC-0001": alerta()}, "2026-10-01", r)
    assert len(gh.issues) == 1 and r["log"] == []
    # alerta sumiu: issue fecha
    r = processos.sincronizar(gh, {}, "2026-10-02", r)
    assert gh.issues[0]["state"] == "closed"
    # voltou: reabre a mesma issue
    processos.sincronizar(gh, {"INC-0001": alerta()}, "2026-10-05", r)
    assert gh.issues[0]["state"] == "open" and len(gh.issues) == 1


def test_abertas_inclui_recem_criada_mesmo_se_listagem_atrasar():
    gh = FakeGH()
    original = gh.req
    gh.req = lambda m, c, b=None: [] if (m == "GET" and "state=open" in c) else original(m, c, b)
    r = processos.sincronizar(gh, {"INC-0001": alerta()}, "2026-09-30")
    assert [i["numero"] for i in r["abertas"]] == [1]


def test_limite_de_issues_novas():
    gh = FakeGH()
    r = processos.sincronizar(gh, {f"K{i}": alerta() for i in range(12)}, "2026-09-30")
    assert len(gh.issues) == processos.MAX_NOVAS
    assert any("limite" in ln for ln in r["log"])
