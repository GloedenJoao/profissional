# Briefing · fechamento de 2026-10-06

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-07.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.061577 · PL R$ 340,859,145 · dia -0.18% · 21d +3.67% vs CDI +1.08% · desde o início +6.16% vs CDI +1.76%
- Fluxo de cotistas no dia: R$ 1,556,040 · caixa da gestora R$ 2,035,672
- Alocação (atual → alvo): caixa 39.9%→40%, prefixado 14.9%→15%, inflacao 20.4%→20%, dolar 9.2%→10%, bolsa 15.5%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 27.6/100 · equipe 3 · orçamento R$ 1,200/dia
- **INC-0009** yahoo `falha_real` há 1 dia(s), ação `fonte_alternativa` — série bova11 parada em 2026-10-02 (esperado 2026-10-05)

## Dashboards
- Credibilidade 91% · confiança média 95%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-06 | 0 | — | 100% |
| selic | 13.75 | 2026-10-06 | 0 | — | 100% |
| dolar | 4.9698 | 2026-10-06 | 0 | — | 100% |
| ipca_12m | 4.22 | 2026-08-01 | 0 | — | 100% |
| focus_ipca | 5.0129 | 2026-10-02 | 0 | — | 100% |
| focus_selic | 13.5 | 2026-10-02 | 0 | — | 100% |
| ibov | 192115.0 | 2026-10-02 | 2 | usar_ontem | 60% |
| bova11 | 202.5 | 2026-10-06 | 0 | — | 90% |
| taxa_pre | 12.55 | 2026-10-06 | 0 | — | 100% |
| taxa_ipca | 6.92 | 2026-10-06 | 0 | — | 100% |

## Alertas ativos
- [media] ERRO-bova11-2026-10-05 — Painel errou BOVA11 (R$) de 2026-10-05
- [alta] INC-0009 — INC-0009 · Yahoo Finance: o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 08:04 · Bia (líder de Extração): INC-0009 · Yahoo Finance (o conector falhou de verdade nesta extração, aberto ontem): `fonte_alternativa` — não tenho gente para corrigir agora; seguro com a alternativa.
- 09:02 · Caio (líder de Dashboards): Ibovespa (pts) (2 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.

## Últimos eventos
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
