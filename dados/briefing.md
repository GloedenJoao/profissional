# Briefing · fechamento de 2026-10-22

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-23.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.066340 · PL R$ 358,561,719 · dia -0.15% · 21d +3.49% vs CDI +1.07% · desde o início +6.63% vs CDI +2.33%
- Fluxo de cotistas no dia: R$ 2,089,709 · caixa da gestora R$ 2,044,606
- Alocação (atual → alvo): caixa 42.7%→40%, prefixado 14.2%→15%, inflacao 19.6%→20%, dolar 8.9%→10%, bolsa 14.6%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%
- Congelados (sem número confiável): inflacao, prefixado

## Extração
- Dívida técnica 29.9/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0014** tesouro `falha_real` há 3 dia(s), ação `corrigir_conector` — série tesouro parada em 2026-10-15 (esperado 2026-10-16)

## Dashboards
- Credibilidade 83% · confiança média 80%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-22 | 0 | — | 100% |
| selic | 13.75 | 2026-10-22 | 0 | — | 100% |
| dolar | 5.0383 | 2026-10-22 | 0 | — | 100% |
| ipca_12m | 4.58 | 2026-09-01 | 0 | — | 100% |
| focus_ipca | 5.219 | 2026-10-16 | 0 | — | 100% |
| focus_selic | 13.25 | 2026-10-16 | 0 | — | 100% |
| ibov | 204120.0 | 2026-10-22 | 0 | — | 100% |
| bova11 | 200.96 | 2026-10-22 | 0 | — | 100% |
| taxa_pre | — | 2026-10-15 | 4 | suspender | 0% |
| taxa_ipca | — | 2026-10-15 | 4 | suspender | 0% |

## Alertas ativos
- [media] DEFAS-taxa_ipca — Painel: Tesouro IPCA+ (% a.a. real) defasado
- [media] DEFAS-taxa_pre — Painel: Tesouro Prefixado (% a.a.) defasado
- [alta] INC-0014 — INC-0014 · Tesouro Direto (CSV): o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 09:02 · Caio (líder de Dashboards): Tesouro Prefixado (% a.a.) (4 dia(s) atrasado): `suspender` — 4 dias sem dado: prefiro não publicar a induzir o comitê ao erro.
- 09:04 · Caio (líder de Dashboards): Tesouro IPCA+ (% a.a. real) (4 dia(s) atrasado): `suspender` — 4 dias sem dado: prefiro não publicar a induzir o comitê ao erro.

## Últimos eventos
- 2026-10-21 · extracao · INC-0015 resolvido: BCB · SGS voltou após 1 dia(s) (corrigir_conector)
- 2026-10-20 · extracao · INC-0015: falha real em BCB · SGS
- 2026-10-19 · extracao · INC-0014: falha real em Tesouro Direto (CSV)
- 2026-10-16 · extracao · INC-0013 resolvido: Yahoo Finance voltou após 3 dia(s) (corrigir_conector)
