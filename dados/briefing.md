# Briefing · fechamento de 2026-10-05

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-06.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.063501 · PL R$ 339,918,090 · dia +2.18% · 21d +3.97% vs CDI +1.08% · desde o início +6.35% vs CDI +1.71%
- Fluxo de cotistas no dia: R$ 2,233,968 · caixa da gestora R$ 2,033,907
- Alocação (atual → alvo): caixa 39.6%→40%, prefixado 14.9%→15%, inflacao 20.6%→20%, dolar 9.3%→10%, bolsa 15.7%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 27.6/100 · equipe 3 · orçamento R$ 1,200/dia
- **INC-0009** yahoo `falha_real` há 0 dia(s), ação `corrigir_conector` — série bova11 parada em 2026-10-02 (esperado 2026-10-05)
- **INC-0008** bcb_sgs `falha_real` há 1 dia(s), ação `corrigir_conector` — série cdi parada em 2026-10-01 (esperado 2026-10-02)
- ⚠️ Falha REAL no conector `bcb_sgs`: JSONDecodeError: Expecting value: line 1 column 1 (char 0) (corrigir em `gestora/fontes.py`)

## Dashboards
- Credibilidade 93% · confiança média 80%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-01 | 2 | estimar | 60% |
| selic | 13.75 | 2026-10-01 | 2 | usar_ontem | 60% |
| dolar | 5.2079 | 2026-10-01 | 2 | usar_ontem | 60% |
| ipca_12m | 4.22 | 2026-08-01 | 0 | — | 100% |
| focus_ipca | 5.0129 | 2026-10-02 | 0 | — | 100% |
| focus_selic | 13.5 | 2026-10-02 | 0 | — | 100% |
| ibov | 193890.8007 | 2026-10-02 | 1 | estimar | 60% |
| bova11 | 191.8912 | 2026-10-02 | 1 | estimar | 60% |
| taxa_pre | 12.74 | 2026-10-05 | 0 | — | 100% |
| taxa_ipca | 6.86 | 2026-10-05 | 0 | — | 100% |

## Alertas ativos
- [alta] INC-0008 — INC-0008 · BCB · SGS: o conector falhou de verdade nesta extração
- [alta] INC-0009 — INC-0009 · Yahoo Finance: o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 08:02 · Téo (engenheiro de plantão): INC-0008 · BCB · SGS (o conector falhou de verdade nesta extração, aberto ontem): `corrigir_conector` — falha real no conector: só resolve mexendo no código.
- 09:02 · Lia (analista de dados): CDI (% a.a.) (2 dia(s) atrasado): `estimar` — o CDI acompanha a Selic, dá para estimar com folga.
- 09:04 · Caio (líder de Dashboards): Selic meta (% a.a.) (2 dia(s) atrasado): `usar_ontem` — número que muda devagar; repetir o último é seguro.
- 09:06 · Caio (líder de Dashboards): Dólar PTAX (R$) (2 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.
- 09:08 · Lia (analista de dados): Ibovespa (pts) (1 dia(s) atrasado): `estimar` — só um dia de atraso; estimo pela tendência da última semana.
- 09:10 · Lia (analista de dados): BOVA11 (R$) (1 dia(s) atrasado): `estimar` — só um dia de atraso; estimo pela tendência da última semana.
- 10:10 · Rafael (CIO): Carteira coerente com os números. Mantemos o alvo.

## Últimos eventos
- 2026-10-05 · extracao · INC-0009: falha real em Yahoo Finance
- 2026-10-02 · extracao · INC-0006 resolvido: BCB · PTAX (Olinda) voltou após 1 dia(s) (aguardar)
- 2026-10-02 · extracao · INC-0007 resolvido: Yahoo Finance voltou após 1 dia(s) (corrigir_conector)
- 2026-10-02 · extracao · INC-0008: falha real em BCB · SGS
- 2026-10-02 · fundo · Rebalanceamento: giro R$ 17,6 mi, custo R$ 8.781
- 2026-10-01 · extracao · INC-0006: BCB · PTAX (Olinda) — a fonte publicou atrasado
- 2026-10-01 · extracao · INC-0007: falha real em Yahoo Finance
- 2026-10-01 · fundo · Rebalanceamento: giro R$ 24,9 mi, custo R$ 12.458
