# Briefing · fechamento de 2026-11-19

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-11-23.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.043688 · PL R$ 326,768,195 · dia -0.01% · 21d -2.34% vs CDI +1.07% · desde o início +4.37% vs CDI +3.32%
- Fluxo de cotistas no dia: R$ -1,276,336 · caixa da gestora R$ 2,054,385
- Alocação (atual → alvo): caixa 30.0%→35%, prefixado 16.1%→15%, inflacao 26.9%→25%, dolar 17.0%→15%, bolsa 10.0%→10%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 19.8/100 · equipe 3 · orçamento R$ 1,200/dia
- Nenhum incidente aberto.
- ⚠️ Falha REAL no conector `tesouro`: FonteIndisponivel: https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c: <urlopen error [Errno 104] Connection reset by peer> (corrigir em `gestora/fontes.py`)

## Dashboards
- Credibilidade 90% · confiança média 100%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-11-19 | 0 | — | 100% |
| selic | 13.75 | 2026-11-19 | 0 | — | 100% |
| dolar | 5.8889 | 2026-11-19 | 0 | — | 100% |
| ipca_12m | 4.63 | 2026-10-01 | 0 | — | 100% |
| focus_ipca | 5.1082 | 2026-11-13 | 0 | — | 100% |
| focus_selic | 13.75 | 2026-11-13 | 0 | — | 100% |
| ibov | 166376.0 | 2026-11-19 | 0 | — | 100% |
| bova11 | 163.6 | 2026-11-19 | 0 | — | 100% |
| taxa_pre | 15.04 | 2026-11-19 | 0 | — | 100% |
| taxa_ipca | 7.86 | 2026-11-19 | 0 | — | 100% |

## Alertas ativos
- nenhum

## Decisões dos times no último dia
- 08:02 · Bia (líder de Extração): INC-0019 · BCB · SGS (a fonte publicou atrasado, aberto ontem): `aguardar` — atraso costuma se resolver sozinho.

## Últimos eventos
- 2026-11-19 · extracao · INC-0019 resolvido: BCB · SGS voltou após 1 dia(s) (aguardar)
- 2026-11-18 · extracao · INC-0019: BCB · SGS — a fonte publicou atrasado
