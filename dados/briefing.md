# Briefing · fechamento de 2026-10-21

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-22.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.067935 · PL R$ 357,005,240 · dia -0.07% · 21d +3.67% vs CDI +1.07% · desde o início +6.79% vs CDI +2.28%
- Fluxo de cotistas no dia: R$ 1,663,206 · caixa da gestora R$ 2,043,660
- Alocação (atual → alvo): caixa 42.2%→40%, prefixado 14.3%→15%, inflacao 19.7%→20%, dolar 8.9%→10%, bolsa 14.9%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%
- Congelados (sem número confiável): inflacao, prefixado

## Extração
- Dívida técnica 29.9/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0014** tesouro `falha_real` há 2 dia(s), ação `corrigir_conector` — série tesouro parada em 2026-10-15 (esperado 2026-10-16)

## Dashboards
- Credibilidade 83% · confiança média 80%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-21 | 0 | — | 100% |
| selic | 13.75 | 2026-10-21 | 0 | — | 100% |
| dolar | 5.0277 | 2026-10-21 | 0 | — | 100% |
| ipca_12m | 4.58 | 2026-09-01 | 0 | — | 100% |
| focus_ipca | 5.219 | 2026-10-16 | 0 | — | 100% |
| focus_selic | 13.25 | 2026-10-16 | 0 | — | 100% |
| ibov | 206495.0 | 2026-10-21 | 0 | — | 100% |
| bova11 | 203.5 | 2026-10-21 | 0 | — | 100% |
| taxa_pre | — | 2026-10-15 | 3 | suspender | 0% |
| taxa_ipca | — | 2026-10-15 | 3 | suspender | 0% |

## Alertas ativos
- [media] DEFAS-taxa_ipca — Painel: Tesouro IPCA+ (% a.a. real) defasado
- [media] DEFAS-taxa_pre — Painel: Tesouro Prefixado (% a.a.) defasado
- [alta] INC-0014 — INC-0014 · Tesouro Direto (CSV): o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 08:02 · Téo (engenheiro de plantão): INC-0015 · BCB · SGS (o conector falhou de verdade nesta extração, aberto ontem): `corrigir_conector` — falha real no conector: só resolve mexendo no código.
- 09:02 · Caio (líder de Dashboards): Tesouro Prefixado (% a.a.) (3 dia(s) atrasado): `suspender` — 3 dias sem dado: prefiro não publicar a induzir o comitê ao erro.
- 09:04 · Caio (líder de Dashboards): Tesouro IPCA+ (% a.a. real) (3 dia(s) atrasado): `suspender` — 3 dias sem dado: prefiro não publicar a induzir o comitê ao erro.

## Últimos eventos
- 2026-10-21 · extracao · INC-0015 resolvido: BCB · SGS voltou após 1 dia(s) (corrigir_conector)
- 2026-10-20 · extracao · INC-0015: falha real em BCB · SGS
- 2026-10-19 · extracao · INC-0014: falha real em Tesouro Direto (CSV)
- 2026-10-16 · extracao · INC-0013 resolvido: Yahoo Finance voltou após 3 dia(s) (corrigir_conector)
