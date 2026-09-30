"""Mensuração de campanha: incrementalidade (grupo de controle) x atribuição (last-touch).

As regras de negócio vivem nos arquivos SQL (`sql/`), escritos para rodar com
poucas adaptações em Impala/Hive. O Python só orquestra, faz a estatística
e monta o relatório.
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass
from importlib import resources
from typing import Any


def sql(nome: str) -> str:
    return resources.files("mensuracao").joinpath("sql", nome).read_text(encoding="utf-8").strip().rstrip(";")


def _rows(conn: sqlite3.Connection, query: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    cur = conn.execute(query, params or {})
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


# ---------------------------------------------------------------- estatística

def _norm_cdf(x: float) -> float:
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


Z_95, Z_80 = 1.959964, 0.841621


def efeito_minimo_detectavel(n_tratamento: int, n_controle: int, taxa_base: float) -> float:
    """MDE absoluto para teste bicaudal com alfa 5% e poder 80%."""
    var = taxa_base * (1 - taxa_base) * (1 / n_tratamento + 1 / n_controle)
    return (Z_95 + Z_80) * math.sqrt(var)


def holdout_necessario(n_total: int, taxa_base: float, efeito: float) -> float | None:
    """Menor fração de controle (1% a 50%) que detecta `efeito` com poder 80%, ou None se nenhuma detecta."""
    for pct in range(1, 51):
        n_c = round(n_total * pct / 100)
        if efeito_minimo_detectavel(n_total - n_c, n_c, taxa_base) <= efeito:
            return pct / 100
    return None


@dataclass(frozen=True)
class Lift:
    n_tratamento: int
    conv_tratamento: int
    n_controle: int
    conv_controle: int

    @property
    def taxa_tratamento(self) -> float:
        return self.conv_tratamento / self.n_tratamento

    @property
    def taxa_controle(self) -> float:
        return self.conv_controle / self.n_controle

    @property
    def lift_abs(self) -> float:
        """Diferença em pontos percentuais (fração)."""
        return self.taxa_tratamento - self.taxa_controle

    @property
    def lift_rel(self) -> float:
        return self.lift_abs / self.taxa_controle if self.taxa_controle else float("inf")

    @property
    def erro_padrao(self) -> float:
        """Erro padrão da diferença (Wald, variância não agrupada) — o mesmo no teste e no IC."""
        pt, pc = self.taxa_tratamento, self.taxa_controle
        return math.sqrt(pt * (1 - pt) / self.n_tratamento + pc * (1 - pc) / self.n_controle)

    @property
    def z(self) -> float:
        """Estatística z para H0: sem efeito."""
        return self.lift_abs / self.erro_padrao if self.erro_padrao else 0.0

    @property
    def p_valor(self) -> float:
        return 2 * (1 - _norm_cdf(abs(self.z)))

    @property
    def ic95(self) -> tuple[float, float]:
        """Intervalo de 95% para a diferença."""
        return self.lift_abs - Z_95 * self.erro_padrao, self.lift_abs + Z_95 * self.erro_padrao

    @property
    def significativo(self) -> bool:
        return self.p_valor < 0.05

    @property
    def mde(self) -> float:
        """Menor efeito detectável com este desenho (alfa 5%, poder 80%)."""
        return efeito_minimo_detectavel(self.n_tratamento, self.n_controle, self.taxa_controle)

    @property
    def conversoes_incrementais(self) -> float:
        """Quantas conversões do tratamento não teriam acontecido sem a campanha."""
        return self.lift_abs * self.n_tratamento


# ---------------------------------------------------------------- consultas

def medir_lift(conn: sqlite3.Connection, campanha_id: int = 1, janela: int = 30) -> Lift:
    grupos = {r["grupo"]: r for r in _rows(conn, sql("01_lift_grupo_controle.sql"),
                                           {"campanha_id": campanha_id, "janela": janela})}
    t, c = grupos["tratamento"], grupos["controle"]
    return Lift(t["clientes"], t["conversoes"], c["clientes"], c["conversoes"])


def atribuir_last_touch(conn: sqlite3.Connection, dt_inicio: str, dt_fim: str, lookback: int = 30) -> list[dict[str, Any]]:
    """Materializa a atribuição em `temp.last_touch` e devolve o resumo por canal."""
    conn.execute("DROP TABLE IF EXISTS temp.last_touch")
    conn.execute(f"CREATE TEMP TABLE last_touch AS {sql('02_atribuicao_last_touch.sql')}",
                 {"dt_inicio": dt_inicio, "dt_fim": dt_fim, "lookback": lookback})
    return _rows(conn, sql("03_last_touch_por_canal.sql"))


def curva_acumulada(conn: sqlite3.Connection, campanha_id: int = 1, dias: int = 30) -> list[dict[str, Any]]:
    return _rows(conn, sql("04_curva_acumulada.sql"), {"campanha_id": campanha_id, "dias": dias})


# ---------------------------------------------------------------- saída

def grafico_svg(curva: list[dict[str, Any]], largura: int = 640, altura: int = 300) -> str:
    """Gráfico de linhas simples, sem dependências, com as duas curvas acumuladas."""
    m = {"esq": 56, "dir": 110, "topo": 20, "base": 36}
    series: dict[str, list[tuple[int, float]]] = {}
    for r in curva:
        series.setdefault(r["grupo"], []).append((r["dia"], r["taxa_acumulada"]))
    max_dia = max(d for s in series.values() for d, _ in s) or 1
    max_taxa = max(t for s in series.values() for _, t in s) or 1
    max_taxa = math.ceil(max_taxa * 100) / 100
    w, h = largura - m["esq"] - m["dir"], altura - m["topo"] - m["base"]

    def xy(d: int, t: float) -> tuple[float, float]:
        return m["esq"] + w * d / max_dia, m["topo"] + h * (1 - t / max_taxa)

    cores = {"tratamento": "#2563eb", "controle": "#9ca3af"}
    partes = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {largura} {altura}" font-family="sans-serif" font-size="11">',
        f'<rect width="{largura}" height="{altura}" fill="#ffffff"/>',
    ]
    for i in range(5):
        t = max_taxa * i / 4
        _, y = xy(0, t)
        partes.append(f'<line x1="{m["esq"]}" x2="{m["esq"] + w}" y1="{y:.1f}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        partes.append(f'<text x="{m["esq"] - 8}" y="{y + 4:.1f}" text-anchor="end" fill="#6b7280">{t:.1%}</text>')
    for d in range(0, max_dia + 1, 5):
        x, _ = xy(d, 0)
        partes.append(f'<text x="{x:.1f}" y="{altura - 14}" text-anchor="middle" fill="#6b7280">{d}</text>')
    partes.append(f'<text x="{m["esq"] + w / 2}" y="{altura - 1}" text-anchor="middle" fill="#374151">dias desde o início da campanha</text>')
    for grupo, pts in series.items():
        cor = cores.get(grupo, "#111827")
        caminho = " ".join(f"{x:.1f},{y:.1f}" for x, y in (xy(d, t) for d, t in pts))
        partes.append(f'<polyline points="{caminho}" fill="none" stroke="{cor}" stroke-width="2.5"/>')
        x, y = xy(*pts[-1])
        partes.append(f'<text x="{x + 8:.1f}" y="{y + 4:.1f}" fill="{cor}" font-weight="bold">{grupo} {pts[-1][1]:.2%}</text>')
    partes.append("</svg>")
    return "\n".join(partes)


def relatorio(lift: Lift, canais: list[dict[str, Any]], nome_campanha: str) -> str:
    crm = next((c for c in canais if c["canal"] == "crm"), {"conversoes": 0})
    n_total = lift.n_tratamento + lift.n_controle
    n_c_pct = lift.n_controle / n_total
    efeito_alvo = 0.01
    holdout = holdout_necessario(n_total, lift.taxa_controle, efeito_alvo)
    lo, hi = lift.ic95
    incrementais = lift.conversoes_incrementais
    fator = crm["conversoes"] / incrementais if incrementais > 0 else float("inf")
    linhas = [
        f"# Relatório de mensuração: {nome_campanha}",
        "",
        "## 1. Incrementalidade (tratamento x grupo de controle)",
        "",
        "| Grupo | Clientes | Conversões | Taxa |",
        "|---|---:|---:|---:|",
        f"| Tratamento | {lift.n_tratamento:,} | {lift.conv_tratamento:,} | {lift.taxa_tratamento:.2%} |",
        f"| Controle | {lift.n_controle:,} | {lift.conv_controle:,} | {lift.taxa_controle:.2%} |",
        "",
        f"- **Lift absoluto:** {lift.lift_abs * 100:+.2f} p.p. (IC 95%: {lo * 100:+.2f} a {hi * 100:+.2f} p.p.)",
        f"- **Lift relativo:** {lift.lift_rel:+.1%}",
        f"- **Significância:** z = {lift.z:.2f}, p-valor = {lift.p_valor:.4f} "
        f"({'significativo' if lift.significativo else 'não significativo'} a 5%)",
        f"- **Conversões incrementais estimadas:** {incrementais:,.0f}",
        f"- **Poder do desenho:** com {n_c_pct:.0%} de holdout, o menor efeito detectável (poder 80%) é "
        f"**{lift.mde * 100:.2f} p.p.**" + (
            f"; para detectar {efeito_alvo * 100:.1f} p.p. o holdout precisaria ser de **{holdout:.0%}**."
            if holdout else "."),
        "",
        "![Curva de conversão acumulada](curva_acumulada.svg)",
        "",
        "## 2. Atribuição last-touch (lookback 30 dias)",
        "",
        "| Canal | Conversões atribuídas | % do total |",
        "|---|---:|---:|",
        *[f"| {c['canal']} | {c['conversoes']:,} | {c['pct_total']:.1f}% |" for c in canais],
        "",
        "## 3. Leitura",
        "",
        f"O last-touch credita **{crm['conversoes']:,} conversões ao CRM**. O grupo de controle estima "
        f"**~{incrementais:,.0f} conversões incrementais** (IC 95%: {max(lo, 0) * lift.n_tratamento:,.0f} a "
        f"{hi * lift.n_tratamento:,.0f}). Mesmo no limite superior do intervalo, o last-touch superestima o CRM em "
        f"**{crm['conversoes'] / (hi * lift.n_tratamento):.1f}x** (na estimativa pontual, {fator:.1f}x). "
        "O CRM toca todo o público, inclusive quem já ia converter, e fica com o crédito da última interação.",
        "",
        *([] if lift.significativo else [
            f"O teste de incrementalidade é **inconclusivo a 5%**. Isso *não* é evidência de que a campanha não "
            f"funciona: com este holdout o desenho só detecta efeitos a partir de {lift.mde * 100:.2f} p.p. "
            "É um problema de desenho, e se resolve antes do disparo.",
            "",
        ]),
        "**Recomendação:** usar last-touch para *distribuir* crédito operacional entre canais e usar grupo de controle "
        "para *decidir investimento*. Toda campanha nova da régua deve nascer com holdout **dimensionado antes do "
        "disparo** para o menor efeito que justificaria o custo da campanha.",
    ]
    return "\n".join(linhas) + "\n"
