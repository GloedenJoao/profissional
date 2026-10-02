"""O motor por dentro: todas as regras, com os parâmetros vigentes, numa estrutura que o site mostra na aba Regras.

Nada aqui decide nada: só descreve as constantes e funções de simulacao.py e times.py e os parâmetros de
politicas.json. Se uma regra muda no código, muda aqui também (os números vêm das mesmas constantes).
"""
from __future__ import annotations

from . import config, simulacao, times
from .rastro import brl, num, pct


def descrever(politicas: dict) -> list[dict]:
    m = times.modelo(politicas)
    pf, pg, pd = politicas["fundo"], politicas["gestora"], politicas["dashboards"]
    est = {"ativo": True, "multiplicador": 1.0, **politicas["extracao"].get("estresse", {})}
    cot = {**simulacao.COTISTAS_PADRAO, **pf.get("cotistas", {})}
    R = times.REGRAS_GESTORA
    neutro = pf["alocacao_inicial"]
    return [
        {"etapa": "geral", "titulo": "O dia útil", "itens": [
            "Etapas em ordem: Herança 07h → Extração 08h → Dashboards 09h → Comitê 10h → Fundo 18h → Empresa 18h30 "
            "→ Verificações 19h. Cada uma só enxerga o que a anterior entregou.",
            "As reuniões da manhã só conhecem o que estava publicado às 08h. O fundo é marcado às 18h com os preços "
            "de fechamento do dia.",
            "O experimento processa o dia D na manhã de D+1 (seg–sex 08h), quando todos os dados reais de D já saíram. "
            "A simulação processa um dia por clique, com as séries de 2026 já baixadas.",
            "Determinístico: o mesmo dia, com os mesmos dados, dá sempre o mesmo resultado. O único acaso é o teste de "
            "estresse da Extração, com semente = cenário + data + fonte.",
        ]},
        {"etapa": "extracao", "titulo": "Quando cada fonte publica", "tabela": {
            "colunas": ["Série", "Fonte", "Disponível às 08h de D"],
            "linhas": [[config.SERIES_INFO[s][0], next(meta["nome"] for meta in config.FONTES.values() if s in meta["series"]),
                        config.REGRA_PUBLICACAO[config.PUBLICACAO[s]]] for s in config.PUBLICACAO]}},
        {"etapa": "extracao", "titulo": "Teste de estresse (falhas simuladas)", "itens": [
            f"Ligado: {'sim' if est['ativo'] else 'não'} · multiplicador {num(est['multiplicador'], 1)} "
            "(politicas.json → extracao.estresse).",
            "Chance diária de uma fonte sem incidente falhar = base da fonte × (1 + dívida técnica ÷ 40) × multiplicador. "
            "Falha se o sorteio (0 a 1) for menor que a chance.",
            "Tipo da falha sorteado com pesos: " + ", ".join(f"{k} {v}" for k, v in simulacao.PESOS_TIPO.items()) + ".",
            "Enquanto há incidente aberto, as séries da fonte ficam paradas no portão, mesmo que o dado real exista.",
        ], "tabela": {"colunas": ["Fonte", "Chance base por dia"],
                      "linhas": [[meta["nome"], pct(meta["prob_base"], 1)] for meta in config.FONTES.values()]}},
        {"etapa": "extracao", "titulo": "Chance de um incidente simulado se resolver por dia", "tabela": {
            "colunas": ["Tipo", "Ação", "Chance"],
            "linhas": [[t, a, pct(p_, 0)] for (t, a), p_ in simulacao.PROB_RESOLVER.items()]
            + [["mudanca_formato", "corrigir_conector", "0,25 × dias de esforço + 0,05 × (equipe − 3), até 95%"],
               ["mudanca_formato", "outras", "0%"], ["falha_real", "qualquer", "resolve quando a fonte real publica"]]}},
        {"etapa": "extracao", "titulo": "Triagem do time de Extração (Bia e Téo)", "itens": times.REGRAS_EXTRACAO
            + ["Custos: " + ", ".join(f"`{a}` {c} ponto(s)" for a, c in config.CUSTO_ACAO.items()) + "."]},
        {"etapa": "extracao", "titulo": "Dívida técnica", "itens": [
            f"Começa em {num(simulacao.DIVIDA['inicial'], 0)}/100. Por dia: +{num(simulacao.DIVIDA['deriva_dia'], 2)} "
            f"(o código envelhece) + {num(simulacao.DIVIDA['por_incidente'], 1)} por incidente aberto − orçamento ÷ 1.000.",
        ]},
        {"etapa": "dashboards", "titulo": "O que publicar quando falta dado (Caio e Lia)", "itens": times.REGRAS_DASHBOARDS
            + [f"Estratégia padrão da política: `{pd['estrategia_padrao']}`."]},
        {"etapa": "dashboards", "titulo": "Conferência de qualidade (dados reais)", "itens": [
            f"BOVA11 Yahoo × B3 e dólar SGS × PTAX na mesma data: diferença até {pct(simulacao.TOLERANCIA_DIVERGENCIA, 1)}; "
            "acima disso a confiança do indicador cai 10 p.p.",
            f"Variação do dia de dólar, Ibovespa e BOVA11 comparada aos 21 pregões anteriores: acima de "
            f"{num(simulacao.Z_ATIPICO, 0)} desvios-padrão é sinalizada.",
        ]},
        {"etapa": "dashboards", "titulo": "Estimativas e credibilidade", "itens": [
            "Toda estimativa é conferida quando o dado real chega. Tolerância de erro por indicador: " + ", ".join(
                f"{k} {num(v, 3)}" for k, v in pd.get("tolerancia_erro_estimativa", {}).items()) + " (preços em fração; "
            "taxas em p.p.).",
            f"Credibilidade começa em {pct(simulacao.CREDIBILIDADE['inicial'], 0)}; +{num(simulacao.CREDIBILIDADE['acerto'] * 100, 0)} "
            f"p.p. por estimativa certa, −{num(simulacao.CREDIBILIDADE['erro'] * 100, 0)} p.p. por estimativa errada, e "
            f"{num(simulacao.CREDIBILIDADE['sens_confianca'], 2)} × (confiança média do dia − "
            f"{pct(simulacao.CREDIBILIDADE['confianca_alvo'], 0)}).",
        ]},
        {"etapa": "comite", "titulo": "Quando há reunião de investimentos (Helena, Rafael, Marta)", "itens": [
            "Na primeira reunião da empresa e no primeiro dia útil de cada semana.",
            f"Ou quando: resgate do dia anterior ≥ {pct(m['gatilho_resgate'], 0)} do patrimônio; algum ativo desenquadrado; "
            f"caixa da gestora negativo; a Extração escalou um incidente; BOVA11 ou dólar mexeram "
            f"≥ {pct(m['gatilho_variacao_dia'], 0)} no último pregão.",
            "Todo dia, mesmo sem reunião de investimentos, o comitê revê equipe e orçamento da Extração.",
        ]},
        {"etapa": "comite", "titulo": "Modelo de alocação", "itens": [
            "Alvo de cada ativo = peso neutro + sensibilidade × sinal. O caixa fica com o que sobra.",
            f"Prefixado: sinal = (taxa do prefixado − Focus Selic do fim do ano) ÷ {num(m['escala_premio_prefixado'], 1)} p.p.",
            f"IPCA+: sinal = (juro real do IPCA+ − {num(m['juro_real_neutro'], 1)}%) ÷ {num(m['escala_juro_real'], 1)} p.p.",
            f"Bolsa: sinal = tendência do BOVA11 em {m['janela_tendencia']} pregões ÷ {pct(m['escala_tendencia_bolsa'], 0)}.",
            f"Dólar: sinal = tendência do dólar em {m['janela_tendencia']} pregões ÷ {pct(m['escala_tendencia_dolar'], 0)}.",
            "Sinais limitados entre −1 e +1.",
            f"Travas, nesta ordem: número congelado ou com confiança abaixo de {pct(m['confianca_minima'], 0)} não mexe; "
            "postura defensiva (credibilidade < 60% ou fundo mais de 1 p.p. abaixo do CDI em 21 pregões) não aumenta bolsa "
            f"nem reduz dólar; limites da política; passo máximo de {num(m['passo_max'] * 100, 0)} p.p. por reunião; "
            f"mudança menor que {num(m['zona_morta'] * 100, 0)} p.p. não gira a carteira; caixa mínimo "
            f"{pct(pf['limites']['caixa'][0], 0)}.",
        ], "tabela": {"colunas": ["Ativo", "Neutro", "Sensibilidade", "Limites"],
                      "linhas": [[config.ATIVOS[a], pct(neutro[a], 0),
                                  (num(m["sensibilidade"][a] * 100, 0) + " p.p.") if a in m["sensibilidade"] else "—",
                                  f"{pct(pf['limites'][a][0], 0)}–{pct(pf['limites'][a][1], 0)}"] for a in neutro]}},
        {"etapa": "comite", "titulo": "Equipe e orçamento da Extração", "itens": [
            f"Fôlego = caixa da gestora ÷ custo diário. Abaixo de {R['folego_minimo']} dias: corta "
            f"{brl(R['passo_orcamento'])}/dia de orçamento (ou 1 pessoa, se o orçamento já é zero).",
            f"Contrata 1 pessoa se a Extração escalou, se há 3+ incidentes com equipe menor que 4 ou se a dívida passa de "
            f"{R['divida_para_contratar']}; só com fôlego acima de {R['folego_para_gastar']} dias e "
            f"{R['dias_entre_contratacoes']} dias úteis depois da última contratação.",
            f"Sobe o orçamento em {brl(R['passo_orcamento'])}/dia se a dívida passa de {R['divida_para_orcamento']} e há "
            f"fôlego acima de {R['folego_para_gastar']} dias.",
            f"Enxuga 1 pessoa se não há incidentes, a dívida está abaixo de {R['divida_para_enxugar']}, a equipe passa de 3 "
            "e a receita não cobre o custo.",
            f"Limites: equipe até {pg['equipe_max']}, orçamento até {brl(pg['orcamento_max_dia'])}/dia.",
        ]},
        {"etapa": "fundo", "titulo": "Fundo", "itens": [
            "Marcação pelo administrador com o preço oficial do dia (Tesouro: PU; dólar: PTAX; bolsa: BOVA11), "
            "independente do portão da Extração. Caixa rende o CDI de cada dia útil.",
            f"Taxa de administração {pct(pf['taxa_adm'], 0)} a.a. ÷ 252 por dia útil, paga à gestora.",
            f"Cotistas (sem sorteio): fluxo = {pct(cot['captacao_base'], 2)} + {num(cot['sens_desempenho'], 2)} × excesso "
            f"sobre o CDI em {cot['janela']} pregões + {num(cot['sens_credibilidade'], 3)} × (credibilidade − "
            f"{pct(cot['credibilidade_neutra'], 0)}), limitado a ±{pct(cot['limite'], 0)} do patrimônio por dia.",
            f"Rebalanceia quando o comitê muda o alvo, quando algum peso se afasta mais de "
            f"{num(politicas['executivos']['rebalancear_se_desvio_maior_que'] * 100, 0)} p.p. do alvo ou quando o caixa "
            f"fica negativo. Custo de {pct(pf['custo_transacao'], 2)} sobre o giro. Ativo congelado fica onde está.",
            "Carteira de referência: começa igual ao fundo, fica na alocação neutra (rebalanceada pela mesma regra), "
            "paga a mesma taxa e não tem cotistas. Fundo ÷ referência − 1 = valor das decisões.",
        ]},
        {"etapa": "empresa", "titulo": "Empresa", "itens": [
            f"Receita = taxa de administração do fundo. Custos por dia útil: casa {brl(pg['custo_fixo_dia'])}, "
            f"{brl(pg['custo_engenheiro_dia'])} por pessoa da Extração e o orçamento da Extração.",
            f"Caixa inicial {brl(pg['caixa_inicial'])}. Caixa negativo abre crise e leva o comitê a cortar custos.",
        ]},
        {"etapa": "verificacoes", "titulo": "Verificações diárias", "itens": [
            "Nada do futuro: as reuniões só usam o que estava publicado às 08h (calendário de cada fonte) e a "
            "marcação só usa preços até o dia.",
            "O painel só usa dados liberados pela Extração.",
            "Patrimônio = soma das posições = cota × cotas.",
            "Variação do patrimônio = resultado dos ativos − taxa − custos + fluxo.",
            "Alvo da carteira soma 100% e respeita os limites.",
            "Preço usado na marcação = preço da fonte na data.",
            "Caixa da gestora = ontem + receita − custos.",
            "Carteira de referência: cota × cotas = soma das posições.",
        ]},
    ]
