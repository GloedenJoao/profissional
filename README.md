# João Gloeden · Engenharia de Dados · Analytics · IA Aplicada

[![CI](https://github.com/GloedenJoao/profissional/actions/workflows/ci.yml/badge.svg)](https://github.com/GloedenJoao/profissional/actions/workflows/ci.yml)
&nbsp;·&nbsp; São Paulo, SP &nbsp;·&nbsp; [LinkedIn](https://www.linkedin.com/in/jo%C3%A3o-ant%C3%B4nio-de-vasconcellos-gloeden-7114001b5) &nbsp;·&nbsp; [English version](README.en.md)

Sou analista de dados pleno no Banco Safra. Mantenho pipelines PySpark/Hive em Cloudera, meço a aquisição de clientes PJ com grupos de controle e construo ferramentas com LLMs e agentes de IA. Tenho mais de 5 anos entre automação, CRM e dados.

Este repositório reúne **o que eu sei fazer, com código que roda e testes que provam**. Também mostra **como cheguei até aqui**: cada projeto conta a sequência de tentativas, pivôs e decisões que levou à versão atual.

---

## Projetos em destaque

### 1 · [dq-kit: validação de pipelines em 3 camadas](projetos/01-data-quality-kit)
`Python` `pandas` `PySpark` `Hive` `MCP` · **34 testes**

O pipeline valida os insumos (pré), os passos intermediários (durante: *"esse join multiplicou linhas?"*) e a saída (pós), e grava tudo numa tabela de controle. Os mesmos checks rodam em pandas e em PySpark. O diagnóstico de duplicidade separa problema de carga (duplicata exata) de problema de regra (duplicata divergente) e aponta a coluna culpada. Um servidor MCP deixa um agente de IA **provar** que a query que ele escreveu está certa.

```
[OK ] consolida_conversoes   pre      contas             not_null(cnpj, dt_abertura)
[ERR] consolida_conversoes   durante  join_leads_contas  row_count_equals(500) — diferença de +4 linhas
-> execução interrompida antes de gravar · causa: 4 contas duplicadas, divergindo em 'segmento'
```

### 2 · [Mensuração de campanhas: incrementalidade x atribuição](projetos/02-mensuracao-crm)
`SQL` `window functions` `estatística` `desenho experimental` · **8 testes** · zero dependências

Uma base sintética com efeito causal conhecido, em que o mesmo problema é medido de dois jeitos. Conclusões: **o last-touch superestima o CRM em 2,5x a 5,7x** frente ao grupo de controle, e **um holdout de 10% não tem poder** para detectar o efeito real (seria preciso ~22%). Recomendação: holdout dimensionado antes do disparo.

<img src="projetos/02-mensuracao-crm/relatorio_exemplo/curva_acumulada.svg" width="560" alt="Curva de conversão acumulada: tratamento x controle">

### 3 · [Stock Oracle: laboratório para medir agentes](projetos/03-stock-oracle)
`FastAPI` `SQLAlchemy` `Anthropic SDK` `sandbox AST` · **26 testes**

Começou como sistema multiagente com LLM prevendo preço. Pivotei para estratégias locais versionadas em sandbox, com backtest, quando ficou claro que medir LLM prevendo preço é caro e não reproduzível. Construído em uma noite a partir de um plano de 346 linhas.

<img src="projetos/03-stock-oracle/docs/img/dashboard.png" width="560" alt="Dashboard do Stock Oracle">

---

## IA aplicada

- **[Skill `impala-sql-review`](ia/skills/impala-sql-review/SKILL.md)**: revisão de SQL Impala/Hive com checklist explícito (correção antes de desempenho) e **[casos de avaliação](ia/skills/impala-sql-review/evals.md)** que penalizam falso positivo.
- **[Servidor MCP do dq-kit](projetos/01-data-quality-kit/src/dq_kit/mcp_server.py)**: ferramentas de dados somente leitura para agentes.
- **[Como uso agentes](ia/README.md)**: princípios e evolução, de assistentes de chat → Codex (um PR por tarefa) → Claude Code (plano, `CLAUDE.md` por camada, testes headless).

## Estudos de caso

Projetos cujo valor está no **processo**. Alguns são privados ou não terminados, e está tudo bem: o que interessa é como foram conduzidos.

| Caso | O que mostra |
|---|---|
| [Impala SQL AI Studio](docs/estudos-de-caso/impala-sql-ai-studio.md) | Editor SQL + agente integrado + skill de otimização (PySide6); em desenvolvimento: execução PySpark via sqlglot + Livy |
| [7 jogos em Godot com agentes](docs/estudos-de-caso/jogos-2d-pixelart.md) | Plano de 90 dias, framework reaproveitado, **~1.000 verificações em testes headless**, 31 PRs, decisões registradas, refazer quando vale a pena |
| [Experimento de copy trading](docs/estudos-de-caso/copy-trading-experimento.md) | Regras pré-registradas, funil com dados reais, benchmark CDI (API do Banco Central), 40 testes offline |
| [De dashboard SQL a framework de DQ](docs/estudos-de-caso/ferramentas-sql-analytics.md) | 5 versões da mesma ideia em Flask, FastAPI e React até virar biblioteca |
| [De réguas de CRM a mensuração causal](docs/estudos-de-caso/crm-reguas-e-mensuracao.md) | Modelagem de réguas com diagrama Mermaid gerado do banco → medição de efeito |
| [Um problema, três plataformas](docs/estudos-de-caso/simulador-financeiro.md) | Mesmo motor de regras em Flask → FastAPI com deploy no Fly.io → Android nativo (Compose) em duas semanas |

## Stack

| Área | Ferramentas |
|---|---|
| Dados e processamento | SQL (Impala, Hive, SQL Server, SQLite), Python, PySpark, Cloudera, pandas, modelagem, qualidade de dados |
| Engenharia | Git, GitLab CI/CD, GitHub Actions, pytest, FastAPI, Flask, SQLAlchemy, Docker, Fly.io |
| IA | LLMs e agentes, tool use, MCP, skills, evals, Claude Code, Anthropic SDK |
| BI e automação | Power BI, Power Automate, RPA, Excel/VBA |
| Outros | Kotlin/Jetpack Compose, Godot/GDScript, React/TypeScript (protótipos) |

## Navegação

```
projetos/     código executável, com testes (CI roda os três)
ia/           skill, evals e como uso agentes
docs/
├── trajetoria.md        carreira e o fio condutor entre cargos e projetos
├── curadoria.md         quais repositórios entraram, quais saíram e por quê
└── estudos-de-caso/     o processo por trás de cada projeto
```

Todos os dados deste repositório são sintéticos ou públicos.
