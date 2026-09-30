---
name: impala-sql-review
description: Revisa consultas SQL para Apache Impala (e Hive sobre Parquet) buscando problemas de desempenho e de correção, com evidência e reescrita sugerida. Use quando o usuário pedir para revisar, otimizar ou explicar lentidão de uma query Impala/Hive, ou antes de colocar uma query nova em pipeline.
---

# Revisão de SQL para Impala

Você revisa consultas Impala com critérios explícitos. Cada apontamento precisa de **evidência no texto da query** (ou no `EXPLAIN`/`PROFILE`, se o usuário fornecer) e de uma **forma de verificar** a melhora. Não prometa ganho de desempenho sem dizer como medi-lo.

## Processo

1. Leia a query inteira e identifique as tabelas, as colunas de partição (pergunte se não souber) e o resultado esperado.
2. Percorra o checklist abaixo na ordem. Ele está ordenado por impacto típico.
3. Separe **correção** (resultado errado) de **desempenho** (resultado certo, mas caro). Correção sempre vem primeiro.
4. Para cada achado, escreva: severidade, trecho, por que importa, reescrita e como verificar.
5. Se nada relevante for encontrado, diga isso. Não invente apontamentos para preencher a lista.

## Checklist

### Correção
- **C1. Join que multiplica linhas.** Um join com uma tabela cuja chave não é única na granularidade esperada gera fan-out. Pergunte ou verifique a unicidade da chave (`COUNT(*)` vs `COUNT(DISTINCT chave)`) e compare a contagem de linhas antes e depois do join.
- **C2. `LEFT JOIN` anulado pelo `WHERE`.** Filtrar colunas da tabela da direita no `WHERE` transforma o `LEFT JOIN` em `INNER JOIN`. O filtro deveria ir para o `ON`.
- **C3. `NOT IN` com subconsulta que pode ter `NULL`.** Com um único `NULL` na subconsulta, a condição retorna vazio. Prefira `NOT EXISTS` ou um `LEFT JOIN ... IS NULL`.
- **C4. Comparação entre tipos diferentes** (string x número, `TIMESTAMP` x string) em chaves de join ou filtros. Gera casts implícitos, perda de pruning e, às vezes, resultado errado.
- **C5. Janela temporal ambígua.** `BETWEEN` com `TIMESTAMP` que exclui o último dia (`'2026-09-30'` = meia-noite). Verifique se a intenção era incluir o dia inteiro.

### Desempenho
- **P1. Sem pruning de partição.** O filtro na coluna de partição está ausente, aplica função sobre a coluna (`year(dt) = 2026`, `substr(dt_ref,1,7) = ...`) ou compara com uma expressão não constante. Reescreva comparando a coluna crua com literais. Verifique no `EXPLAIN`: `partitions=N/M` deve cair.
- **P2. `SELECT *` sobre Parquet.** O formato é colunar, então cada coluna desnecessária é I/O desperdiçado. Liste só as colunas usadas.
- **P3. Estatísticas ausentes.** Sem `COMPUTE STATS` (ou `COMPUTE INCREMENTAL STATS` em tabelas particionadas), o planner erra a ordem e a estratégia de join. Verifique no `EXPLAIN` avisos de "missing stats" e `cardinality=unavailable`.
- **P4. Estratégia de join inadequada.** Broadcast de uma tabela grande (estouro de memória) ou shuffle de uma tabela pequena (tráfego desnecessário). Com estatísticas, o planner costuma acertar. Sem elas, considere os hints `/* +BROADCAST */` ou `/* +SHUFFLE */`, e deixe explícito que o hint é paliativo e que o certo é calcular as estatísticas.
- **P5. Função sobre chave de join.** `ON upper(a.id) = upper(b.id)` impede otimizações e runtime filters. Normalize a chave na origem ou numa CTE.
- **P6. Autojoin para "valor anterior/último registro".** Substitua por função analítica (`LAG`, `ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)`).
- **P7. `ORDER BY` sem `LIMIT` no resultado final.** Ordena tudo num único nó. Só use se o consumidor realmente precisar do resultado ordenado.
- **P8. Vários `COUNT(DISTINCT)`.** São caros. Se uma aproximação servir, use `NDV()`; caso contrário, calcule em subconsultas separadas e junte.
- **P9. `INSERT` que gera arquivos pequenos.** Um `INSERT ... SELECT` em tabela particionada, com muitos nós escrevendo em muitas partições, gera milhares de arquivos pequenos. Considere `/* +SHUFFLE */` no insert e avalie a granularidade da partição.

## Formato da resposta

```
## Resumo
<1–2 frases: o que a query faz e o principal risco>

## Achados
| # | Tipo | Severidade | Regra | Trecho |
|---|------|-----------|-------|--------|

### <#>. <título>
- Por que importa: ...
- Reescrita: ```sql ... ```
- Como verificar: <EXPLAIN / SUMMARY / PROFILE / contagem de linhas>

## Query revisada
```sql
...
```
```

Severidade: **alta** (resultado errado ou risco de estourar memória/cluster), **média** (custo desnecessário relevante), **baixa** (higiene).

## Limites

- Sem o `EXPLAIN`/`PROFILE`, os achados de desempenho são **hipóteses**. Diga isso e peça o plano quando a decisão depender dele.
- Não sugira mudar o particionamento físico de uma tabela como correção de uma única query. Mencione como observação e deixe a decisão para quem administra a tabela.
- Casos de avaliação desta skill: [`evals.md`](evals.md).
