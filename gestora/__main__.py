"""Linha de comando: python -m gestora [--cenario ID] {fechamento,avancar,sincronizar,validar,painel,cenarios,site}."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import armazem, calendario, comandos, config, decisoes, extracao, painel, processos, simulacao
from .mercado import Mercado

BRT = timezone(timedelta(hours=-3))


def _hoje() -> date:
    return datetime.now(BRT).date()


def _dias_registrados(n: int = 20) -> list[dict]:
    arquivos = sorted(config.DIAS.glob("*.json"))[-n:]
    return [armazem.ler_json(a) for a in arquivos]


def gerar_painel(controle: dict | None = None) -> dict:
    estado = armazem.ler_json(config.DADOS / "estado.json")
    controle = controle or armazem.ler_json(config.DADOS / "controle.json")
    proc = armazem.ler_json(config.DADOS / "processos.json")
    politicas = armazem.ler_json(config.POLITICAS)
    p = painel.montar_painel(estado, _dias_registrados(), painel.ler_historico(), controle, proc, politicas)
    painel.completar(p, politicas)
    painel.gravar_saidas(p)
    return p


def fechamento(data_ref: date | None, inicio: date | None, extrair: bool = True, conectores=None) -> list[str]:
    ref = data_ref or calendario.dia_util_anterior(_hoje())
    if not calendario.dia_util(ref):
        ref = calendario.dia_util_anterior(ref)
    politicas = armazem.ler_json(config.POLITICAS)
    erros = decisoes.validar_politicas(politicas)
    if erros:
        raise SystemExit("políticas inválidas:\n" + "\n".join(erros))
    estado = armazem.ler_json(config.DADOS / "estado.json")
    if estado is None:
        inicio = inicio or calendario.dias_uteis_entre(ref - timedelta(days=60), ref)[-31]
        janela_ini = inicio - timedelta(days=15)
    else:
        janela_ini = date.fromisoformat(estado["ultima_data"]) - timedelta(days=12)
    controle = None
    if extrair:
        controle = extracao.extrair(janela_ini, ref, conectores)
        extracao.registrar_historico(controle)
        armazem.gravar_json(config.DADOS / "controle.json", controle)
        for f, r in controle["fontes"].items():
            print(f"extração {f}: {r['status']} {r['linhas_novas']} linhas novas {r['erro'] or ''}")
    mercado = Mercado()
    if estado is None:
        estado = simulacao.estado_inicial(inicio, politicas, mercado)
        print(f"empresa fundada em {inicio}")
    feitos = []
    for d in calendario.dias_uteis_entre(date.fromisoformat(estado["ultima_data"]), ref):
        dec = decisoes.carregar_decisao(d)
        if dec:
            problemas = decisoes.validar_decisao(dec, politicas, f"{d}.json")
            if problemas:
                print("decisão inválida ignorada:\n  " + "\n  ".join(problemas))
                dec = None
        estado, reg = simulacao.simular_dia(estado, d, mercado, politicas, dec, controle if d == ref else None)
        armazem.gravar_json(config.DIAS / f"{d}.json", reg)
        painel.registrar_historico(reg)
        feitos.append(d.isoformat())
        r = reg["resumo"]
        print(f"{d}: cota {r['cota']:.6f} PL {r['pl']:,.0f} incidentes {r['incidentes_abertos']} "
              f"credibilidade {r['credibilidade']:.0%} decisão={'sim' if dec else 'não'}")
    armazem.gravar_json(config.DADOS / "estado.json", estado)
    gerar_painel(controle)
    return feitos


# Avanço em blocos: a janela de extração de cada bloco cabe nos 30 pregões que o conector da B3 baixa.
PASSO_AVANCO = 15


def avancar(dias: int | None = None, ate: date | None = None, extrair: bool = True, conectores=None,
            hoje: date | None = None) -> list[str]:
    """Cenário manual: avança a simulação N dias úteis (ou até a data), sem nunca passar de ontem."""
    cen = config.cenario()
    estado = armazem.ler_json(config.DADOS / "estado.json")
    inicio = date.fromisoformat(cen["inicio"]) if cen.get("inicio") else None
    if estado is None and inicio is None:
        raise SystemExit(f"cenário {cen['id']} sem estado e sem `inicio` em cenario.json")
    base = date.fromisoformat(estado["ultima_data"]) if estado else inicio
    limite = calendario.dia_util_anterior(hoje or _hoje())
    destino = comandos.alvo(base, dias, ate, limite, calendario.proximo_dia_util)
    pendentes = calendario.dias_uteis_entre(base, destino)
    if not pendentes:
        print(f"{cen['id']}: nada a avançar (último dia simulado {base}, limite {limite})")
        return []
    feitos = []
    for i in range(0, len(pendentes), PASSO_AVANCO):
        bloco = pendentes[i:i + PASSO_AVANCO]
        feitos += fechamento(bloco[-1], inicio, extrair=extrair, conectores=conectores)
    return feitos


def resumo_avanco(feitos: list[str]) -> str:
    """Markdown curto do que aconteceu nos dias avançados (vai como comentário na issue de controle)."""
    p = armazem.ler_json(config.DADOS / "painel.json")
    cen = p["cenario"]
    if not feitos:
        return f"**{cen['nome']}**: nada a avançar. Último dia simulado: {p['data_referencia']}.\n"
    r = p["resumo"]
    pct = lambda v: "—" if v is None else f"{v:+.2%}"  # noqa: E731
    linhas = [f"### {cen['nome']}: {feitos[0]} → {feitos[-1]} ({len(feitos)} dia(s) útil(eis))", "",
              f"- Cota **{r['cota']:.6f}** · PL R$ {r['pl']:,.0f} · desde o início {pct(r['retorno_total'])} "
              f"vs CDI {pct(r['cdi_total'])}",
              f"- Incidentes abertos: {r['incidentes_abertos']} · credibilidade {r['credibilidade']:.0%} · "
              f"caixa da gestora R$ {r['caixa_gestora']:,.0f}", ""]
    st = p["status_areas"]
    icone = {"ok": "🟢", "aviso": "🟡", "ruim": "🔴"}
    linhas += [f"{icone[v['nivel']]} **{simulacao.AREAS[a]}**: {v['texto']}  " for a, v in st.items()] + [""]
    eventos = []
    for d in feitos:
        reg = armazem.ler_json(config.DIAS / f"{d}.json") or {}
        eventos += [f"- {d} · {simulacao.AREAS.get(e['area'], e['area'])} · {e['texto']}" for e in reg.get("eventos", [])
                    if e["tipo"] != "info"]
    if eventos:
        linhas += ["<details><summary>O que aconteceu</summary>", "", *eventos[-20:], "", "</details>", ""]
    dec = p["decisao_proxima"]
    linhas.append(f"**Próximo:** decisão de {dec['data']} → [escrever]({dec['link_criar']}) · "
                  f"[painel](https://{config.REPO.split('/')[0].lower()}.github.io/{config.REPO.split('/')[1]}/#/{cen['id']})")
    return "\n".join(linhas) + "\n"


def sincronizar() -> None:
    gh = processos.cliente_do_ambiente()
    if gh is None:
        print("sem GITHUB_TOKEN/GITHUB_REPOSITORY: sincronização de issues pulada")
        return
    cen = config.cenario()
    estado = armazem.ler_json(config.DADOS / "estado.json")
    anterior = armazem.ler_json(config.DADOS / "processos.json")
    paralelo = None if cen["id"] == config.CENARIO_PADRAO else cen["id"]
    if cen.get("issues", True):
        resultado = processos.sincronizar(gh, estado["alertas"], estado["ultima_data"], anterior, paralelo)
    else:
        resultado = {"data_ref": estado["ultima_data"], "issues": {}, "abertas": [], "detalhes": {}, "log": []}
    if paralelo:
        resultado["controle"] = processos.garantir_controle(gh, cen)
    armazem.gravar_json(config.DADOS / "processos.json", resultado)
    print("\n".join(resultado["log"]) or "issues já estavam em dia")
    gerar_painel()


def montar_site(destino: Path) -> list[dict]:
    """Site estático: páginas de site/, o painel do ao vivo na raiz (o app Android lê de lá) e um painel
    por cenário em cenarios/<id>/painel.json, listados em cenarios.json."""
    if destino.exists():
        shutil.rmtree(destino)
    shutil.copytree(config.RAIZ / "site", destino)
    indice = []
    for c in config.listar_cenarios():
        origem = config.RAIZ / c["dados"] / "painel.json"
        rel = "painel.json" if c["id"] == config.CENARIO_PADRAO else f"cenarios/{c['id']}/painel.json"
        if origem.exists():
            (destino / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(origem, destino / rel)
        indice.append({k: c.get(k) for k in ("id", "nome", "descricao", "modo", "inicio")}
                      | {"painel": rel if origem.exists() else None})
    armazem.gravar_json(destino / "cenarios.json", {"repositorio": config.REPO, "cenarios": indice})
    return indice


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gestora")
    ap.add_argument("--cenario", help=f"cenário (padrão: {config.CENARIO_PADRAO}); veja `cenarios`")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fechamento", help="extrai dados e simula os dias úteis pendentes")
    f.add_argument("--data", type=date.fromisoformat, help="data de referência (padrão: dia útil anterior a hoje)")
    f.add_argument("--proximo", action="store_true", help="simula só o próximo dia útil depois do último (ensaio da CI)")
    f.add_argument("--inicio", type=date.fromisoformat, help="fundação da empresa, se ainda não existe estado")
    f.add_argument("--sem-extracao", action="store_true", help="usa só os dados já gravados")
    av = sub.add_parser("avancar", help="cenário manual: avança N dias úteis (ou até uma data)")
    av.add_argument("--dias", type=int, help="quantos dias úteis avançar (padrão 1)")
    av.add_argument("--ate", type=date.fromisoformat, help="avança até esta data (no máximo ontem)")
    av.add_argument("--comando", help="texto de um comentário `/avancar ...` (issue de controle)")
    av.add_argument("--resumo", type=Path, help="grava aqui o resumo em Markdown do avanço")
    av.add_argument("--sem-extracao", action="store_true", help="usa só os dados já gravados")
    sub.add_parser("sincronizar", help="espelha os alertas em issues do GitHub")
    sub.add_parser("validar", help="valida políticas e decisões pendentes (de todos os cenários, sem --cenario)")
    sub.add_parser("painel", help="regera painel.json e briefing.md")
    ce = sub.add_parser("cenarios", help="lista os cenários")
    ce.add_argument("--ids", action="store_true", help="só os ids, um por linha")
    si = sub.add_parser("site", help="monta o site estático com os painéis de todos os cenários")
    si.add_argument("destino", type=Path, nargs="?", default=Path("_site"))
    a = ap.parse_args(argv)
    if a.cenario:
        config.usar_cenario(a.cenario)
    if a.cmd == "fechamento":
        ref = a.data
        if a.proximo:
            estado = armazem.ler_json(config.DADOS / "estado.json")
            if estado is None:
                print(f"{config.CENARIO}: ainda sem estado, nada a ensaiar")
                return 0
            ref = calendario.proximo_dia_util(date.fromisoformat(estado["ultima_data"]))
        fechamento(ref, a.inicio, extrair=not a.sem_extracao)
    elif a.cmd == "avancar":
        dias, ate = a.dias, a.ate
        if a.comando:
            try:
                pedido = comandos.interpretar(a.comando)
            except ValueError as e:
                if a.resumo:
                    a.resumo.write_text(f"Não entendi o comando: {e}.\n", encoding="utf-8")
                print(f"comando inválido: {e}")
                return 2
            dias, ate = pedido.get("dias"), date.fromisoformat(pedido["ate"]) if "ate" in pedido else None
        feitos = avancar(dias, ate, extrair=not a.sem_extracao)
        if a.resumo:
            a.resumo.write_text(resumo_avanco(feitos), encoding="utf-8")
    elif a.cmd == "sincronizar":
        sincronizar()
    elif a.cmd == "validar":
        ids = [a.cenario] if a.cenario else [c["id"] for c in config.listar_cenarios()]
        erros = []
        for cid in ids:
            config.usar_cenario(cid)
            erros += [(f"[{cid}] " if len(ids) > 1 else "") + e for e in decisoes.validar_repositorio()]
        print("\n".join(erros) or "políticas e decisões válidas")
        return 1 if erros else 0
    elif a.cmd == "painel":
        gerar_painel()
    elif a.cmd == "cenarios":
        for c in config.listar_cenarios():
            existe = (config.RAIZ / c["dados"] / "estado.json").exists()
            print(c["id"] if a.ids else f"{c['id']:<10} {c['modo']:<7} {c['nome']} · {c['dados']}"
                  f"{'' if existe else ' (ainda sem estado)'}")
    elif a.cmd == "site":
        for c in montar_site(a.destino):
            print(f"site: {c['id']} → {c['painel'] or 'sem painel ainda'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
