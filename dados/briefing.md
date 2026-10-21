# Briefing · fechamento de 2026-10-20

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-21.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.068673 · PL R$ 355,587,740 · dia +0.13% · 21d +3.84% vs CDI +1.07% · desde o início +6.87% vs CDI +2.23%
- Fluxo de cotistas no dia: R$ 1,311,657 · caixa da gestora R$ 2,042,758
- Alocação (atual → alvo): caixa 41.9%→40%, prefixado 14.3%→15%, inflacao 19.8%→20%, dolar 8.9%→10%, bolsa 15.0%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 29.9/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0015** bcb_sgs `falha_real` há 0 dia(s), ação `corrigir_conector` — JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- **INC-0014** tesouro `falha_real` há 1 dia(s), ação `corrigir_conector` — série tesouro parada em 2026-10-15 (esperado 2026-10-16)
- ⚠️ Falha REAL no conector `bcb_sgs`: JSONDecodeError: Expecting value: line 1 column 1 (char 0) (corrigir em `gestora/fontes.py`)

## Dashboards
- Credibilidade 82% · confiança média 84%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-19 | 1 | estimar | 60% |
| selic | 13.75 | 2026-10-19 | 1 | usar_ontem | 80% |
| dolar | 5.0564 | 2026-10-19 | 1 | usar_ontem | 80% |
| ipca_12m | 4.58 | 2026-09-01 | 0 | — | 100% |
| focus_ipca | 5.219 | 2026-10-16 | 0 | — | 100% |
| focus_selic | 13.25 | 2026-10-16 | 0 | — | 100% |
| ibov | 208296.0 | 2026-10-20 | 0 | — | 100% |
| bova11 | 205.01 | 2026-10-20 | 0 | — | 100% |
| taxa_pre | 12.64 | 2026-10-15 | 2 | usar_ontem | 60% |
| taxa_ipca | 6.84 | 2026-10-15 | 2 | usar_ontem | 60% |

## Alertas ativos
- [alta] INC-0014 — INC-0014 · Tesouro Direto (CSV): o conector falhou de verdade nesta extração
- [alta] INC-0015 — INC-0015 · BCB · SGS: o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 08:02 · Téo (engenheiro de plantão): INC-0014 · Tesouro Direto (CSV) (o conector falhou de verdade nesta extração, aberto ontem): `corrigir_conector` — falha real no conector: só resolve mexendo no código.
- 09:02 · Lia (analista de dados): CDI (% a.a.) (1 dia(s) atrasado): `estimar` — o CDI acompanha a Selic, dá para estimar com folga.
- 09:04 · Caio (líder de Dashboards): Selic meta (% a.a.) (1 dia(s) atrasado): `usar_ontem` — número que muda devagar; repetir o último é seguro.
- 09:06 · Caio (líder de Dashboards): Dólar PTAX (R$) (1 dia(s) atrasado): `usar_ontem` — errei a estimativa disso há pouco, vou de último valor.
- 09:08 · Caio (líder de Dashboards): Tesouro Prefixado (% a.a.) (2 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.
- 09:10 · Caio (líder de Dashboards): Tesouro IPCA+ (% a.a. real) (2 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.

## Últimos eventos
- 2026-10-20 · extracao · INC-0015: falha real em BCB · SGS
- 2026-10-19 · extracao · INC-0014: falha real em Tesouro Direto (CSV)
- 2026-10-16 · extracao · INC-0013 resolvido: Yahoo Finance voltou após 3 dia(s) (corrigir_conector)
