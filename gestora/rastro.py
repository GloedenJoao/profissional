"""O rastro do dia: cada etapa grava o que recebeu, a regra que aplicou, a conta que fez e o que entregou.

O rastro é a fonte da verdade do que aconteceu. As falas da reunião (a ata) são escritas a partir dele e
apontam para o bloco que as sustenta, então o site pode mostrar, ao lado de cada frase, as contas por trás.

Cada número carrega a sua origem:
- `real`: dado público, com fonte e data;
- `derivado`: conta feita só com dados reais;
- `simulado`: modelo da empresa fictícia (inclui os sorteios do teste de estresse, sempre com a chance e o número);
- `decisao`: escolha de um time, com a regra que a produziu;
- `conselho`: diretriz humana que vale por cima do time;
- `regra`: parâmetro de política (empresa/politicas.json) ou constante do motor.
"""
from __future__ import annotations

ORIGENS = ("real", "derivado", "simulado", "decisao", "conselho", "regra")

PESSOAS = {
    "extracao": [("Bia", "líder de Extração"), ("Téo", "engenheiro de dados")],
    "dashboards": [("Caio", "líder de Dashboards"), ("Lia", "analista de dados")],
    "executivos": [("Helena", "CEO"), ("Rafael", "CIO"), ("Marta", "Risco")],
    "fundo": [("Administrador", "administrador do fundo")],
    "conselho": [("Conselho", "diretriz")],
}


# ====================================================================== formatação (pt-BR)
def num(v: float | None, casas: int = 2) -> str:
    """1234.5 → '1.234,50'. Negativo com sinal de menos (−); zero arredondado nunca sai como '−0'."""
    if v is None:
        return "—"
    if round(v, casas) == 0:
        v = 0.0
    s = f"{abs(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("−" + s) if v < 0 else s


def pct(v: float | None, casas: int = 2, sinal: bool = False) -> str:
    """0,0123 → '1,23%' (com `sinal`, '+1,23%')."""
    if v is None:
        return "—"
    s = num(v * 100, casas) + "%"
    return ("+" + s) if sinal and not s.startswith("−") and s.strip("0,%") else s


def pp(v: float | None, casas: int = 1) -> str:
    """Diferença em pontos percentuais: 0,05 → '+5,0 p.p.'."""
    if v is None:
        return "—"
    s = num(v * 100, casas)
    return (s if s.startswith("−") or not s.strip("0,") else "+" + s) + " p.p."


def sinal(v: float, casas: int = 2) -> str:
    """Número com sinal explícito: 0,46 → '+0,46'."""
    s = num(v, casas)
    return s if s.startswith("−") or not s.strip("0,") else "+" + s


def brl(v: float | None, casas: int = 0) -> str:
    if v is None:
        return "—"
    return ("−" if round(v, casas) < 0 else "") + "R$ " + num(abs(v), casas)


def mi(v: float | None, casas: int = 1) -> str:
    if v is None:
        return "—"
    return ("−" if round(v / 1e6, casas) < 0 else "") + "R$ " + num(abs(v) / 1e6, casas) + " mi"


def mil(v: float | None, com_sinal: bool = False) -> str:
    if v is None:
        return "—"
    if abs(v) >= 1e6:
        s = mi(v, 2)
    else:
        s = ("−" if round(v / 1e3) < 0 else "") + "R$ " + num(abs(v) / 1e3, 0) + " mil"
    return ("+" + s) if com_sinal and not s.startswith("−") else s


def data(iso) -> str:
    """'2026-01-22' (ou date) → '22/01/2026'."""
    if not iso:
        return "—"
    a, m, d = str(iso)[:10].split("-")
    return f"{d}/{m}/{a}"


MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]


def mes(iso) -> str:
    """'2025-11-01' → 'nov/25' (séries mensais, como o IPCA)."""
    if not iso:
        return "—"
    s = str(iso)
    return f"{MESES[int(s[5:7]) - 1]}/{s[2:4]}"


def dm(iso) -> str:
    return data(iso)[:5] if iso else "—"


def n_(n: int, singular: str, plural: str | None = None) -> str:
    """Quantidade com a palavra no número certo: n_(1, "dia") → '1 dia'; n_(3, "pregão", "pregões") → '3 pregões'."""
    return f"{n} {singular if n == 1 else (plural or singular + 's')}"


def cel(v, origem: str | None = None, dica: str | None = None) -> dict | str:
    """Célula de tabela com origem (e dica opcional). Sem origem, vira texto simples."""
    if origem is None and dica is None:
        return v
    out = {"v": v}
    if origem:
        out["o"] = origem
    if dica:
        out["dica"] = dica
    return out


# ====================================================================== estrutura
class Etapa:
    def __init__(self, rastro: "Rastro", id_: str, area: str, hora: str, titulo: str, pergunta: str):
        self.rastro = rastro
        self.dados = {"id": id_, "area": area, "hora": hora, "titulo": titulo, "pergunta": pergunta,
                      "status": "ok", "resumo": "", "blocos": []}
        self._min = 0

    @property
    def id(self) -> str:
        return self.dados["id"]

    def _bloco(self, b: dict) -> str:
        b["id"] = f"{self.id}.{len(self.dados['blocos']) + 1}"
        self.dados["blocos"].append(b)
        return b["id"]

    def tabela(self, titulo: str, colunas: list[str], linhas: list[list], nota: str | None = None,
               origem: str | None = None) -> str:
        """`origem` é a origem padrão das células sem origem própria."""
        return self._bloco({"tipo": "tabela", "titulo": titulo, "colunas": colunas, "linhas": linhas,
                            "nota": nota, "origem": origem})

    def contas(self, titulo: str, linhas: list[dict], nota: str | None = None) -> str:
        """Linhas: {"rot": o que é, "expr": a conta com os números, "valor": resultado, "o": origem}."""
        return self._bloco({"tipo": "contas", "titulo": titulo, "linhas": linhas, "nota": nota})

    def regras(self, titulo: str, itens: list[str], nota: str | None = None) -> str:
        return self._bloco({"tipo": "regras", "titulo": titulo, "itens": itens, "nota": nota})

    def texto(self, titulo: str, texto: str) -> str:
        return self._bloco({"tipo": "texto", "titulo": titulo, "texto": texto})

    def status(self, nivel: str, resumo: str) -> None:
        self.dados["status"], self.dados["resumo"] = nivel, resumo

    def piora(self, nivel: str) -> None:
        ordem = {"ok": 0, "info": 1, "aviso": 2, "ruim": 3}
        if ordem[nivel] > ordem[self.dados["status"]]:
            self.dados["status"] = nivel

    def diz(self, pessoa: int, texto: str, tipo: str = "fala", bloco: str | None = None, area: str | None = None,
            minutos: int | None = None) -> None:
        """Uma fala da reunião desta etapa. Cada fala "leva" 2 minutos (ou `minutos` depois do início)."""
        area = area or self.dados["area"]
        nome, papel = PESSOAS[area][pessoa]
        self._fala(area, nome, papel, texto, tipo, bloco, minutos)

    def conselho(self, texto: str, autor: str | None = None, bloco: str | None = None) -> None:
        papel = f"diretriz de {autor}" if autor and autor != "conselho" else "diretriz"
        self._fala(self.dados["area"], "Conselho", papel, texto, "conselho", bloco, None)

    def _fala(self, area, nome, papel, texto, tipo, bloco, minutos) -> None:
        h, m = map(int, self.dados["hora"].split(":"))
        if minutos is not None:
            self._min = max(self._min, minutos)
        m += self._min
        self._min += 2
        self.rastro.falas.append({"hora": f"{h + m // 60:02d}:{m % 60:02d}", "area": area, "quem": nome,
                                  "papel": papel, "texto": texto, "tipo": tipo, "etapa": self.id, "bloco": bloco})


class Rastro:
    def __init__(self) -> None:
        self.etapas: list[Etapa] = []
        self.falas: list[dict] = []

    def etapa(self, id_: str, area: str, hora: str, titulo: str, pergunta: str) -> Etapa:
        e = Etapa(self, id_, area, hora, titulo, pergunta)
        self.etapas.append(e)
        return e

    def ata(self) -> list[dict]:
        return sorted(self.falas, key=lambda f: f["hora"])  # sort estável: dentro do mesmo minuto, a ordem de fala

    def json(self) -> list[dict]:
        return [e.dados for e in self.etapas]
