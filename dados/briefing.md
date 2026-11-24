# Briefing · fechamento de 2026-11-23

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-11-24.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.045441 · PL R$ 326,335,302 · dia +0.17% · 21d -2.11% vs CDI +1.07% · desde o início +4.54% vs CDI +3.37%
- Fluxo de cotistas no dia: R$ -981,639 · caixa da gestora R$ 2,055,675
- Alocação (atual → alvo): caixa 35.0%→35%, prefixado 15.0%→15%, inflacao 25.0%→25%, dolar 15.0%→15%, bolsa 10.0%→10%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 19.8/100 · equipe 3 · orçamento R$ 1,200/dia
- **INC-0020** tesouro `falha_real` há 0 dia(s), ação `corrigir_conector` — FonteIndisponivel: https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c: <urlopen error [Errno 104] Connection reset by peer>
- ⚠️ Falha REAL no conector `tesouro`: FonteIndisponivel: https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c: <urlopen error [Errno 104] Connection reset by peer> (corrigir em `gestora/fontes.py`)

## Dashboards
- Credibilidade 90% · confiança média 100%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-11-23 | 0 | — | 100% |
| selic | 13.75 | 2026-11-23 | 0 | — | 100% |
| dolar | 5.9708 | 2026-11-23 | 0 | — | 100% |
| ipca_12m | 4.63 | 2026-10-01 | 0 | — | 100% |
| focus_ipca | 5.1505 | 2026-11-19 | 0 | — | 100% |
| focus_selic | 13.75 | 2026-11-19 | 0 | — | 100% |
| ibov | 164796.0 | 2026-11-23 | 0 | — | 100% |
| bova11 | 162.35 | 2026-11-23 | 0 | — | 100% |
| taxa_pre | 15.04 | 2026-11-19 | 0 | — | 100% |
| taxa_ipca | 7.86 | 2026-11-19 | 0 | — | 100% |

## Alertas ativos
- [alta] INC-0020 — INC-0020 · Tesouro Direto (CSV): o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 10:14 · Rafael (CIO): Carteira coerente com os números. Mantemos o alvo.

## Últimos eventos
- 2026-11-23 · extracao · INC-0020: falha real em Tesouro Direto (CSV)
- 2026-11-23 · fundo · Rebalanceamento: giro R$ 17,2 mi, custo R$ 8.620
- 2026-11-19 · extracao · INC-0019 resolvido: BCB · SGS voltou após 1 dia(s) (aguardar)
- 2026-11-18 · extracao · INC-0019: BCB · SGS — a fonte publicou atrasado
