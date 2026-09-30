-- Taxa de conversão por grupo (tratamento x controle) de uma campanha.
-- Conta a conversão se ela ocorreu entre o início da campanha e o fim da
-- janela de observação. Cada cliente conta uma vez, mesmo com várias conversões.
WITH campanha AS (
    SELECT campanha_id, dt_inicio, date(dt_fim, '+' || :janela || ' days') AS dt_limite
    FROM campanhas
    WHERE campanha_id = :campanha_id
),
por_cliente AS (
    SELECT p.grupo,
           p.cliente_id,
           MAX(CASE WHEN c.dt_conversao BETWEEN cp.dt_inicio AND cp.dt_limite THEN 1 ELSE 0 END) AS converteu
    FROM publico_campanha AS p
    JOIN campanha AS cp ON cp.campanha_id = p.campanha_id
    LEFT JOIN conversoes AS c ON c.cliente_id = p.cliente_id
    GROUP BY p.grupo, p.cliente_id
)
SELECT grupo,
       COUNT(*)                        AS clientes,
       SUM(converteu)                  AS conversoes,
       ROUND(1.0 * SUM(converteu) / COUNT(*), 6) AS taxa
FROM por_cliente
GROUP BY grupo
ORDER BY grupo DESC;
