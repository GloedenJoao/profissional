# Briefing · fechamento de 2026-11-26

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-11-27.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.048712 · PL R$ 323,716,818 · dia +0.31% · 21d +2.02% vs CDI +1.07% · desde o início +4.87% vs CDI +3.53%
- Fluxo de cotistas no dia: R$ 1,042,497 · caixa da gestora R$ 2,059,151
- Alocação (atual → alvo): caixa 30.0%→30%, prefixado 15.0%→15%, inflacao 25.0%→25%, dolar 15.0%→15%, bolsa 15.0%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 19.6/100 · equipe 3 · orçamento R$ 1,200/dia
- **INC-0022** b3 `fora_do_ar` há 0 dia(s), ação `fonte_alternativa` — a fonte saiu do ar
- **INC-0021** tesouro `falha_real` há 0 dia(s), ação `corrigir_conector` — FonteIndisponivel: https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c: <urlopen error [Errno 104] Connection reset by peer>
- ⚠️ Falha REAL no conector `tesouro`: FonteIndisponivel: https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c: <urlopen error [Errno 104] Connection reset by peer> (corrigir em `gestora/fontes.py`)

## Dashboards
- Credibilidade 90% · confiança média 100%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-11-26 | 0 | — | 100% |
| selic | 13.75 | 2026-11-26 | 0 | — | 100% |
| dolar | 5.7446 | 2026-11-26 | 0 | — | 100% |
| ipca_12m | 4.63 | 2026-10-01 | 0 | — | 100% |
| focus_ipca | 5.1505 | 2026-11-19 | 0 | — | 100% |
| focus_selic | 13.75 | 2026-11-19 | 0 | — | 100% |
| ibov | 176800.0 | 2026-11-26 | 0 | — | 100% |
| bova11 | 174.49 | 2026-11-26 | 0 | — | 100% |
| taxa_pre | 14.89 | 2026-11-25 | 0 | — | 100% |
| taxa_ipca | 7.87 | 2026-11-25 | 0 | — | 100% |

## Alertas ativos
- [alta] INC-0021 — INC-0021 · Tesouro Direto (CSV): o conector falhou de verdade nesta extração
- [media] INC-0022 — INC-0022 · B3 · COTAHIST: a fonte saiu do ar

## Decisões dos times no último dia
- 10:12 · Rafael (CIO): Decidido: Ações (BOVA11) +5 p.p. (tendência de +0,9% em 20 pregões). Caixa fica em 30%.

## Últimos eventos
- 2026-11-26 · extracao · INC-0021: falha real em Tesouro Direto (CSV)
- 2026-11-26 · extracao · INC-0022: B3 · COTAHIST — a fonte saiu do ar
- 2026-11-26 · fundo · Rebalanceamento: giro R$ 14,9 mi, custo R$ 7.474
- 2026-11-25 · extracao · INC-0020 resolvido: Tesouro Direto (CSV) voltou após 2 dia(s) (corrigir_conector)
- 2026-11-23 · extracao · INC-0020: falha real em Tesouro Direto (CSV)
- 2026-11-23 · fundo · Rebalanceamento: giro R$ 17,2 mi, custo R$ 8.620
- 2026-11-19 · extracao · INC-0019 resolvido: BCB · SGS voltou após 1 dia(s) (aguardar)
