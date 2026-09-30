# Casos de avaliação: impala-sql-review

Cada caso tem uma query de entrada e os achados **obrigatórios** (a skill falha se não apontar) e **proibidos** (a skill falha se apontar, porque seria falso positivo). Rodar a skill contra estes casos a cada mudança no `SKILL.md` evita regressões e o "achismo" crescendo com o tempo.

Premissa comum: `vendas` e `clientes` são tabelas Parquet; `vendas` é particionada por `dt_ref STRING` (`'YYYY-MM-DD'`).

---

## Caso 1: pruning perdido + `SELECT *`

```sql
SELECT *
FROM vendas
WHERE substr(dt_ref, 1, 7) = '2026-09';
```

- **Obrigatórios:** P1 (função sobre a coluna de partição; reescrever para `dt_ref BETWEEN '2026-09-01' AND '2026-09-30'`), P2.
- **Proibidos:** C1 (não há join).

## Caso 2: `LEFT JOIN` que virou `INNER`

```sql
SELECT c.id_cliente, v.valor
FROM clientes c
LEFT JOIN vendas v ON v.id_cliente = c.id_cliente
WHERE v.dt_ref = '2026-09-29';
```

- **Obrigatórios:** C2 (mover `v.dt_ref = ...` para o `ON` se a intenção for manter clientes sem venda; perguntar a intenção).
- **Proibidos:** P1 (o filtro de partição é literal e direto; não há perda de pruning).

## Caso 3: `NOT IN` com possível `NULL`

```sql
SELECT id_cliente
FROM clientes
WHERE id_cliente NOT IN (SELECT id_indicador FROM clientes);
```

- **Obrigatórios:** C3 (`id_indicador` pode ser nulo → resultado vazio; usar `NOT EXISTS`).
- **Proibidos:** P6.

## Caso 4: autojoin para o último registro

```sql
SELECT v.id_cliente, v.valor
FROM vendas v
JOIN (
    SELECT id_cliente, MAX(dt_ref) AS ult
    FROM vendas
    WHERE dt_ref >= '2026-09-01'
    GROUP BY id_cliente
) u ON u.id_cliente = v.id_cliente AND u.ult = v.dt_ref
WHERE v.dt_ref >= '2026-09-01';
```

- **Obrigatórios:** P6 (`ROW_NUMBER() OVER (PARTITION BY id_cliente ORDER BY dt_ref DESC)`); mencionar que, com mais de uma venda no mesmo `dt_ref`, as duas formas retornam várias linhas (C1) e que é preciso definir o desempate.
- **Proibidos:** P1 (os filtros de partição estão corretos nas duas leituras).

## Caso 5: query limpa

```sql
SELECT dt_ref, canal, COUNT(*) AS vendas, SUM(valor) AS total
FROM vendas
WHERE dt_ref BETWEEN '2026-09-01' AND '2026-09-29'
GROUP BY dt_ref, canal;
```

- **Obrigatórios:** declarar que não há achados relevantes (no máximo, sugerir conferir as estatísticas).
- **Proibidos:** qualquer achado de severidade alta ou média.

---

### Como pontuar

`nota = (obrigatórios encontrados / obrigatórios totais) − 0,5 × (proibidos apontados)`, por caso. A versão atual da skill só é aceita se todos os casos tiverem nota ≥ 1,0.
