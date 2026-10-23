"""Verificações de integridade (19h): o motor confere o próprio trabalho todo dia.

Cada verificação devolve {"id", "nome", "ok", "detalhe"} e entra no rastro do dia. Uma verificação que falha não
interrompe a empresa (o dia já aconteceu), mas aparece em vermelho no site e conta na aba Validação.
"""
from __future__ import annotations

from datetime import date

from . import config
from .mercado import Mercado
from .rastro import Rastro, brl, data, num, pct


def verificar(rastro: Rastro, estado: dict, d: date, mercado: Mercado, politicas: dict, fundo_conta: dict,
              empresa_conta: dict, situacao: dict) -> list[dict]:
    hoje = d.isoformat()
    out: list[dict] = []

    def chk(id_: str, nome: str, ok: bool, detalhe: str) -> None:
        out.append({"id": id_, "nome": nome, "ok": bool(ok), "detalhe": detalhe})

    # 1) sem olhar o futuro: as reuniões só usam o que estava publicado às 08h; a marcação, preços até o dia
    from .simulacao import corte  # import tardio: simulacao importa este módulo
    vistos, futuros = 0, []
    for ind, reg in estado["dashboards"]["indicadores"].items():
        serie = reg.get("serie") or config.INDICADORES[ind]["serie"]
        limite = corte(serie, d)[0].isoformat()
        for rot, x in (("painel", reg.get("data_ref")), ("tendência", (reg.get("tendencia") or {}).get("ate"))):
            if x:
                vistos += 1
                if x > limite:
                    futuros.append(f"{rot} {ind} {data(x)} > {data(limite)}")
    for f in estado["extracao"]["fontes"].values():
        for s, lib in f["liberado_ate"].items():
            if lib:
                vistos += 1
                if lib > corte(s, d)[0].isoformat():
                    futuros.append(f"portão {s} {data(lib)}")
    for a, p in estado["fundo"]["posicoes"].items():
        if p.get("data_preco"):
            vistos += 1
            if p["data_preco"] > hoje:
                futuros.append(f"preço {a} {data(p['data_preco'])}")
    chk("sem_futuro", "Nada do futuro: reuniões só com o publicado até as 08h, marcação só com preços até o dia",
        not futuros, f"{vistos} datas conferidas contra o calendário de publicação de cada fonte" if not futuros
        else "; ".join(futuros[:4]))

    # 2) portão: o painel só usa o que a Extração liberou
    fora = []
    for ind, s in situacao.items():
        reg = estado["dashboards"]["indicadores"][ind]
        if reg.get("data_ref") and s["lib"] and reg["data_ref"] > s["lib"]:
            fora.append(f"{ind} {data(reg['data_ref'])} > liberado {data(s['lib'])}")
    chk("portao", "O painel só usa dados liberados pela Extração", not fora,
        f"{len(situacao)} indicadores dentro do que foi liberado" if not fora else "; ".join(fora))

    # 3) contabilidade: patrimônio = soma das posições; cota × cotas = patrimônio
    fundo = estado["fundo"]
    soma = sum(p["valor"] for p in fundo["posicoes"].values())
    dif1 = abs(soma - fundo["pl"])
    dif2 = abs(fundo["cota"] * fundo["cotas"] - fundo["pl"])
    chk("contabilidade", "Patrimônio = soma das posições = cota × cotas", dif1 < 0.02 and dif2 < 1.0,
        f"soma {brl(soma, 2)}; patrimônio {brl(fundo['pl'], 2)}; cota × cotas {brl(fundo['cota'] * fundo['cotas'], 2)}")

    # 4) a variação do patrimônio é explicada pelos componentes
    c = fundo_conta
    dif = abs(c["conferencia"] - c["pl_fim"])
    chk("reconciliacao", "Variação do patrimônio = resultado dos ativos − taxa − custos + fluxo", dif < 1.0,
        f"{brl(c['pl_ini'], 2)} + {brl(c['resultado'], 2)} − {brl(c['taxa'], 2)} − {brl(c['custo'], 2)} + "
        f"{brl(c['fluxo'], 2)} = {brl(c['conferencia'], 2)} (diferença {brl(dif, 2)})")

    # 5) alvo dentro da política
    alvo, lim = estado["executivos"]["alvo"], politicas["fundo"]["limites"]
    problemas = [f"{a} {pct(w, 1)} fora de {pct(lim[a][0], 0)}–{pct(lim[a][1], 0)}" for a, w in alvo.items()
                 if not lim[a][0] - 1e-9 <= w <= lim[a][1] + 1e-9]
    if abs(sum(alvo.values()) - 1) > 1e-6:
        problemas.append(f"soma {pct(sum(alvo.values()), 2)}")
    chk("limites", "Alvo da carteira soma 100% e respeita os limites", not problemas,
        "alvo " + ", ".join(f"{a} {pct(w, 1)}" for a, w in alvo.items()) if not problemas else "; ".join(problemas))

    # 6) preços conferem com a fonte
    divergentes = []
    for a, p in fundo["posicoes"].items():
        if a == "caixa" or not p.get("data_preco"):
            continue
        if p["serie"] == "tesouro":
            tipo = config.TITULOS[a][0]
            h = mercado.titulo(tipo, p["titulo"], p["data_preco"])
            real = h[2] if h and h[0] == p["data_preco"] else None
        else:
            u = mercado.ultimo(p["serie"], p["data_preco"])
            real = u[1] if u and u[0] == p["data_preco"] else None
        if real is None or abs(real - p["preco"]) > 1e-9:
            divergentes.append(f"{a}: usado {p['preco']} × fonte {real}")
    chk("precos", "Preço usado na marcação = preço da fonte na data", not divergentes,
        f"{sum(1 for a in fundo['posicoes'] if a != 'caixa')} preços conferidos com as séries gravadas" if not divergentes
        else "; ".join(divergentes))

    # 7) caixa da gestora
    e = empresa_conta
    g = estado["gestora"]["caixa"]
    dif = abs(e["caixa_ant"] + e["receita"] - e["custo"] - g)
    chk("caixa_gestora", "Caixa da gestora = ontem + receita − custos", dif < 0.02,
        f"{brl(e['caixa_ant'], 2)} + {brl(e['receita'], 2)} − {brl(e['custo'], 2)} = {brl(g, 2)}")

    # 8) carteira de referência coerente
    ref = estado["referencia"]
    soma_ref = sum(p["valor"] for p in ref["posicoes"].values())
    chk("referencia", "Carteira de referência: cota × cotas = soma das posições",
        abs(ref["cota"] * ref["cotas"] - soma_ref) < 1.0, f"cota de referência {num(ref['cota'], 6)}")

    # a etapa no rastro
    et = rastro.etapa("verificacoes", "fundo", "19:00", "Verificações", "O motor fez tudo certo?")
    b = et.tabela("Verificações de integridade", ["Verificação", "Resultado", "Detalhe"],
                  [[c_["nome"], "✓ ok" if c_["ok"] else "✗ falhou", c_["detalhe"]] for c_ in out],
                  nota="Rodam todo dia, depois do fechamento. Uma falha aqui é bug do motor, não da empresa.")
    ok = sum(c_["ok"] for c_ in out)
    f = estado["fundo"]
    et.diz(0, f"Fechamento de {data(hoje)}: cota {num(f['cota'], 6)} ({pct(f['retorno_dia'], 2, True)}), patrimônio "
              f"R$ {num(f['pl'] / 1e6, 1)} mi. Verificações: {ok} de {len(out)} ok"
              + ("." if ok == len(out) else ": falhou " + ", ".join(c_["nome"] for c_ in out if not c_["ok"]) + "."),
           tipo="fechamento", bloco=b)
    et.status("ok" if ok == len(out) else "ruim", f"{ok}/{len(out)} verificações ok")
    et.dados["bloco_principal"] = b
    return out
