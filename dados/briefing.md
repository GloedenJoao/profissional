# Briefing · fechamento de 2026-10-08

Os times decidem sozinhos. Diretriz do conselho (opcional): `empresa/decisoes/2026-10-09.json` vale por cima deles nesse dia.

## Fundo
- Cota 1.064673 · PL R$ 344,498,351 · dia +0.36% · 21d +3.77% vs CDI +1.08% · desde o início +6.47% vs CDI +1.86%
- Fluxo de cotistas no dia: R$ 1,497,213 · caixa da gestora R$ 2,037,902
- Alocação (atual → alvo): caixa 40.3%→40%, prefixado 14.8%→15%, inflacao 20.4%→20%, dolar 9.2%→10%, bolsa 15.4%→15%
- Limites: caixa 10%–100%, prefixado 0%–40%, inflacao 0%–40%, dolar 0%–20%, bolsa 0%–30%

## Extração
- Dívida técnica 30.3/100 · equipe 4 · orçamento R$ 1,200/dia
- **INC-0012** bcb_focus `falha_real` há 0 dia(s), ação `corrigir_conector` — FonteIndisponivel: https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais?%24filter=%28Indicador%2: HTTP Error 403: Forbidden
- **INC-0011** bcb_ptax `falha_real` há 0 dia(s), ação `corrigir_conector` — FonteIndisponivel: https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCota: HTTP Error 403: Forbidden
- **INC-0010** bcb_sgs `falha_real` há 1 dia(s), ação `corrigir_conector` — JSONDecodeError: Expecting value: line 1 column 1 (char 0)
- **INC-0009** yahoo `falha_real` há 3 dia(s), ação `fonte_alternativa` — série bova11 parada em 2026-10-02 (esperado 2026-10-05)
- ⚠️ Falha REAL no conector `bcb_sgs`: JSONDecodeError: Expecting value: line 1 column 1 (char 0) (corrigir em `gestora/fontes.py`)
- ⚠️ Falha REAL no conector `bcb_ptax`: FonteIndisponivel: https://olinda.bcb.gov.br/olinda/servico/PTAX/versao/v1/odata/CotacaoDolarPeriodo(dataInicial=@dataInicial,dataFinalCota: HTTP Error 403: Forbidden (corrigir em `gestora/fontes.py`)
- ⚠️ Falha REAL no conector `bcb_focus`: FonteIndisponivel: https://olinda.bcb.gov.br/olinda/servico/Expectativas/versao/v1/odata/ExpectativasMercadoAnuais?%24filter=%28Indicador%2: HTTP Error 403: Forbidden (corrigir em `gestora/fontes.py`)

## Dashboards
- Credibilidade 90% · confiança média 79%

| indicador | valor | ref | defasagem | estratégia | confiança |
|---|---|---|---|---|---|
| cdi | 13.65 | 2026-10-06 | 2 | estimar | 60% |
| selic | 13.75 | 2026-10-06 | 2 | usar_ontem | 60% |
| dolar | 4.9698 | 2026-10-06 | 2 | usar_ontem | 60% |
| ipca_12m | 4.22 | 2026-08-01 | 0 | — | 100% |
| focus_ipca | 5.0129 | 2026-10-02 | 0 | — | 100% |
| focus_selic | 13.5 | 2026-10-02 | 0 | — | 100% |
| ibov | 192115.0 | 2026-10-02 | 4 | usar_ontem | 20% |
| bova11 | 203.08 | 2026-10-08 | 0 | — | 90% |
| taxa_pre | 12.53 | 2026-10-08 | 0 | — | 100% |
| taxa_ipca | 6.84 | 2026-10-08 | 0 | — | 100% |

## Alertas ativos
- [media] DEFAS-ibov — Painel: Ibovespa (pts) defasado
- [media] ERRO-bova11-2026-10-05 — Painel errou BOVA11 (R$) de 2026-10-05
- [alta] INC-0009 — INC-0009 · Yahoo Finance: o conector falhou de verdade nesta extração
- [alta] INC-0010 — INC-0010 · BCB · SGS: o conector falhou de verdade nesta extração
- [alta] INC-0011 — INC-0011 · BCB · PTAX (Olinda): o conector falhou de verdade nesta extração
- [alta] INC-0012 — INC-0012 · BCB · Focus (Olinda): o conector falhou de verdade nesta extração

## Decisões dos times no último dia
- 08:02 · Téo (engenheiro de plantão): INC-0010 · BCB · SGS (o conector falhou de verdade nesta extração, aberto ontem): `corrigir_conector` — falha real no conector: só resolve mexendo no código.
- 08:04 · Bia (líder de Extração): INC-0009 · Yahoo Finance (o conector falhou de verdade nesta extração, aberto há 2 dias): `fonte_alternativa` — não tenho gente para corrigir agora; seguro com a alternativa.
- 09:02 · Lia (analista de dados): CDI (% a.a.) (2 dia(s) atrasado): `estimar` — o CDI acompanha a Selic, dá para estimar com folga.
- 09:04 · Caio (líder de Dashboards): Selic meta (% a.a.) (2 dia(s) atrasado): `usar_ontem` — número que muda devagar; repetir o último é seguro.
- 09:06 · Caio (líder de Dashboards): Dólar PTAX (R$) (2 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.
- 09:08 · Caio (líder de Dashboards): Ibovespa (pts) (4 dia(s) atrasado): `usar_ontem` — repito o último valor com aviso de defasagem.
- 10:06 · Helena (CEO): Aprovado: +1 pessoa na Extração (4 incidentes abertos). Equipe vai para 4.

## Últimos eventos
- 2026-10-08 · extracao · INC-0011: falha real em BCB · PTAX (Olinda)
- 2026-10-08 · extracao · INC-0012: falha real em BCB · Focus (Olinda)
- 2026-10-07 · extracao · INC-0010: falha real em BCB · SGS
- 2026-10-06 · extracao · INC-0008 resolvido: BCB · SGS voltou após 2 dia(s) (corrigir_conector)
- 2026-10-06 · dashboards · Estimativa errada de bova11 em 2026-10-05: 191.8912 vs real 204.35
- 2026-10-05 · extracao · INC-0009: falha real em Yahoo Finance
- 2026-10-02 · extracao · INC-0006 resolvido: BCB · PTAX (Olinda) voltou após 1 dia(s) (aguardar)
- 2026-10-02 · extracao · INC-0007 resolvido: Yahoo Finance voltou após 1 dia(s) (corrigir_conector)
- 2026-10-02 · extracao · INC-0008: falha real em BCB · SGS
- 2026-10-02 · fundo · Rebalanceamento: giro R$ 17,6 mi, custo R$ 8.781
