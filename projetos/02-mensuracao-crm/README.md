# Mensuração de campanhas: incrementalidade x atribuição

> "Quantas contas essa campanha trouxe?" tem duas respostas diferentes, e elas respondem perguntas diferentes. Este projeto calcula as duas em SQL, sobre uma base sintética em que a resposta certa é conhecida, e mostra quando cada uma serve.

**Stack:** SQL (CTEs, window functions) · Python stdlib · SQLite (SQL portável para Impala/Hive) · pytest · zero dependências

## Contexto

É o tipo de trabalho que faço hoje: medir e atribuir a aquisição de clientes PJ entre canais digitais (CRM, mídia paga, MGM) e humanos (gerentes), com grupos de controle e regras de last-touch. Os dados reais não podem sair do banco, então este projeto **reproduz o problema com dados sintéticos**. A vantagem é que o efeito verdadeiro da campanha é um parâmetro da simulação (`lift_real = +1,5 p.p.`), e dá para checar se cada método de mensuração acerta.

## O que ele calcula

| Pergunta | Método | Arquivo |
|---|---|---|
| A campanha **causou** conversões? Quantas? | Grupo de controle (holdout): taxa do tratamento − taxa do controle, com IC 95% e teste z | [`01_lift_grupo_controle.sql`](src/mensuracao/sql/01_lift_grupo_controle.sql) |
| Qual canal fica com o **crédito operacional** de cada conversão? | Last-touch com lookback de 30 dias, desempate por prioridade de canal, "orgânico" sem toque | [`02_atribuicao_last_touch.sql`](src/mensuracao/sql/02_atribuicao_last_touch.sql) |
| Como fica a divisão por canal? | Participação com `SUM() OVER ()` | [`03_last_touch_por_canal.sql`](src/mensuracao/sql/03_last_touch_por_canal.sql) |
| Quando o efeito aparece? | Curva acumulada diária por grupo (CTE recursiva + soma móvel) | [`04_curva_acumulada.sql`](src/mensuracao/sql/04_curva_acumulada.sql) |
| O desenho do teste **consegue** detectar o efeito? | Menor efeito detectável (MDE, poder 80%) e holdout necessário | `analise.py` |

## Resultado (base sintética, seed 42)

![Curva de conversão acumulada](relatorio_exemplo/curva_acumulada.svg)

Relatório completo: [`relatorio_exemplo/relatorio.md`](relatorio_exemplo/relatorio.md). Principais leituras:

1. **O last-touch superestima o CRM em 2,5x a 5,7x.** Ele credita 790 conversões ao CRM, e o grupo de controle estima ~139 incrementais. O CRM toca todo o público, inclusive quem já ia converter, e fica com a última interação.
2. **O teste com 10% de holdout é inconclusivo** (p = 0,12), embora o efeito real exista: são +1,5 p.p. configurados, e esse valor está dentro do IC estimado. O desenho só detecta efeitos ≥ 1,37 p.p. Para detectar 1 p.p., o holdout precisaria ser de ~22%. **Holdout se dimensiona antes do disparo.**
3. **Recomendação:** last-touch serve para distribuir crédito operacional; grupo de controle serve para decidir investimento.

## Rodando

```bash
pip install -e ".[dev]"
python -m mensuracao --saida relatorio_exemplo   # gera base, roda SQL, escreve relatorio.md + SVG
pytest
```

## Regras de negócio testadas

As regras de atribuição rodam contra uma base montada à mão, onde a resposta certa é conhecida (`tests/test_mensuracao.py`):

- um toque **depois** da conversão não recebe crédito;
- um toque **fora do lookback** não recebe crédito;
- dois toques no **mesmo dia** → vence o canal de maior prioridade (`gerente > mgm > crm > mídia paga`);
- um cliente com várias conversões conta **uma vez** na taxa do grupo;
- uma conversão **antes da campanha** ou **depois da janela** não conta;
- com amostra grande, a mensuração **recupera o lift real** dentro do IC.

## De onde veio

Evolução de três projetos de CRM de 2025 (ver [estudo de caso](../../docs/estudos-de-caso/crm-reguas-e-mensuracao.md)):

- **`crm` (set/2025):** um case técnico de CRM de cartão de crédito. ETL de Excel → SQLite, perguntas de negócio respondidas 100% em SQL e proposta de régua.
- **`crm_conceito` (set/2025):** POC com base simulada de 10 mil clientes e webapp FastAPI de indicadores com filtros.
- **`regua_uml` (out/2025):** modelagem de réguas de comunicação (jornadas → temas → regras → dias) em Flask + SQLAlchemy, com diagrama gerado automaticamente em Mermaid. Foram 25 commits em uma semana.

O que mudou de lá para cá: os projetos anteriores **descreviam** campanhas (quantos clientes, quantas comunicações). Este **mede efeito causal** e deixa claro o limite de cada método, que é o que eu faço hoje no trabalho.
