# João Gloeden · Data Engineering · Analytics · Applied AI

São Paulo, Brazil · [LinkedIn](https://www.linkedin.com/in/jo%C3%A3o-ant%C3%B4nio-de-vasconcellos-gloeden-7114001b5) · [Versão em português](README.md)

I'm a mid-level data analyst at Banco Safra with 5+ years across automation, CRM and data. I maintain PySpark/Hive pipelines on Cloudera, measure business-client acquisition with control groups, and build tools powered by LLMs and AI agents. Fluent in English.

This repository holds **runnable code with tests that prove it works**, plus the story of how each project got there: the attempts, pivots and decisions. Project docs are in Portuguese; this page summarizes them.

## Featured projects

| Project | What it shows | Tests |
|---|---|---:|
| [**dq-kit**](projetos/01-data-quality-kit) | 3-layer pipeline validation (pre-conditions, in-run checkpoints such as join fan-out detection, post-conditions) logged to an auditable control table. The same checks run on **pandas and PySpark**. The duplicate diagnosis separates load problems (exact duplicates) from modeling problems (diverging duplicates). Includes an **MCP server** so AI agents can prove their queries are correct. | 34 |
| [**Campaign measurement**](projetos/02-mensuracao-crm) | Incrementality (control group, 95% CI, z-test, power/MDE) vs. last-touch attribution, written in SQL with window functions, on synthetic data with a known true effect. Findings: last-touch overstates CRM by 2.5–5.7x, and a 10% holdout is underpowered for the real effect. | 8 |
| [**Stock Oracle**](projetos/03-stock-oracle) | A lab for measuring prediction agents against ground truth. It started as an LLM multi-agent system and pivoted to sandboxed, versioned local strategies with backtesting once LLM measurement proved costly and non-reproducible. | 26 |

## Applied AI

- [`impala-sql-review` skill](ia/skills/impala-sql-review/SKILL.md): an explicit checklist that puts correctness before performance, with an [eval set](ia/skills/impala-sql-review/evals.md) that penalizes false positives.
- [How I work with agents](ia/README.md): from chat assistants to Codex (one PR per task) to Claude Code (plans, per-layer `CLAUDE.md`, headless tests).

## Case studies

[Impala SQL AI Studio](docs/estudos-de-caso/impala-sql-ai-studio.md) (SQL editor with an embedded agent) · [7 Godot games built with agents](docs/estudos-de-caso/jogos-2d-pixelart.md) (~1,000 checks in headless tests, 31 PRs) · [Pre-registered copy-trading experiment](docs/estudos-de-caso/copy-trading-experimento.md) · [From SQL dashboards to a DQ framework](docs/estudos-de-caso/ferramentas-sql-analytics.md) · [From CRM journeys to causal measurement](docs/estudos-de-caso/crm-reguas-e-mensuracao.md) · [One rules engine, three platforms](docs/estudos-de-caso/simulador-financeiro.md)

## Experience

- **Market Intelligence Analyst (mid-level), Banco Safra**, Sep 2025–present: ~10 PySpark/Hive pipelines on Cloudera deployed via GitLab CI; acquisition measurement and attribution; Power BI; a 3-layer pipeline validation framework.
- **CRM Analyst (junior), Banco Safra**, Feb 2024–Oct 2025 · **CRM Intern**, Jun 2023–Feb 2024
- **Digital Solutions Intern, BASF (Suvinil)**, Nov 2020–Jan 2023: RPA, Power BI, internal Python/RPA/Power Automate courses.

All data in this repository is synthetic or public.
