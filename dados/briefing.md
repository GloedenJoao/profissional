# Briefing · fechamento de 2026-11-24

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-11-25.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.042050 · PL R$ 323,070,468 · dia -0.32% · 21d -2.28% vs CDI +1.07% · desde o início +4.21% vs CDI +3.43%
- Fluxo de cotistas no dia: R$ -2,206,563 · caixa da gestora R$ 2,056,883
- Alocação (atual → alvo): caixa 34.7%→35%, prefixado 15.2%→15%, inflacao 25.3%→25%, dolar 14.9%→15%, bolsa 10.0%→10%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 19.7/100 · equipe 3 · orçamento R$ 1,200/dia
- **INC-0020** tesouro `falha_real` há 1 dia(s), ação `corrigir_conector` — FonteIndisponivel: https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c: <urlopen error [Errno 104] Connection reset by peer>
- ⚠️ Falha REAL no conector `tesouro`: FonteIndisponivel: https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c: <urlopen error [Errno 104] Connection reset by peer> (corrigir em `gestora/fontes.py`)

## Dashboards
- Credibilidade 90% · confiança média 96%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-11-24 | 0 | — | 100% |
| selic | 13.75 | 2026-11-24 | 0 | — | 100% |
| dolar | 5.8573 | 2026-11-24 | 0 | — | 100% |
| ipca_12m | 4.63 | 2026-10-01 | 0 | — | 100% |
| focus_ipca | 5.1505 | 2026-11-19 | 0 | — | 100% |
| focus_selic | 13.75 | 2026-11-19 | 0 | — | 100% |
| ibov | 164090.0 | 2026-11-24 | 0 | — | 100% |
| bova11 | 161.49 | 2026-11-24 | 0 | — | 100% |
| taxa_pre | 15.04 | 2026-11-19 | 1 | usar_ontem | 80% |
| taxa_ipca | 7.86 | 2026-11-19 | 1 | usar_ontem | 80% |

## Alertas ativos
- [alta] INC-0020 — INC-0020 · Tesouro Direto (CSV): o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 08:02 · Téo (engenheiro de plantão): INC-0020 · Tesouro Direto (CSV) (o conector falhou de verdade nesta extração, aberto ontem): `corrigir_conector` — falha real no conector: só resolve mexendo no código.
- 09:02 · Caio (líder de Dashboards): Tesouro Prefixado (% a.a.) (1 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.
- 09:04 · Caio (líder de Dashboards): Tesouro IPCA+ (% a.a. real) (1 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.

## Últimos eventos
- 2026-11-23 · extracao · INC-0020: falha real em Tesouro Direto (CSV)
- 2026-11-23 · fundo · Rebalanceamento: giro R$ 17,2 mi, custo R$ 8.620
- 2026-11-19 · extracao · INC-0019 resolvido: BCB · SGS voltou após 1 dia(s) (aguardar)
- 2026-11-18 · extracao · INC-0019: BCB · SGS — a fonte publicou atrasado
