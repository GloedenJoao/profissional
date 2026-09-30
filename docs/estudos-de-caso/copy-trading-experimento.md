# Estudo de caso: experimento controlado com regras pré-registradas

**Período:** jul/2026 · **Repositório:** `copy-trading-tracker` (privado)

## A pergunta

"Copy trading funciona como renda passiva?" A resposta honesta não vem de opinião. Vem de um experimento **com regras definidas antes de ver o resultado**, medido contra um benchmark sem risco (CDI).

> Não é recomendação de investimento. O app é um instrumento de medição, e a premissa dele é que copy trading **não** é renda passiva confiável até que os dados provem o contrário.

## O que foi construído

Webapp local (FastAPI + SQLAlchemy + Jinja2, gráficos SVG renderizados no servidor, sem JS):

- **Funil de seleção com 6 filtros eliminatórios em ordem:** histórico ≥ 24 meses; drawdown < 25%; frequência baixa; consistência > magnitude; posições abertas x fechadas; e ignorar o número de copiadores (prova social não é critério).
- **Screening automático com dados reais:** um script busca a série pública de ganhos mensais de cada candidato e decide os filtros. Os que dá para calcular (meses de histórico, max drawdown da curva mensal, % de meses positivos com red flag para mediana > 10%/mês) são calculados. O que não é derivável dos dados (frequência) fica **pendente**, e não é aprovado por padrão.
- **Regras mecânicas de saída** avaliadas a cada página: 3 meses consecutivos negativos, aumento de risk score, mudança de padrão de frequência.
- **Benchmark CDI** a partir da série 12 do SGS/Banco Central, com cache local e veredito automático após 90 dias.
- **Simulação retroativa de cópia** a partir de qualquer data passada. A limitação fica explícita na UI: a distribuição pro-rata suaviza o caminho intramensal.

## Decisões que mostram método

| Decisão | Motivo |
|---|---|
| Regras do experimento vêm de um documento de decisões e "não se alteram sem alinhamento" (está no `CLAUDE.md`) | Evitar mudar a regra depois de ver o resultado, que é o erro clássico. |
| O drawdown mensal é tratado como **piso** do drawdown real | Fechamento mensal esconde a queda intramensal, e o código documenta isso. |
| Chamadas externas com `http_client` injetável; testes com `httpx.MockTransport` | 40 testes rodando offline. |
| Camadas separadas: `routers/` só HTTP, `services/` donos das regras | As regras do experimento são testáveis sem subir servidor. |

## Por que o repositório é privado

Contém a lista de candidatos avaliados (perfis públicos da plataforma, com notas da pesquisa). O código em si pode ser aberto sem essa lista, e isso está no radar.
