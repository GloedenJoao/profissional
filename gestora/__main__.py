"""Linha de comando: python -m gestora [--cenario ID] {fechamento,avancar,sincronizar,validar,painel,cenarios,site}."""
from __future__ import annotations

import argparse
import hashlib
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


def fechamento(data_ref: date | None, inicio: date | None, extrair: bool = True, conectores=None,
               extrair_ate: date | None = None) -> list[str]:
    """Extrai e simula até `data_ref`. `extrair_ate` (cenários do passado) baixa dados além de `data_ref`: o motor
    corta tudo pela data simulada, então isso só adianta trabalho para os próximos avanços."""
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
        controle = extracao.extrair(janela_ini, max(ref, extrair_ate or ref), conectores)
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
        estado, reg = simulacao.simular_dia(estado, d, mercado, politicas, dec, controle if d == ref else None,
                                            times=config.cenario().get("times", True))
        armazem.gravar_json(config.DIAS / f"{d}.json", reg)
        painel.registrar_historico(reg)
        feitos.append(d.isoformat())
        r = reg["resumo"]
        print(f"{d}: cota {r['cota']:.6f} PL {r['pl']:,.0f} incidentes {r['incidentes_abertos']} "
              f"credibilidade {r['credibilidade']:.0%} decisão={reg['decisao']['autor'] or 'piloto automático'}")
    armazem.gravar_json(config.DADOS / "estado.json", estado)
    gerar_painel(controle)
    return feitos


# Avanço em blocos: a janela de extração de cada bloco (com os dias baixados adiantado) cabe nos 30 pregões
# que o conector da B3 baixa.
PASSO_AVANCO = 12
ADIANTE = 10


def _series_cobrem(d: date) -> bool:
    """As séries já gravadas têm o que cada fonte publicaria até `d`? Então não precisa baixar nada."""
    mercado = Mercado()
    for fonte, meta in config.FONTES.items():
        for serie in meta["series"]:
            ultima = mercado.ultima_data(serie)
            if ultima is None or ultima < simulacao._data_esperada(serie, fonte, d).isoformat():
                return False
    return True


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
    feitos, fundada = [], estado is not None
    for i in range(0, len(pendentes), PASSO_AVANCO):
        bloco = pendentes[i:i + PASSO_AVANCO]
        # o passado não muda: se as séries já cobrem o bloco, simula sem baixar; senão baixa também os próximos
        # dias úteis, para o próximo clique em "simular" não esperar a extração
        baixar = extrair and not (fundada and _series_cobrem(bloco[-1]))
        adiante = bloco[-1]
        for _ in range(ADIANTE):
            adiante = min(limite, calendario.proximo_dia_util(adiante))
        if extrair and not baixar:
            print(f"{cen['id']}: séries já cobrem até {bloco[-1]}, simulando sem extrair")
        feitos += fechamento(bloco[-1], inicio, extrair=baixar, conectores=conectores, extrair_ate=adiante)
        fundada = True
    return feitos


def pendentes(hoje: date | None = None) -> list[str]:
    """Cenários com `automatico` em cenario.json que ainda têm dia útil para simular até ontem."""
    limite = calendario.dia_util_anterior(hoje or _hoje())
    ids = []
    for c in config.listar_cenarios():
        if not c.get("automatico"):
            continue
        estado = armazem.ler_json(config.RAIZ / c["dados"] / "estado.json")
        base = date.fromisoformat(estado["ultima_data"] if estado else c["inicio"])
        if calendario.dias_uteis_entre(base, limite):
            ids.append(c["id"])
    return ids


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
    eventos, decididas = [], []
    for d in feitos:
        reg = armazem.ler_json(config.DIAS / f"{d}.json") or {}
        eventos += [f"- {d} · {simulacao.AREAS.get(e['area'], e['area'])} · {e['texto']}" for e in reg.get("eventos", [])
                    if e["tipo"] != "info"]
        decididas += [f"- {d} · {f['quem']} ({f['papel']}): {f['texto']}" for f in reg.get("ata", [])
                      if f["tipo"] in ("decisao", "conselho")]
    if decididas:
        linhas += ["<details><summary>O que os times decidiram</summary>", "", *decididas[-25:], "", "</details>", ""]
    if eventos:
        linhas += ["<details><summary>O que aconteceu</summary>", "", *eventos[-20:], "", "</details>", ""]
    site = f"https://{config.REPO.split('/')[0].lower()}.github.io/{config.REPO.split('/')[1]}"
    linhas.append(f"**Assistir:** [reuniões ao vivo]({site}/#/{cen['id']}/aovivo) · [painel]({site}/#/{cen['id']})")
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
    # sem issues de alerta (cenário que anda sozinho a cada meia hora): fecha as que tiverem sobrado abertas
    alertas = estado["alertas"] if cen.get("issues", True) else {}
    resultado = processos.sincronizar(gh, alertas, estado["ultima_data"], anterior, paralelo)
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
        origem = config.RAIZ / c["dados"]
        base = "" if c["id"] == config.CENARIO_PADRAO else f"cenarios/{c['id']}/"
        existe = (origem / "painel.json").exists()
        if existe:
            (destino / base).mkdir(parents=True, exist_ok=True)
            shutil.copy(origem / "painel.json", destino / base / "painel.json")
            if (origem / "dias").exists():  # cada dia com a ata das reuniões: o modo ao vivo toca daqui
                shutil.copytree(origem / "dias", destino / base / "dias")
        indice.append({k: c.get(k) for k in ("id", "nome", "descricao", "modo", "inicio", "automatico")}
                      | {"painel": f"{base}painel.json" if existe else None, "dias": f"{base}dias/" if existe else None})
    armazem.gravar_json(destino / "cenarios.json", {"repositorio": config.REPO, "cenarios": indice})
    # Versão do site: entra no nome dos arquivos (o navegador nunca usa app.js velho) e em versao.json, que a
    # página consulta de tempos em tempos para se atualizar sozinha quando sai um fechamento ou avanço novo.
    # `codigo` só muda quando muda o código do site: aí a página se recarrega sozinha; dado novo só recarrega os JSONs.
    versao = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    codigo = hashlib.sha256(b"".join((config.RAIZ / "site" / n).read_bytes()
                                     for n in ("index.html", "app.js", "style.css"))).hexdigest()[:12]
    paineis = {c["id"]: armazem.ler_json(destino / c["painel"]).get("data_referencia") for c in indice if c["painel"]}
    armazem.gravar_json(destino / "versao.json", {"versao": versao, "codigo": codigo, "paineis": paineis})
    pagina = destino / "index.html"
    pagina.write_text(pagina.read_text(encoding="utf-8").replace("__VERSAO__", versao).replace("__CODIGO__", codigo),
                      encoding="utf-8")
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
    av.add_argument("--automatico", action="store_true", help="avança o que `automatico` de cenario.json manda")
    av.add_argument("--resumo", type=Path, help="grava aqui o resumo em Markdown do avanço")
    av.add_argument("--sem-extracao", action="store_true", help="usa só os dados já gravados")
    sub.add_parser("sincronizar", help="espelha os alertas em issues do GitHub")
    sub.add_parser("validar", help="valida políticas e decisões pendentes (de todos os cenários, sem --cenario)")
    sub.add_parser("painel", help="regera painel.json e briefing.md")
    ce = sub.add_parser("cenarios", help="lista os cenários")
    ce.add_argument("--ids", action="store_true", help="só os ids, um por linha")
    ce.add_argument("--pendentes", action="store_true", help="só os automáticos com dia a simular (ids)")
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
        elif a.automatico:
            dias = int((config.cenario().get("automatico") or {}).get("dias_por_execucao", 1))
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
    elif a.cmd == "cenarios" and a.pendentes:
        print("\n".join(pendentes()))
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
