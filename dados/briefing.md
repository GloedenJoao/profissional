# Briefing · fechamento de 2026-10-07

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-08.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.060870 · PL R$ 341,775,962 · dia -0.07% · 21d +3.29% vs CDI +1.08% · desde o início +6.09% vs CDI +1.81%
- Fluxo de cotistas no dia: R$ 1,143,882 · caixa da gestora R$ 2,037,490
- Alocação (atual → alvo): caixa 40.2%→40%, prefixado 14.9%→15%, inflacao 20.3%→20%, dolar 9.2%→10%, bolsa 15.4%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%
- Congelados (sem número confiável): bolsa

## Extração
- Dívida técnica 28.2/100 · equipe 3 · orçamento R$ 1,200/dia
- **INC-0010** bcb_sgs `falha_real` há 0 dia(s), ação `corrigir_conector` — JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- **INC-0009** yahoo `falha_real` há 2 dia(s), ação `corrigir_conector` — série bova11 parada em 2026-10-02 (esperado 2026-10-05)
- ⚠️ Falha REAL no conector `bcb_sgs`: JSONDecodeError: Expecting value: line 1 column 1 (char 0) (corrigir em `gestora/fontes.py`)

## Dashboards
- Credibilidade 90% · confiança média 74%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-06 | 1 | estimar | 60% |
| selic | 13.75 | 2026-10-06 | 1 | usar_ontem | 80% |
| dolar | 4.9211 | 2026-10-06 | 1 | estimar | 60% |
| ipca_12m | 4.22 | 2026-08-01 | 0 | — | 100% |
| focus_ipca | 5.0129 | 2026-10-02 | 0 | — | 100% |
| focus_selic | 13.5 | 2026-10-02 | 0 | — | 100% |
| ibov | 192115.0 | 2026-10-02 | 3 | usar_ontem | 40% |
| bova11 | — | 2026-10-02 | 3 | suspender | 0% |
| taxa_pre | 12.55 | 2026-10-07 | 0 | — | 100% |
| taxa_ipca | 6.95 | 2026-10-07 | 0 | — | 100% |

## Alertas ativos
- [media] DEFAS-bova11 — Painel: BOVA11 (R$) defasado
- [media] DEFAS-ibov — Painel: Ibovespa (pts) defasado
- [media] ERRO-bova11-2026-10-05 — Painel errou BOVA11 (R$) de 2026-10-05
- [alta] INC-0009 — INC-0009 · Yahoo Finance: o conector falhou de verdade nesta extração
- [alta] INC-0010 — INC-0010 · BCB · SGS: o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 08:02 · Téo (engenheiro de plantão): INC-0009 · Yahoo Finance (o conector falhou de verdade nesta extração, aberto ontem): `corrigir_conector` — falha real no conector: só resolve mexendo no código.
- 09:02 · Lia (analista de dados): CDI (% a.a.) (1 dia(s) atrasado): `estimar` — o CDI acompanha a Selic, dá para estimar com folga.
- 09:04 · Caio (líder de Dashboards): Selic meta (% a.a.) (1 dia(s) atrasado): `usar_ontem` — número que muda devagar; repetir o último é seguro.
- 09:06 · Lia (analista de dados): Dólar PTAX (R$) (1 dia(s) atrasado): `estimar` — só um dia de atraso; estimo pela tendência da última semana.
- 09:08 · Caio (líder de Dashboards): Ibovespa (pts) (3 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.
- 09:10 · Caio (líder de Dashboards): BOVA11 (R$) (3 dia(s) atrasado): `suspender` — 3 dias sem dado: prefiro não publicar a induzir o comitê ao erro.

## Últimos eventos
- 2026-10-07 · extracao · INC-0010: falha real em BCB · SGS
- 2026-10-06 · extracao · INC-0008 resolvido: BCB · SGS voltou após 2 dia(s) (corrigir_conector)
- 2026-10-06 · dashboards · Estimativa errada de bova11 em 2026-10-05: 191.8912 vs real 204.35
- 2026-10-05 · extracao · INC-0009: falha real em Yahoo Finance
- 2026-10-02 · extracao · INC-0006 resolvido: BCB · PTAX (Olinda) voltou após 1 dia(s) (aguardar)
- 2026-10-02 · extracao · INC-0007 resolvido: Yahoo Finance voltou após 1 dia(s) (corrigir_conector)
- 2026-10-02 · extracao · INC-0008: falha real em BCB · SGS
- 2026-10-02 · fundo · Rebalanceamento: giro R$ 17,6 mi, custo R$ 8.781
- 2026-10-01 · extracao · INC-0006: BCB · PTAX (Olinda) — a fonte publicou atrasado
- 2026-10-01 · extracao · INC-0007: falha real em Yahoo Finance
- 2026-10-01 · fundo · Rebalanceamento: giro R$ 24,9 mi, custo R$ 12.458
