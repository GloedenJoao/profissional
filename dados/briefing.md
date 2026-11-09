# Briefing · fechamento de 2026-11-06

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-11-09.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.031668 · PL R$ 337,158,118 · dia +0.50% · 21d -2.82% vs CDI +1.07% · desde o início +3.17% vs CDI +2.85%
- Fluxo de cotistas no dia: R$ -1,518,759 · caixa da gestora R$ 2,049,221
- Alocação (atual → alvo): caixa 33.2%→35%, prefixado 15.6%→15%, inflacao 26.0%→25%, dolar 15.4%→15%, bolsa 9.9%→10%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%
- Congelados (sem número confiável): dolar

## Extração
- Dívida técnica 25.1/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0018** bcb_sgs `atraso` há 1 dia(s), ação `aguardar` — a fonte publicou atrasado

## Dashboards
- Credibilidade 83% · confiança média 80%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-11-03 | 3 | estimar | 60% |
| selic | 13.75 | 2026-11-03 | 3 | usar_ontem | 40% |
| dolar | — | 2026-11-03 | 3 | suspender | 0% |
| ipca_12m | 4.58 | 2026-09-01 | 0 | — | 100% |
| focus_ipca | 5.2195 | 2026-11-06 | 0 | — | 100% |
| focus_selic | 13.75 | 2026-11-06 | 0 | — | 100% |
| ibov | 168499.0 | 2026-11-06 | 0 | — | 100% |
| bova11 | 165.93 | 2026-11-06 | 0 | — | 100% |
| taxa_pre | 14.78 | 2026-11-06 | 0 | — | 100% |
| taxa_ipca | 7.87 | 2026-11-06 | 0 | — | 100% |

## Alertas ativos
- [media] DEFAS-cdi — Painel: CDI (% a.a.) defasado
- [media] DEFAS-dolar — Painel: Dólar PTAX (R$) defasado
- [media] DEFAS-selic — Painel: Selic meta (% a.a.) defasado
- [media] INC-0018 — INC-0018 · BCB · SGS: a fonte publicou atrasado

## Decisões dos times no último dia
- 08:02 · Bia (líder de Extração): INC-0018 · BCB · SGS (a fonte publicou atrasado, aberto ontem): `aguardar` — atraso costuma se resolver sozinho.
- 09:02 · Lia (analista de dados): CDI (% a.a.) (3 dia(s) atrasado): `estimar` — o CDI acompanha a Selic, dá para estimar com folga.
- 09:04 · Caio (líder de Dashboards): Selic meta (% a.a.) (3 dia(s) atrasado): `usar_ontem` — número que muda devagar; repetir o último é seguro.
- 09:06 · Caio (líder de Dashboards): Dólar PTAX (R$) (3 dia(s) atrasado): `suspender` — 3 dias sem dado: prefiro não publicar a induzir o comitê ao erro.

## Últimos eventos
- 2026-11-05 · extracao · INC-0016 resolvido: BCB · SGS voltou após 1 dia(s) (corrigir_conector)
- 2026-11-05 · extracao · INC-0017 resolvido: Tesouro Direto (CSV) voltou após 1 dia(s) (corrigir_conector)
- 2026-11-05 · extracao · INC-0018: BCB · SGS — a fonte publicou atrasado
- 2026-11-04 · extracao · INC-0016: falha real em BCB · SGS
- 2026-11-04 · extracao · INC-0017: falha real em Tesouro Direto (CSV)
