# Estudo de caso: de dashboard SQL a framework de qualidade de dados

**Período:** out/2025 → set/2026 · **Repositórios:** `dashboard`, `dashboard2`, `duplicates_python`, `duplicate-insight`, `interface_html` → [`projetos/01-data-quality-kit`](../../projetos/01-data-quality-kit)

## O problema de origem

O ponto de partida foram duas tarefas repetitivas do dia a dia de análise: **montar visões rápidas sobre o resultado de uma query** e **descobrir por que uma tabela tinha chave duplicada**. As duas eram feitas à mão, em planilha ou em SQL avulso. Todos os projetos abaixo atacam esse mesmo problema, e cada versão nasceu do que a anterior ensinou.

## Linha do tempo

| Quando | Projeto | O que era | O que aprendi |
|---|---|---|---|
| 09–10/out/2025 | `dashboard` | Flask + SQLite: editor SQL com autocomplete e um construtor de dashboard (tabela dinâmica, gráfico, indicador) sobre bases sintéticas de voos e transações. | Dá para construir a UI rápido, mas **o gargalo não é visualizar**: é confiar no dado que está sendo visualizado. |
| 11/out/2025 | `dashboard2` | Reescrita em FastAPI com API REST (`/api/schema`, `/api/query`, `/api/dashboards`), dashboards salvos e documentação de deploy. | Separar API de UI; preparar projeto para publicação. |
| 21/out/2025 | `duplicates_python` | Flask: informa tabela ou `SELECT`, escolhe colunas-chave e vê os registros duplicados, com um **resumo das colunas que divergem** entre as linhas repetidas. 7 PRs pequenos num único dia. | O valor está no diagnóstico ("*quais* colunas divergem"), não na contagem. |
| 21/out/2025 | `duplicate-insight` | A mesma ferramenta com front em React + TypeScript + shadcn/ui, prototipada no Lovable e ligada a um backend Flask. Agrupa as divergências por **tipo de diferença**. | Testar a mesma ideia em duas stacks no mesmo dia mostrou que o valor não estava na interface. |
| 13/nov/2025 | `interface_html` | "Flight SQL Lab": views SQL reutilizáveis, análise de duplicidade, dashboards Plotly e sandbox SQL num só app, com 10 mil registros sintéticos. 39 commits, **6 deles reverts**. | Testei várias UX de filtro no dashboard e reverti as que complicavam mais do que ajudavam. Reverter rápido faz parte de experimentar. |
| set/2026 | **`dq-kit`** | A lógica saiu da interface e virou **biblioteca testada**: validação em 3 camadas (pré, durante, pós), tabela de controle, diagnóstico de duplicidade exata/divergente, mesmos checks em pandas e PySpark, CLI e servidor MCP para agentes. | Ver abaixo. |

## Por que a versão final é uma biblioteca, e não mais um app

1. **O problema real acontece dentro do pipeline**, não numa tela. Uma duplicidade descoberta num dashboard já contaminou o número. O lugar de detectar é na execução, antes de gravar.
2. **O que se repete entre projetos é a lógica**, não a UI. Três interfaces diferentes (Flask, React e o SQL Lab) reimplementavam a mesma lógica de duplicidade, e agora ela existe uma vez, com testes.
3. **Agentes de IA também precisam dessas ferramentas.** Um agente que escreve SQL deveria provar que a saída tem chave única e sem nulos antes de propor o PR. O servidor MCP expõe exatamente isso.

## Como trabalhei

- Em 2025, com **Codex**: cada ajuste era uma tarefa → um PR pequeno (`codex/...`) → revisão → merge. É por isso que `duplicates_python` tem 7 PRs num dia e `interface_html` tem reverts explícitos. O histórico mostra as tentativas, inclusive as que não deram certo.
- Em 2026, com **Claude Code**: especificação e arquitetura primeiro, testes junto do código, e validação da saída (exemplo ponta a ponta rodando nos testes).
