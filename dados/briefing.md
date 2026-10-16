# Briefing · fechamento de 2026-10-15

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-16.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.065996 · PL R$ 350,774,114 · dia -0.31% · 21d +3.56% vs CDI +1.07% · desde o início +6.60% vs CDI +2.07%
- Fluxo de cotistas no dia: R$ 1,427,111 · caixa da gestora R$ 2,040,387
- Alocação (atual → alvo): caixa 41.3%→40%, prefixado 14.5%→15%, inflacao 20.1%→20%, dolar 9.1%→10%, bolsa 15.0%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%
- Congelados (sem número confiável): bolsa

## Extração
- Dívida técnica 30.1/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0013** yahoo `falha_real` há 2 dia(s), ação `corrigir_conector` — série bova11 parada em 2026-10-09 (esperado 2026-10-13)

## Dashboards
- Credibilidade 82% · confiança média 84%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-15 | 0 | — | 100% |
| selic | 13.75 | 2026-10-15 | 0 | — | 100% |
| dolar | 5.0521 | 2026-10-15 | 0 | — | 100% |
| ipca_12m | 4.58 | 2026-09-01 | 0 | — | 100% |
| focus_ipca | 5.2245 | 2026-10-09 | 0 | — | 100% |
| focus_selic | 13.25 | 2026-10-09 | 0 | — | 100% |
| ibov | 209067.0 | 2026-10-09 | 3 | usar_ontem | 40% |
| bova11 | — | 2026-10-09 | 3 | suspender | 0% |
| taxa_pre | 12.64 | 2026-10-15 | 0 | — | 100% |
| taxa_ipca | 6.84 | 2026-10-15 | 0 | — | 100% |

## Alertas ativos
- [media] DEFAS-bova11 — Painel: BOVA11 (R$) defasado
- [media] DEFAS-ibov — Painel: Ibovespa (pts) defasado
- [media] ERRO-dolar-2026-10-07 — Painel errou Dólar PTAX (R$) de 2026-10-07
- [media] ERRO-ibov-2026-10-05 — Painel errou Ibovespa (pts) de 2026-10-05
- [alta] INC-0013 — INC-0013 · Yahoo Finance: o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 09:02 · Caio (líder de Dashboards): Ibovespa (pts) (3 dia(s) atrasado): `usar_ontem` — errei a estimativa disso há pouco, vou de último valor.
- 09:04 · Caio (líder de Dashboards): BOVA11 (R$) (3 dia(s) atrasado): `suspender` — 3 dias sem dado: prefiro não publicar a induzir o comitê ao erro.

## Últimos eventos
- 2026-10-13 · extracao · INC-0010 resolvido: BCB · SGS voltou após 3 dia(s) (corrigir_conector)
- 2026-10-13 · extracao · INC-0013: falha real em Yahoo Finance
- 2026-10-13 · dashboards · Estimativa errada de dolar em 2026-10-07: 4.9211 vs real 4.9935
- 2026-10-09 · extracao · INC-0009 resolvido: Yahoo Finance voltou após 4 dia(s) (corrigir_conector)
- 2026-10-09 · extracao · INC-0011 resolvido: BCB · PTAX (Olinda) voltou após 1 dia(s) (escalar)
- 2026-10-09 · extracao · INC-0012 resolvido: BCB · Focus (Olinda) voltou após 1 dia(s) (escalar)
- 2026-10-09 · dashboards · Estimativa errada de ibov em 2026-10-05: 193890.8007 vs real 206912.0
- 2026-10-08 · extracao · INC-0011: falha real em BCB · PTAX (Olinda)
- 2026-10-08 · extracao · INC-0012: falha real em BCB · Focus (Olinda)
