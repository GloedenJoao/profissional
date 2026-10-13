# Briefing · fechamento de 2026-10-09

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-13.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.070965 · PL R$ 348,177,539 · dia +0.59% · 21d +4.19% vs CDI +1.08% · desde o início +7.10% vs CDI +1.91%
- Fluxo de cotistas no dia: R$ 1,643,104 · caixa da gestora R$ 2,038,454
- Alocação (atual → alvo): caixa 40.4%→40%, prefixado 14.7%→15%, inflacao 20.5%→20%, dolar 9.1%→10%, bolsa 15.4%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%
- Congelados (sem número confiável): dolar

## Extração
- Dívida técnica 30.2/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0010** bcb_sgs `falha_real` há 2 dia(s), ação `corrigir_conector` — JSONDecodeError: Expecting value: line 1 column 1 (char 0)

## Dashboards
- Credibilidade 85% · confiança média 80%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-06 | 3 | estimar | 60% |
| selic | 13.75 | 2026-10-06 | 3 | usar_ontem | 40% |
| dolar | — | 2026-10-06 | 3 | suspender | 0% |
| ipca_12m | 4.22 | 2026-08-01 | 0 | — | 100% |
| focus_ipca | 5.0129 | 2026-10-02 | 0 | — | 100% |
| focus_selic | 13.5 | 2026-10-02 | 0 | — | 100% |
| ibov | 209067.0 | 2026-10-09 | 0 | — | 100% |
| bova11 | 205.55 | 2026-10-09 | 0 | — | 100% |
| taxa_pre | 12.3 | 2026-10-09 | 0 | — | 100% |
| taxa_ipca | 6.66 | 2026-10-09 | 0 | — | 100% |

## Alertas ativos
- [media] DEFAS-cdi — Painel: CDI (% a.a.) defasado
- [media] DEFAS-dolar — Painel: Dólar PTAX (R$) defasado
- [media] DEFAS-selic — Painel: Selic meta (% a.a.) defasado
- [media] ERRO-bova11-2026-10-05 — Painel errou BOVA11 (R$) de 2026-10-05
- [media] ERRO-ibov-2026-10-05 — Painel errou Ibovespa (pts) de 2026-10-05
- [alta] INC-0010 — INC-0010 · BCB · SGS: o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 08:04 · Téo (engenheiro de plantão): INC-0009 · Yahoo Finance (o conector falhou de verdade nesta extração, aberto há 3 dias): `corrigir_conector` — falha real no conector: só resolve mexendo no código.
- 08:08 · Bia (líder de Extração): INC-0011 · BCB · PTAX (Olinda) (o conector falhou de verdade nesta extração, aberto ontem): `escalar` — falta equipe.
- 08:12 · Bia (líder de Extração): INC-0012 · BCB · Focus (Olinda) (o conector falhou de verdade nesta extração, aberto ontem): `escalar` — falta equipe.
- 09:02 · Lia (analista de dados): CDI (% a.a.) (3 dia(s) atrasado): `estimar` — o CDI acompanha a Selic, dá para estimar com folga.
- 09:04 · Caio (líder de Dashboards): Selic meta (% a.a.) (3 dia(s) atrasado): `usar_ontem` — número que muda devagar; repetir o último é seguro.
- 09:06 · Caio (líder de Dashboards): Dólar PTAX (R$) (3 dia(s) atrasado): `suspender` — 3 dias sem dado: prefiro não publicar a induzir o comitê ao erro.

## Últimos eventos
- 2026-10-09 · extracao · INC-0009 resolvido: Yahoo Finance voltou após 4 dia(s) (corrigir_conector)
- 2026-10-09 · extracao · INC-0011 resolvido: BCB · PTAX (Olinda) voltou após 1 dia(s) (escalar)
- 2026-10-09 · extracao · INC-0012 resolvido: BCB · Focus (Olinda) voltou após 1 dia(s) (escalar)
- 2026-10-09 · dashboards · Estimativa errada de ibov em 2026-10-05: 193890.8007 vs real 206912.0
- 2026-10-08 · extracao · INC-0011: falha real em BCB · PTAX (Olinda)
- 2026-10-08 · extracao · INC-0012: falha real em BCB · Focus (Olinda)
- 2026-10-07 · extracao · INC-0010: falha real em BCB · SGS
- 2026-10-06 · extracao · INC-0008 resolvido: BCB · SGS voltou após 2 dia(s) (corrigir_conector)
- 2026-10-06 · dashboards · Estimativa errada de bova11 em 2026-10-05: 191.8912 vs real 204.35
- 2026-10-05 · extracao · INC-0009: falha real em Yahoo Finance
