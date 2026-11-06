# Briefing · fechamento de 2026-11-05

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-11-06.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.026521 · PL R$ 336,987,232 · dia -0.21% · 21d -3.48% vs CDI +1.07% · desde o início +2.65% vs CDI +2.80%
- Fluxo de cotistas no dia: R$ -2,089,141 · caixa da gestora R$ 2,048,981
- Alocação (atual → alvo): caixa 33.7%→35%, prefixado 15.6%→15%, inflacao 25.8%→25%, dolar 15.3%→15%, bolsa 9.7%→10%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 25.2/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0018** bcb_sgs `atraso` há 0 dia(s), ação `aguardar` — a fonte publicou atrasado

## Dashboards
- Credibilidade 83% · confiança média 88%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-11-03 | 2 | estimar | 60% |
| selic | 13.75 | 2026-11-03 | 2 | usar_ontem | 60% |
| dolar | 5.4935 | 2026-11-03 | 2 | usar_ontem | 60% |
| ipca_12m | 4.58 | 2026-09-01 | 0 | — | 100% |
| focus_ipca | 5.2166 | 2026-10-30 | 0 | — | 100% |
| focus_selic | 13.5 | 2026-10-30 | 0 | — | 100% |
| ibov | 166192.0 | 2026-11-05 | 0 | — | 100% |
| bova11 | 163.03 | 2026-11-05 | 0 | — | 100% |
| taxa_pre | 14.94 | 2026-11-05 | 0 | — | 100% |
| taxa_ipca | 7.94 | 2026-11-05 | 0 | — | 100% |

## Alertas ativos
- [media] INC-0018 — INC-0018 · BCB · SGS: a fonte publicou atrasado

## Decisões dos times no último dia
- 08:02 · Téo (engenheiro de plantão): INC-0016 · BCB · SGS (o conector falhou de verdade nesta extração, aberto ontem): `corrigir_conector` — falha real no conector: só resolve mexendo no código.
- 08:04 · Téo (engenheiro de plantão): INC-0017 · Tesouro Direto (CSV) (o conector falhou de verdade nesta extração, aberto ontem): `corrigir_conector` — falha real no conector: só resolve mexendo no código.
- 09:02 · Lia (analista de dados): CDI (% a.a.) (2 dia(s) atrasado): `estimar` — o CDI acompanha a Selic, dá para estimar com folga.
- 09:04 · Caio (líder de Dashboards): Selic meta (% a.a.) (2 dia(s) atrasado): `usar_ontem` — número que muda devagar; repetir o último é seguro.
- 09:06 · Caio (líder de Dashboards): Dólar PTAX (R$) (2 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.

## Últimos eventos
- 2026-11-05 · extracao · INC-0016 resolvido: BCB · SGS voltou após 1 dia(s) (corrigir_conector)
- 2026-11-05 · extracao · INC-0017 resolvido: Tesouro Direto (CSV) voltou após 1 dia(s) (corrigir_conector)
- 2026-11-05 · extracao · INC-0018: BCB · SGS — a fonte publicou atrasado
- 2026-11-04 · extracao · INC-0016: falha real em BCB · SGS
- 2026-11-04 · extracao · INC-0017: falha real em Tesouro Direto (CSV)
