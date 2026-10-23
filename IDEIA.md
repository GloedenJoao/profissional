# Capivara Asset · a ideia

Uma gestora de ativos **fictícia** que vive só no GitHub e opera sobre **dados públicos reais**
(Banco Central, Tesouro Direto, B3, Yahoo Finance). A empresa tem áreas que dependem umas das outras:
a Extração traz os dados, os Dashboards preparam os números, o Comitê decide com esses números e o fundo
sente o resultado no preço de mercado do dia. O que acontece hoje é o ponto de partida de amanhã.

> Empresa e fundo fictícios. Nada aqui é recomendação de investimento.

## Duas coisas separadas

| | **Experimento** | **Simulação** |
|---|---|---|
| O que é | a empresa funcionando de verdade, um dia útil por vez, no presente | a mesma empresa refazendo 2026 desde 1º de janeiro |
| Para que serve | descobrir se uma gestora tocada por regras sobre dados reais se sustenta | testar o experimento antes de confiar nele: ver cada etapa, conferir cada conta, comparar com quem não decide nada |
| Quem anda | sozinha, seg–sex às 08h (`fechamento.yml`), com os dados de ontem | só quando o dono manda ("Simular próximo dia", `simulacao.yml`) |
| Onde mora | `dados/` e `empresa/` | `cenarios/2026/` |

As duas rodam **o mesmo motor** (`gestora/`). Se a simulação mostra que o motor erra, o erro também está no
experimento; se a simulação passa nas verificações por meses de dados, o experimento merece confiança.

## O motor: um dia útil em etapas

Cada dia útil passa pelas mesmas etapas, sempre nesta ordem. Cada etapa só enxerga o que a anterior
entregou e grava no **rastro do dia** (`dias/AAAA-MM-DD.json → rastro`) o que recebeu, a regra que
aplicou, a conta que fez e o que entregou. As falas da reunião são escritas **a partir do rastro**: toda
frase tem os números de onde veio.

| hora | etapa | pergunta que responde | entra | sai |
|---|---|---|---|---|
| 07:00 | **Herança** | de onde partimos? | o fechamento de ontem | incidentes abertos, carteira, equipe, caixa |
| 08:00 | **Extração** | que dados chegaram e quais a empresa pode usar? | fontes públicas | séries liberadas (o "portão") |
| 09:00 | **Dashboards** | que números vão para o comitê, e com que confiança? | séries liberadas | painel com 10 indicadores |
| 10:00 | **Comitê** | mexemos na carteira, na equipe ou no orçamento? | só o painel | alvo da carteira, equipe, orçamento |
| 18:00 | **Fundo** | quanto o fundo ganhou ou perdeu, e por quê? | preços oficiais do dia | cota, patrimônio, atribuição por ativo |
| 18:30 | **Empresa** | a gestora se paga? | taxa e custos | caixa da gestora, dívida técnica, credibilidade |
| 19:00 | **Verificações** | o motor fez tudo certo? | o rastro inteiro | ✓/✗ de cada regra de integridade |

### Cada número diz de onde veio

| origem | quer dizer | exemplo |
|---|---|---|
| **real** | dado público, com fonte e data | BOVA11 R$ 172,74 em 21/01 (Yahoo) |
| **derivado** | conta feita só com dados reais | CDI 14,90% a.a. = (1 + 0,055131%)^252 − 1 |
| **simulado** | modelo da empresa fictícia (com a conta ou o sorteio à vista) | chance de falha 6,6%, sorteio 0,041 → falhou |
| **decisão** | escolha de um time, com a regra que a produziu | IPCA+ 15% → 20% porque o juro real está 1,7 p.p. acima da referência |
| **regra** | parâmetro de política (`empresa/politicas.json`) | passo máximo de 5 p.p. por reunião |

### O que é real e o que é simulado

- **Real:** todas as cotações, taxas e índices; o calendário da B3; se uma fonte publicou ou não o dado
  esperado; as falhas reais de extração (no experimento); a divergência entre fontes (Yahoo × B3).
- **Simulado (e mostrado como tal):** a empresa, seus times e o dinheiro dos cotistas; o **teste de
  estresse** da Extração, que sorteia falhas que as fontes reais quase nunca têm, para a empresa ter os
  desafios da ideia original. O sorteio aparece no rastro com a chance, o número sorteado e a semente;
  a política pode desligá-lo (`extracao.estresse.ativo`).
- **Nunca:** olhar o futuro. Toda etapa só usa dados com data até o dia simulado, e a etapa Verificações
  confere isso todo dia.

### As regras de cada time (todas no rastro e na aba Regras)

- **Extração:** triagem por tipo de incidente (falha real e mudança de formato só se resolvem
  corrigindo o conector; queda com fonte alternativa liga a alternativa; atraso espera), dentro da
  capacidade da equipe (cada pessoa = 1 ponto). Sem gente, escala para o comitê.
- **Dashboards:** com dado faltando, número que muda devagar repete o último; CDI se estima pela Selic;
  preço com 1 dia de atraso se estima pela tendência; 3+ dias sem preço suspende. Estimativas são
  conferidas quando o dado real chega; erro além da tolerância derruba a credibilidade.
- **Comitê:** uma reunião de investimentos por semana (ou quando há pauta: resgate, desenquadramento,
  caixa da gestora, pedido da Extração, preço mexendo 3% no dia). A tese é um **modelo explícito**
  (`politicas.json → executivos.modelo`): cada ativo tem um sinal calculado com números do painel,
  o alvo é `peso neutro + sensibilidade × sinal`, limitado pela política e por um passo máximo. Número
  com confiança baixa não é usado ("não mexemos no que não enxergamos").
- **Fundo:** marcação a mercado pelo administrador (preço oficial, independente dos problemas da
  Extração), CDI no caixa, taxa de administração, aplicações e resgates por um modelo sem sorteio
  (desempenho contra o CDI e credibilidade), rebalanceamento quando o alvo muda ou o desvio passa
  de 5 p.p.

### Como saber se funciona

A simulação existe para responder "o experimento funciona?". Três jeitos de medir, todos no site:

1. **Verificações diárias** (integridade): sem olhar o futuro; a contabilidade fecha (patrimônio =
   soma das posições; variação do patrimônio = resultado de cada ativo − taxa − custos + fluxo); pesos
   dentro dos limites; preço usado = preço da fonte.
2. **Contrafactual** (valor das decisões): uma **carteira de referência** começa igual ao fundo e nunca
   muda de ideia (alocação neutra, rebalanceada por desvio). Fundo − referência = o que as decisões do
   comitê acrescentaram ou tiraram. O CDI é a régua mínima.
3. **Saúde da empresa:** dias com todos os números em dia, tempo até resolver incidentes, acerto das
   estimativas, caixa da gestora.

## As telas

O site (GitHub Pages) e o app Android leem os mesmos arquivos.

- **Início:** as duas coisas lado a lado, com o estado de cada uma e o mapa das etapas.
- **Dia** (a tela principal de cada um): escolhe-se a data; as etapas aparecem em ordem, cada uma com a
  conversa do time e, ao lado de cada fala, **as contas que a sustentam** (tabelas com origem de cada
  número). O modo **Assistir** toca o dia etapa por etapa. Na simulação, o botão **Simular próximo dia**
  dispara o GitHub Actions e mostra a execução passo a passo até o dia novo chegar e começar a tocar.
- **Fundo:** cota × CDI × carteira de referência, atribuição do resultado por ativo, alocação e
  decisões com o efeito de cada uma.
- **Dados:** o pipeline (fontes → séries → indicadores), a última extração real, a qualidade dos dados,
  os incidentes (reais e simulados) e a disponibilidade dia a dia.
- **Empresa:** receita, custos, caixa da gestora, equipe, dívida técnica e credibilidade.
- **Validação:** as verificações de todos os dias, o contrafactual e as métricas de saúde.
- **Regras:** o motor por dentro, com os parâmetros vigentes de `politicas.json`.

## Pedido original

O texto que deu origem a tudo (o agente agendado virou os times dentro do motor; o conselho é opcional):

> Ideia: simular uma gestora de ativos fictícia, com dados públicos reais e atualizados,
> que vive só no GitHub.
>
> A empresa tem:
> - Um pipeline de dados: extração automatizada, preparo dos dados por área da empresa e
>   dashboards específicos por tema/objetivo.
> - Uma simulação em cima desses dados: um fluxo de decisão que gera novos processos
>   (issues, PRs, mudanças de política), de forma que o que acontece hoje influencia o
>   que acontece amanhã.
>
> A empresa é dividida em áreas, e cada área enfrenta desafios do dia a dia que afetam as
> outras:
> - Extração: um dia a fonte muda, atrasa ou sai do ar, e a área precisa resolver o problema
>   para que o resto da empresa tenha acesso aos dados.
> - Dashboards: sofre com a falta de atualização dos dados, decide se usa os dados de ontem
>   ou outra estratégia, e leva os números para os executivos.
> - Executivos: tomam decisões e direcionam a empresa a partir dos dashboards.
>
> Cada dia útil, um agente Claude agendado (Scheduled task) executa a empresa.
>
> Eu devo poder ver (e, se possível, acionar) a simulação pelo meu celular Android. Já tenho
> um padrão para isso no repo https://github.com/GloedenJoao/android: seguir esse caminho e,
> se for fácil, evoluí-lo; se não, um aplicativo .apk está ok.
>
> Você decide como isso funciona no GitHub: arquitetura, ferramentas e etapas.
