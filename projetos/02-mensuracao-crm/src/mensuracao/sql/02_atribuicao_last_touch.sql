-- Atribuição last-touch: cada conversão vai para o último canal que tocou o
-- cliente dentro da janela de lookback (e não depois da conversão).
-- Empate no mesmo dia: vence o canal de menor `prioridade` (tabela canais).
-- Conversão sem toque elegível = 'organico'.
WITH candidatos AS (
    SELECT cv.cliente_id,
           cv.dt_conversao,
           t.canal,
           t.dt_toque,
           ROW_NUMBER() OVER (
               PARTITION BY cv.cliente_id, cv.dt_conversao
               ORDER BY t.dt_toque DESC, ca.prioridade ASC
           ) AS ordem
    FROM conversoes AS cv
    LEFT JOIN toques AS t
           ON t.cliente_id = cv.cliente_id
          AND t.dt_toque <= cv.dt_conversao
          AND t.dt_toque >= date(cv.dt_conversao, '-' || :lookback || ' days')
    LEFT JOIN canais AS ca ON ca.canal = t.canal
    WHERE cv.dt_conversao BETWEEN :dt_inicio AND :dt_fim
)
SELECT cliente_id,
       dt_conversao,
       COALESCE(canal, 'organico') AS canal_atribuido,
       dt_toque
FROM candidatos
WHERE ordem = 1
ORDER BY cliente_id, dt_conversao;
