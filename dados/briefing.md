# Briefing · fechamento de 2026-11-09

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-11-10.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.037442 · PL R$ 338,107,824 · dia +0.56% · 21d -2.21% vs CDI +1.07% · desde o início +3.74% vs CDI +2.90%
- Fluxo de cotistas no dia: R$ -937,279 · caixa da gestora R$ 2,049,475
- Alocação (atual → alvo): caixa 32.9%→35%, prefixado 15.6%→15%, inflacao 26.2%→25%, dolar 15.3%→15%, bolsa 10.0%→10%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 25.1/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0018** bcb_sgs `atraso` há 2 dia(s), ação `fonte_alternativa` — a fonte publicou atrasado

## Dashboards
- Credibilidade 84% · confiança média 87%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-11-03 | 4 | estimar | 60% |
| selic | 13.75 | 2026-11-03 | 4 | usar_ontem | 20% |
| dolar | 5.5146 | 2026-11-09 | 0 | — | 90% |
| ipca_12m | 4.58 | 2026-09-01 | 0 | — | 100% |
| focus_ipca | 5.2195 | 2026-11-06 | 0 | — | 100% |
| focus_selic | 13.75 | 2026-11-06 | 0 | — | 100% |
| ibov | 172236.0 | 2026-11-09 | 0 | — | 100% |
| bova11 | 169.67 | 2026-11-09 | 0 | — | 100% |
| taxa_pre | 14.71 | 2026-11-09 | 0 | — | 100% |
| taxa_ipca | 7.75 | 2026-11-09 | 0 | — | 100% |

## Alertas ativos
- [media] DEFAS-cdi — Painel: CDI (% a.a.) defasado
- [media] DEFAS-selic — Painel: Selic meta (% a.a.) defasado
- [media] INC-0018 — INC-0018 · BCB · SGS: a fonte publicou atrasado

## Decisões dos times no último dia
- 08:02 · Bia (líder de Extração): INC-0018 · BCB · SGS (a fonte publicou atrasado, aberto ontem): `fonte_alternativa` — o atraso passou de um dia: liga a alternativa.
- 09:02 · Lia (analista de dados): CDI (% a.a.) (4 dia(s) atrasado): `estimar` — o CDI acompanha a Selic, dá para estimar com folga.
- 09:04 · Caio (líder de Dashboards): Selic meta (% a.a.) (4 dia(s) atrasado): `usar_ontem` — número que muda devagar; repetir o último é seguro.
- 10:14 · Rafael (CIO): Carteira coerente com os números. Mantemos o alvo.

## Últimos eventos
- 2026-11-05 · extracao · INC-0016 resolvido: BCB · SGS voltou após 1 dia(s) (corrigir_conector)
- 2026-11-05 · extracao · INC-0017 resolvido: Tesouro Direto (CSV) voltou após 1 dia(s) (corrigir_conector)
- 2026-11-05 · extracao · INC-0018: BCB · SGS — a fonte publicou atrasado
- 2026-11-04 · extracao · INC-0016: falha real em BCB · SGS
- 2026-11-04 · extracao · INC-0017: falha real em Tesouro Direto (CSV)
