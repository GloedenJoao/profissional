# Trajetória

Da automação de processos ao dado confiável, e daí à IA aplicada sobre esse dado. Os projetos pessoais sempre andaram um passo à frente do cargo: serviram para testar fora do expediente o que depois virou trabalho.

```
2016 ──────── 2020 ─────────── 2023 ──────────── 2024 ─────────── 2025 ─────────────── 2026
 Professor    BASF (Suvinil)   Banco Safra        Banco Safra       Banco Safra
 particular   Soluções         Estágio CRM        Analista CRM      Analista de Inteligência
 (Mat, Fís,   Digitais         Consignado         (Consignado,      de Mercado Pleno
  Python)     RPA, Power BI                       Cartão, Veículos) PySpark · Hive · Cloudera
                                                                    Power BI · mensuração PJ
                                                                    framework de validação
                                                  │                  │                    │
 projetos pessoais:                               │   ago–set/25     │  out–dez/25        │  2026
                                                  │   finapp, crm,   │  SQL tools,        │  Stock Oracle, copy
                                                  │   crm_conceito   │  réguas, finanças, │  trading, 7 jogos,
                                                  │                  │  Android (Codex)   │  este portfólio
```

## Experiência

**Analista de Inteligência de Mercado Pleno · Banco Safra** · set/2025 – atual
- Mantenho cerca de 10 pipelines em PySpark e Hive na plataforma Cloudera, versionados e implantados via GitLab CI.
- Meço e atribuo a aquisição de clientes PJ nos canais digitais (CRM, mídia paga, MGM) e humanos (gerentes de conta), com grupos de controle e regras de last-touch. → *reproduzido com dados sintéticos em [`02-mensuracao-crm`](../projetos/02-mensuracao-crm)*
- Mantenho 4 dashboards em Power BI de acompanhamento da aquisição e modelo as tabelas que os alimentam. Uso Impala diariamente.
- Desenho um framework de validação de pipelines em 3 camadas (pré-condições, checagens durante a execução e pós-condições), com resultados registrados em tabela de controle no Hive. → *versão pública e independente em [`01-data-quality-kit`](../projetos/01-data-quality-kit)*

**Analista de CRM Júnior · Banco Safra** · fev/2024 – out/2025
- Concebi, automatizei e mensurei réguas de comunicação e campanhas sazonais de Consignado, Cartão de Crédito e Financiamento de Veículos.

**Estagiário de CRM (Consignado) · Banco Safra** · jun/2023 – fev/2024
- Automatizei processos internos e réguas de disparo para clientes.

**Estagiário em Soluções Digitais · BASF (Suvinil)** · nov/2020 – jan/2023
- Desenvolvi RPAs e dashboards em Power BI para a controladoria.
- Ministrei cursos internos de Python, RPA para SAP e Power Automate.

**Professor particular** · 2016 – atual
- Matemática, Física e programação em Python.

## Formação

Cursei Engenharia Civil (2018–2020), Ciência da Computação (2020–2024) e Ciência de Dados (2024–2025) na Universidade Presbiteriana Mackenzie, sem concluir nenhum dos três. O aprendizado técnico veio sobretudo da prática: do trabalho e dos projetos deste repositório.

**Idiomas:** Português (nativo) · Inglês (fluente) · Espanhol (compreensão avançada)

## O fio condutor

| Fase | Pergunta que eu respondia | Ferramenta principal |
|---|---|---|
| BASF | "Como esse processo roda sem alguém clicando?" | RPA, Power Automate, Power BI |
| CRM | "Qual comunicação vai para quem, e quando?" | SQL, automação de réguas |
| Inteligência de mercado | "Quanto disso foi *causado* pela ação, e o dado está certo?" | PySpark, Hive, Impala, grupo de controle |
| IA aplicada | "Como um agente trabalha com esses dados sem inventar?" | Claude Code, skills, MCP, evals |
