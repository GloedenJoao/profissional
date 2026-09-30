# Estudo de caso: Impala SQL AI Studio

**Período:** 2026 (em desenvolvimento) · **Código:** não público (iniciativa própria no contexto de trabalho)

## O que é

Aplicativo desktop para Windows, em Python (PySide6), que junta **um editor SQL para Impala e um agente de IA integrado**. O objetivo é que a pessoa analista escreva, entenda e otimize consultas sem sair do editor.

## Componentes

- **Editor SQL para Impala** com execução de consultas.
- **Agente de IA integrado** ao editor, com contexto da consulta em edição.
- **Skill de otimização de queries Impala** baseada na documentação da Cloudera, usada pelo agente para revisar consultas com critérios explícitos, e não com "achismo" do modelo. Veja uma versão pública e genérica em [`ia/skills/impala-sql-review`](../../ia/skills/impala-sql-review/SKILL.md).
- **Em desenvolvimento:**
  - módulo de **Knowledge Base** com grafo interativo de notas;
  - módulo de **execução em PySpark**, traduzindo SQL com `sqlglot` e submetendo via **Apache Livy**.

## Por que importa

É a ponte entre as duas metades do meu trabalho: **engenharia de dados** (Impala, Hive, PySpark, Cloudera) e **IA aplicada** (agentes, skills, tool use). Os projetos públicos deste portfólio isolam peças dessa ideia:

- a skill de revisão de SQL → [`ia/skills/impala-sql-review`](../../ia/skills/impala-sql-review/SKILL.md);
- ferramentas de dados expostas para agentes via MCP → [`projetos/01-data-quality-kit`](../../projetos/01-data-quality-kit).
