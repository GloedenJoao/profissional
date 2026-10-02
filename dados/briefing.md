# Briefing · fechamento de 2026-10-01

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-02.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.035250 · PL R$ 328,978,234 · dia -0.07% · 21d +1.97% vs CDI +1.08% · desde o início +3.52% vs CDI +1.60%
- Fluxo de cotistas no dia: R$ 1,677,814 · caixa da gestora R$ 2,030,781
- Alocação (atual → alvo): caixa 40.0%→40%, prefixado 20.0%→20%, inflacao 15.0%→15%, dolar 10.0%→10%, bolsa 15.0%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 27.1/100 · equipe 3 · orçamento R$ 1,200/dia
- **INC-0007** yahoo `falha_real` há 0 dia(s), ação `corrigir_conector` — série bova11 parada em 2026-09-30 (esperado 2026-10-01)
- **INC-0006** bcb_ptax `atraso` há 0 dia(s), ação `aguardar` — a fonte publicou atrasado

## Dashboards
- Credibilidade 91% · confiança média 92%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-01 | 0 | — | 100% |
| selic | 13.75 | 2026-10-01 | 0 | — | 100% |
| dolar | 5.2079 | 2026-10-01 | 0 | — | 100% |
| ipca_12m | 4.22 | 2026-08-01 | 0 | — | 100% |
| focus_ipca | 4.9915 | 2026-09-25 | 0 | — | 100% |
| focus_selic | 13.5 | 2026-09-25 | 0 | — | 100% |
| ibov | 186445.3785 | 2026-09-30 | 1 | estimar | 60% |
| bova11 | 184.325 | 2026-09-30 | 1 | estimar | 60% |
| taxa_pre | 13.86 | 2026-10-01 | 0 | — | 100% |
| taxa_ipca | 7.56 | 2026-10-01 | 0 | — | 100% |

## Alertas ativos
- [media] INC-0006 — INC-0006 · BCB · PTAX (Olinda): a fonte publicou atrasado
- [alta] INC-0007 — INC-0007 · Yahoo Finance: o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 09:02 · Lia (analista de dados): Ibovespa (pts) (1 dia(s) atrasado): `estimar` — só um dia de atraso; estimo pela tendência da última semana.
- 09:04 · Lia (analista de dados): BOVA11 (R$) (1 dia(s) atrasado): `estimar` — só um dia de atraso; estimo pela tendência da última semana.
- 10:04 · Conselho (diretriz de agente): Alocação definida pelo conselho: Caixa (CDI) 40%, Tesouro Prefixado 20%, Tesouro IPCA+ 15%, Dólar 10%, Ações (BOVA11) 15%.
- 10:06 · Conselho (diretriz de agente): Equipe de Extração 3, orçamento R$ 1.200/dia.

## Últimos eventos
- 2026-10-01 · extracao · INC-0006: BCB · PTAX (Olinda) — a fonte publicou atrasado
- 2026-10-01 · extracao · INC-0007: falha real em Yahoo Finance
- 2026-10-01 · fundo · Rebalanceamento: giro R$ 24,9 mi, custo R$ 12.458
