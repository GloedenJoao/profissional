# Briefing · fechamento de 2026-10-19

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-20.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.067260 · PL R$ 353,807,619 · dia -0.02% · 21d +3.64% vs CDI +1.07% · desde o início +6.73% vs CDI +2.17%
- Fluxo de cotistas no dia: R$ 1,723,440 · caixa da gestora R$ 2,041,899
- Alocação (atual → alvo): caixa 41.7%→40%, prefixado 14.4%→15%, inflacao 19.9%→20%, dolar 9.0%→10%, bolsa 14.9%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 29.3/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0014** tesouro `falha_real` há 0 dia(s), ação `corrigir_conector` — série tesouro parada em 2026-10-15 (esperado 2026-10-16)

## Dashboards
- Credibilidade 82% · confiança média 96%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-19 | 0 | — | 100% |
| selic | 13.75 | 2026-10-19 | 0 | — | 100% |
| dolar | 5.0564 | 2026-10-19 | 0 | — | 100% |
| ipca_12m | 4.58 | 2026-09-01 | 0 | — | 100% |
| focus_ipca | 5.219 | 2026-10-16 | 0 | — | 100% |
| focus_selic | 13.25 | 2026-10-16 | 0 | — | 100% |
| ibov | 205079.0 | 2026-10-19 | 0 | — | 100% |
| bova11 | 202.42 | 2026-10-19 | 0 | — | 100% |
| taxa_pre | 12.64 | 2026-10-15 | 1 | usar_ontem | 80% |
| taxa_ipca | 6.84 | 2026-10-15 | 1 | usar_ontem | 80% |

## Alertas ativos
- [media] ERRO-dolar-2026-10-07 — Painel errou Dólar PTAX (R$) de 2026-10-07
- [alta] INC-0014 — INC-0014 · Tesouro Direto (CSV): o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 09:02 · Caio (líder de Dashboards): Tesouro Prefixado (% a.a.) (1 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.
- 09:04 · Caio (líder de Dashboards): Tesouro IPCA+ (% a.a. real) (1 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.
- 10:10 · Rafael (CIO): Carteira coerente com os números. Mantemos o alvo.

## Últimos eventos
- 2026-10-19 · extracao · INC-0014: falha real em Tesouro Direto (CSV)
- 2026-10-16 · extracao · INC-0013 resolvido: Yahoo Finance voltou após 3 dia(s) (corrigir_conector)
- 2026-10-13 · extracao · INC-0010 resolvido: BCB · SGS voltou após 3 dia(s) (corrigir_conector)
- 2026-10-13 · extracao · INC-0013: falha real em Yahoo Finance
- 2026-10-13 · dashboards · Estimativa errada de dolar em 2026-10-07: 4.9211 vs real 4.9935
