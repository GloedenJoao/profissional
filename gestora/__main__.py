"""Linha de comando: python -m gestora {fechamento,sincronizar,validar,painel}."""
from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta, timezone

from . import armazem, calendario, config, decisoes, extracao, painel, processos, simulacao
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


def sincronizar() -> None:
    gh = processos.cliente_do_ambiente()
    if gh is None:
        print("sem GITHUB_TOKEN/GITHUB_REPOSITORY: sincronização de issues pulada")
        return
    estado = armazem.ler_json(config.DADOS / "estado.json")
    anterior = armazem.ler_json(config.DADOS / "processos.json")
    resultado = processos.sincronizar(gh, estado["alertas"], estado["ultima_data"], anterior)
    armazem.gravar_json(config.DADOS / "processos.json", resultado)
    print("\n".join(resultado["log"]) or "issues já estavam em dia")
    gerar_painel()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="gestora")
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("fechamento", help="extrai dados e simula os dias úteis pendentes")
    f.add_argument("--data", type=date.fromisoformat, help="data de referência (padrão: dia útil anterior a hoje)")
    f.add_argument("--inicio", type=date.fromisoformat, help="fundação da empresa, se ainda não existe estado")
    f.add_argument("--sem-extracao", action="store_true", help="usa só os dados já gravados")
    sub.add_parser("sincronizar", help="espelha os alertas em issues do GitHub")
    sub.add_parser("validar", help="valida políticas e decisões pendentes")
    sub.add_parser("painel", help="regera painel.json e briefing.md")
    a = ap.parse_args(argv)
    if a.cmd == "fechamento":
        fechamento(a.data, a.inicio, extrair=not a.sem_extracao)
    elif a.cmd == "sincronizar":
        sincronizar()
    elif a.cmd == "validar":
        erros = decisoes.validar_repositorio()
        print("\n".join(erros) or "políticas e decisões válidas")
        return 1 if erros else 0
    elif a.cmd == "painel":
        gerar_painel()
    return 0


if __name__ == "__main__":
    sys.exit(main())
