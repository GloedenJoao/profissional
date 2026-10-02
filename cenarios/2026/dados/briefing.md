# Briefing · fechamento de 2026-01-08 · cenário Simulação 2026

Os times decidem sozinhos. Diretriz do conselho (opcional): `cenarios/2026/empresa/decisoes/2026-01-09.json` vale por cima deles nesse dia.

## Fundo
- Cota 0.997681 · PL R$ 298,804,805 · dia +0.08% · 21d -0.19% vs CDI +0.22% · desde o início -0.23% vs CDI +0.28%
- Fluxo de cotistas no dia: R$ -201,183 · caixa da gestora R$ 2,002,029
- Alocação (atual → alvo): caixa 24.8%→25%, prefixado 25.2%→25%, inflacao 24.8%→25%, dolar 10.0%→10%, bolsa 15.2%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 34.4/100 · equipe 3 · orçamento R$ 1,000/dia
- **INC-0003** bcb_sgs `falha_real` há 0 dia(s), ação `corrigir_conector` — JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- ⚠️ Falha REAL no conector `bcb_sgs`: JSONDecodeError: Expecting value: line 1 column 1 (char 0) (corrigir em `gestora/fontes.py`)

## Dashboards
- Credibilidade 81% · confiança média 92%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 14.9 | 2026-01-07 | 1 | estimar | 60% |
| selic | 15.0 | 2026-01-07 | 1 | usar_ontem | 80% |
| dolar | 5.388 | 2026-01-07 | 1 | usar_ontem | 80% |
| ipca_12m | 4.44 | 2026-01-01 | 0 | — | 100% |
| focus_ipca | 4.0574 | 2026-01-08 | 0 | — | 100% |
| focus_selic | 12.25 | 2026-01-08 | 0 | — | 100% |
| ibov | 162937.0 | 2026-01-08 | 0 | — | 100% |
| bova11 | 159.6 | 2026-01-08 | 0 | — | 100% |
| taxa_pre | 13.07 | 2026-01-08 | 0 | — | 100% |
| taxa_ipca | 7.43 | 2026-01-08 | 0 | — | 100% |

## Alertas ativos
- [media] ERRO-dolar-2026-01-06 — Painel errou Dólar PTAX (R$) de 2026-01-06
- [alta] INC-0003 — INC-0003 · BCB · SGS: o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 09:02 · Lia (analista de dados): CDI (% a.a.) (1 dia(s) atrasado): `estimar` — o CDI acompanha a Selic, dá para estimar com folga.
- 09:04 · Caio (líder de Dashboards): Selic meta (% a.a.) (1 dia(s) atrasado): `usar_ontem` — número que muda devagar; repetir o último é seguro.
- 09:06 · Caio (líder de Dashboards): Dólar PTAX (R$) (1 dia(s) atrasado): `usar_ontem` — errei a estimativa disso há pouco, vou de último valor.

## Últimos eventos
- 2026-01-08 · extracao · INC-0003: falha real em BCB · SGS
- 2026-01-07 · extracao · INC-0002 resolvido: BCB · SGS voltou após 1 dia(s) (aguardar)
- 2026-01-07 · dashboards · Estimativa errada de dolar em 2026-01-06: 5.4141 vs real 5.3797
- 2026-01-06 · extracao · INC-0002: BCB · SGS — a fonte publicou atrasado
- 2026-01-05 · extracao · INC-0001 resolvido: BCB · PTAX (Olinda) voltou após 1 dia(s) (aguardar)
- 2026-01-05 · fundo · Rebalanceamento: giro R$ 30,5 mi, custo R$ 15.240
- 2026-01-02 · extracao · INC-0001: BCB · PTAX (Olinda) — a fonte publicou atrasado
- 2026-01-02 · fundo · Rebalanceamento: giro R$ 30,3 mi, custo R$ 15.154
