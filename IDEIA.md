Ideia: simular uma gestora de ativos fictícia, com dados públicos reais e atualizados,
que vive só no GitHub.

A empresa tem:
- Um pipeline de dados: extração automatizada, preparo dos dados por área da empresa e
  dashboards específicos por tema/objetivo.
- Uma simulação em cima desses dados: um fluxo de decisão que gera novos processos
  (issues, PRs, mudanças de política), de forma que o que acontece hoje influencia o
  que acontece amanhã.

A empresa é dividida em áreas, e cada área enfrenta desafios do dia a dia que afetam as
outras:
- Extração: um dia a fonte muda, atrasa ou sai do ar, e a área precisa resolver o problema
  para que o resto da empresa tenha acesso aos dados.
- Dashboards: sofre com a falta de atualização dos dados, decide se usa os dados de ontem
  ou outra estratégia, e leva os números para os executivos.
- Executivos: tomam decisões e direcionam a empresa a partir dos dashboards.

Cada dia útil, um agente Claude agendado (Scheduled task) executa a empresa.
Você decide como isso funciona no GitHub: arquitetura, ferramentas e etapas.
