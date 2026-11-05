# Briefing · fechamento de 2026-11-04

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-11-05.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.028690 · PL R$ 339,792,899 · dia +0.08% · 21d -1.17% vs CDI +1.07% · desde o início +2.87% vs CDI +2.75%
- Fluxo de cotistas no dia: R$ -1,115,643 · caixa da gestora R$ 2,048,725
- Alocação (atual → alvo): caixa 34.0%→35%, prefixado 15.4%→15%, inflacao 25.7%→25%, dolar 15.2%→15%, bolsa 9.7%→10%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 25.2/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0017** tesouro `falha_real` há 0 dia(s), ação `corrigir_conector` — série tesouro parada em 2026-10-30 (esperado 2026-11-03)
- **INC-0016** bcb_sgs `falha_real` há 0 dia(s), ação `corrigir_conector` — JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- ⚠️ Falha REAL no conector `bcb_sgs`: JSONDecodeError: Expecting value: line 1 column 1 (char 0) (corrigir em `gestora/fontes.py`)

## Dashboards
- Credibilidade 83% · confiança média 86%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-11-03 | 1 | estimar | 60% |
| selic | 13.75 | 2026-11-03 | 1 | usar_ontem | 80% |
| dolar | 5.4921 | 2026-11-03 | 1 | estimar | 60% |
| ipca_12m | 4.58 | 2026-09-01 | 0 | — | 100% |
| focus_ipca | 5.2166 | 2026-10-30 | 0 | — | 100% |
| focus_selic | 13.5 | 2026-10-30 | 0 | — | 100% |
| ibov | 167564.0 | 2026-11-04 | 0 | — | 100% |
| bova11 | 164.82 | 2026-11-04 | 0 | — | 100% |
| taxa_pre | 14.89 | 2026-10-30 | 1 | usar_ontem | 80% |
| taxa_ipca | 7.88 | 2026-10-30 | 1 | usar_ontem | 80% |

## Alertas ativos
- [alta] INC-0016 — INC-0016 · BCB · SGS: o conector falhou de verdade nesta extração
- [alta] INC-0017 — INC-0017 · Tesouro Direto (CSV): o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 09:02 · Lia (analista de dados): CDI (% a.a.) (1 dia(s) atrasado): `estimar` — o CDI acompanha a Selic, dá para estimar com folga.
- 09:04 · Caio (líder de Dashboards): Selic meta (% a.a.) (1 dia(s) atrasado): `usar_ontem` — número que muda devagar; repetir o último é seguro.
- 09:06 · Lia (analista de dados): Dólar PTAX (R$) (1 dia(s) atrasado): `estimar` — só um dia de atraso; estimo pela tendência da última semana.
- 09:08 · Caio (líder de Dashboards): Tesouro Prefixado (% a.a.) (1 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.
- 09:10 · Caio (líder de Dashboards): Tesouro IPCA+ (% a.a. real) (1 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.

## Últimos eventos
- 2026-11-04 · extracao · INC-0016: falha real em BCB · SGS
- 2026-11-04 · extracao · INC-0017: falha real em Tesouro Direto (CSV)
