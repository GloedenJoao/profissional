# IA aplicada: como uso agentes de verdade

Uso agentes de IA em duas frentes: **para construir** (Codex em 2025, Claude Code em 2026) e **como parte do que é construído** (ferramentas, skills e servidores MCP que outros agentes usam). Esta pasta reúne os artefatos dessa segunda frente e aponta onde está a evidência da primeira.

## Artefatos

| Artefato | O que é | Onde |
|---|---|---|
| Servidor MCP `dq-kit` | Expõe perfil de dados, diagnóstico de duplicidade e checks declarativos para agentes (Claude Code, Claude Desktop). Somente leitura, testado. | [`projetos/01-data-quality-kit`](../projetos/01-data-quality-kit/src/dq_kit/mcp_server.py) |
| Skill `impala-sql-review` | Revisão de SQL Impala/Hive com checklist explícito, formato de saída fixo e limites declarados. | [`skills/impala-sql-review`](skills/impala-sql-review/SKILL.md) |
| Evals da skill | 5 casos com achados obrigatórios e **proibidos** (falso positivo também é falha) e regra de pontuação. | [`skills/impala-sql-review/evals.md`](skills/impala-sql-review/evals.md) |
| Agentes medidos contra gabarito | Previsões de agentes gravadas e resolvidas contra o preço real; pivô de LLM para estratégia local quando medir ficou caro demais. | [`projetos/03-stock-oracle`](../projetos/03-stock-oracle) |
| Impala SQL AI Studio | Editor SQL + agente integrado + skill de otimização (código não público). | [estudo de caso](../docs/estudos-de-caso/impala-sql-ai-studio.md) |

## Princípios que sigo

1. **Contexto escrito vale mais que prompt esperto.** Cada projeto tem `CLAUDE.md` (ou `AGENTS.md`, na fase Codex) com as regras de arquitetura. No Stock Oracle há um por camada, então o agente sabe que `routers/` não chama `yfinance` e que teste não acessa a rede.
2. **Plano antes de código.** Projetos longos começam por um documento de plano ([Stock Oracle](../projetos/03-stock-oracle/docs/PLANO_ORIGINAL.md), [jogos](https://github.com/GloedenJoao/jogos-2d-pixelart/tree/main/docs)), que é revisado e atualizado junto com o código.
3. **O agente prova, não afirma.** Testes rodam a cada mudança, o exemplo ponta a ponta faz parte da suíte, os jogos geram screenshots automaticamente para validação visual e o `dq-kit` existe para o agente provar que os dados estão certos.
4. **Medir antes de otimizar.** Uma skill sem casos de avaliação é opinião. Um agente sem gabarito é demonstração.
5. **Mudanças pequenas e reversíveis.** Um PR por mudança, reverter sem cerimônia quando a ideia não se paga (veja os reverts em `interface_html`) e refazer do zero quando for melhor (Projeto 5 → 5 V2 dos jogos).

## Evolução do meu uso

| Fase | Ferramenta | Como era |
|---|---|---|
| ago–out/2025 | Assistentes de chat, Lovable | Código gerado em blocos, colado e ajustado à mão. Protótipo de front no Lovable. |
| out–dez/2025 | Codex | Uma tarefa → um PR (`codex/...`). `AGENTS.md` com regras de manutenção. Até 17 PRs num único dia (`Android_AppV4`). |
| 2026 | Claude Code | Sessões longas com plano, `CLAUDE.md` por camada, testes headless, skills, MCP e sessões remotas. Projetos de semanas (7 jogos, 31 PRs) mantendo o histórico legível. |
