-- Resumo da atribuição last-touch por canal, com participação no total.
WITH atribuicao AS (
    SELECT canal_atribuido, COUNT(*) AS conversoes
    FROM last_touch
    GROUP BY canal_atribuido
)
SELECT canal_atribuido AS canal,
       conversoes,
       ROUND(100.0 * conversoes / SUM(conversoes) OVER (), 2) AS pct_total
FROM atribuicao
ORDER BY conversoes DESC;
