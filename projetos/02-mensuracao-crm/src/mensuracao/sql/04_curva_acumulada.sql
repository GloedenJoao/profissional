-- Curva de conversão acumulada por dia desde o início da campanha, por grupo.
-- Útil para ver quando o efeito aparece e se ele se sustenta ou só antecipa conversões.
WITH campanha AS (
    SELECT dt_inicio FROM campanhas WHERE campanha_id = :campanha_id
),
dias AS (
    SELECT 0 AS d
    UNION ALL
    SELECT d + 1 FROM dias WHERE d < :dias
),
tamanho AS (
    SELECT grupo, COUNT(*) AS clientes FROM publico_campanha WHERE campanha_id = :campanha_id GROUP BY grupo
),
primeira_conversao AS (
    SELECT p.grupo, p.cliente_id, MIN(julianday(c.dt_conversao) - julianday(cp.dt_inicio)) AS dia
    FROM publico_campanha AS p
    CROSS JOIN campanha AS cp
    JOIN conversoes AS c ON c.cliente_id = p.cliente_id AND c.dt_conversao >= cp.dt_inicio
    WHERE p.campanha_id = :campanha_id
    GROUP BY p.grupo, p.cliente_id
),
diario AS (
    SELECT t.grupo, dd.d AS dia, COUNT(pc.cliente_id) AS novas
    FROM tamanho AS t
    CROSS JOIN dias AS dd
    LEFT JOIN primeira_conversao AS pc ON pc.grupo = t.grupo AND pc.dia = dd.d
    GROUP BY t.grupo, dd.d
)
SELECT d.grupo,
       d.dia,
       SUM(d.novas) OVER (PARTITION BY d.grupo ORDER BY d.dia) AS acumuladas,
       ROUND(1.0 * SUM(d.novas) OVER (PARTITION BY d.grupo ORDER BY d.dia) / t.clientes, 6) AS taxa_acumulada
FROM diario AS d
JOIN tamanho AS t ON t.grupo = d.grupo
ORDER BY d.grupo DESC, d.dia;
