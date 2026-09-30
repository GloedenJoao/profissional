# dq-kit: validação de pipelines de dados em 3 camadas

> Um pipeline que roda sem erro pode estar gravando dado errado. O `dq-kit` faz o pipeline provar, a cada execução, que está gravando o dado certo, e deixa essa prova registrada numa tabela de controle.

**Stack:** Python · pandas · PySpark · SQLite/Hive · MCP (Model Context Protocol) · pytest

## O problema

No dia a dia com pipelines PySpark/Hive, os incidentes mais caros não são os que quebram a execução. São os que passam quietos: um join que multiplica linhas porque a origem mandou a mesma conta duas vezes, uma partição que chegou vazia, um campo que passou a vir nulo. Quando alguém percebe, o dashboard já mostrou o número errado.

## A solução

Cada passo do pipeline é validado em três momentos, e todo resultado vira uma linha auditável:

```
          ┌──────────────┐      ┌────────────────────┐      ┌───────────────┐
insumos → │ PRÉ-CONDIÇÕES│ ───→ │ TRANSFORMAÇÃO      │ ───→ │ PÓS-CONDIÇÕES │ → saída gravada
          │ os insumos   │      │  └ checkpoint()    │      │ a saída cumpre│
          │ estão ok?    │      │    DURANTE: o join │      │ o contrato?   │
          └──────┬───────┘      │    explodiu?       │      └───────┬───────┘
                 │              └─────────┬──────────┘              │
                 └────────────────────────┴─────────────────────────┘
                                          ▼
                          tabela de controle (SQLite local / Hive no cluster)
                  run_id · passo · camada · check · observado · esperado · status
```

- **Dentro de cada camada todos os checks rodam** antes da decisão, então o log mostra *todos* os problemas, e não só o primeiro.
- **Severidade**: `error` interrompe o passo antes de gravar e `warn` fica só registrado (ex.: prazo de conversão fora do usual).
- **O mesmo check roda em pandas e em PySpark.** Os checks não conhecem o engine; eles pedem operações simples a um adaptador (`frames.py`). Os testes garantem que os dois engines dão o mesmo resultado.
- **Diagnóstico de duplicidade:** ele não para no "tem chave repetida". Classifica cada grupo em `exata` (problema de carga) ou `divergente` (problema de regra/modelagem) e ranqueia as colunas que divergem, que é por onde a investigação começa.
- **Servidor MCP:** as mesmas ferramentas ficam disponíveis para um agente de IA. Assim o agente pode *provar* que a query que escreveu respeita o contrato, em vez de só afirmar isso.

## Rodando

```bash
pip install -e ".[dev]"            # + ".[spark]" para PySpark, ".[mcp]" para o servidor MCP
python examples/pipeline_aquisicao_pj.py
pytest
```

Saída do exemplo (dados sintéticos). Na segunda execução a origem manda 4 contas duplicadas:

```
== Execução 2: origem com contas duplicadas ==
  [OK ] consolida_conversoes   pre      leads              unique(cnpj)
  [OK ] consolida_conversoes   pre      contas             not_null(cnpj, dt_abertura)
  [ERR] consolida_conversoes   durante  join_leads_contas  row_count_equals(500) — diferença de +4 linhas
-> execução interrompida antes de gravar

Diagnóstico da origem 'contas': {'chaves_duplicadas': 4, 'por_tipo': {'divergente': 4},
                                 'colunas_divergentes': {'segmento': 4}}
```

O pipeline parou **antes** de gravar a tabela final, e o diagnóstico já aponta a causa: mesma conta com dois segmentos na origem.

### Uso na biblioteca

```python
from dq_kit import Pipeline, ControlTable, checks as C

pipe = Pipeline("aquisicao_pj", ControlTable("controle.db"))

def consolidar(ctx, leads, contas):
    base = leads.merge(contas, on="cnpj", how="left")
    ctx.checkpoint("join", base, [C.row_count_equals(len(leads))])   # camada "durante"
    return base

fato = pipe.step(
    "consolida_conversoes",
    inputs={"leads": leads, "contas": contas},
    transform=consolidar,
    pre={"leads": [C.not_null("cnpj"), C.unique("cnpj")]},
    post=[C.unique("cnpj"), C.values_between("dias", 0, 30).as_warning()],
)
```

### CLI

```bash
dq-kit perfil dados.csv
dq-kit duplicidades banco.db --table contas --keys cnpj
dq-kit checar saida.parquet --spec checks.json     # exit code 1 se algum check bloqueante falhar → serve de gate em CI
dq-kit controle controle.db
```

### Com agentes de IA (MCP)

```bash
pip install -e ".[mcp]"
claude mcp add dq-kit -- dq-kit-mcp
```

Ferramentas expostas: `perfil_dataset`, `duplicidades_dataset`, `checar_dataset`, `resumo_controle`. Todas são somente leitura: consultas SQLite só aceitam `SELECT`/`WITH`, e nomes de tabela são validados.

## Decisões de design

| Decisão | Por quê |
|---|---|
| Checks devolvem *observado* e *esperado*, não só `True/False` | Quem lê a tabela de controle às 8h precisa entender a falha sem abrir o código. |
| Check que lança exceção vira **falha**, não crash | Um check mal escrito não pode derrubar o pipeline nem esconder os outros resultados. |
| Checks declaráveis em JSON (`from_spec`) | Regras de qualidade podem viver em configuração, ser revisadas em PR e ser geradas por um agente. |
| DDL Hive particionada por data de execução (`hive_ddl()`) | Mesmo contrato de tabela no local (SQLite) e no cluster. |
| Sem dependência de framework de DQ pronto | O objetivo é deixar a lógica de validação em 3 camadas explícita e legível (~850 linhas), e não escondida atrás de configuração. |

## Como chegou aqui

Esse projeto é a quarta versão de uma mesma ideia (ver [estudo de caso](../../docs/estudos-de-caso/ferramentas-sql-analytics.md)):

1. **Out/2025:** `dashboard` / `dashboard2`. Construtor de dashboards SQL em Flask e depois FastAPI. A lição foi que visualização sem dado confiável não resolve nada.
2. **Out/2025:** `duplicates_python` (Flask) e `duplicate-insight` (React + shadcn, prototipado no Lovable). Um analisador de duplicidade com resumo de colunas divergentes, construído em 7 PRs pequenos num mesmo dia.
3. **Nov/2025:** `interface_html`. Juntou views SQL, duplicidade e dashboards num "SQL Lab". Foram 39 commits, 6 deles *reverts*: testei várias UX de filtro e descartei as que não se pagavam.
4. **Set/2026:** este kit. A lógica de duplicidade saiu da interface e virou biblioteca, e ganhou as 3 camadas de validação que desenho no trabalho, suporte a PySpark e interface para agentes (MCP).

## Próximos passos

- Checks de volume relativo (variação vs. média das últimas N execuções).
- Leitura direta de tabelas Hive/Impala via conexão configurável.
- Publicar no PyPI.
