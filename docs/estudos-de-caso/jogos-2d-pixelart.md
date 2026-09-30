# Estudo de caso: 7 jogos em Godot, desenvolvidos com agentes

**Período:** ago/2026 · **Repositório público:** [GloedenJoao/jogos-2d-pixelart](https://github.com/GloedenJoao/jogos-2d-pixelart)

## Por que está num portfólio de dados

Não é um projeto de dados, e não precisa ser. É o melhor registro de **como eu conduzo um projeto longo com agentes de IA**: planejamento documentado, escopo que cresce um sistema por vez, testes automatizados em tudo e decisões registradas junto com o motivo.

## O desenho do projeto

- **Objetivo declarado:** aprender uma engine do zero (Godot 4, GDScript) com jogos cada vez mais complexos, até publicar no itch.io.
- **[Plano de 90 dias](https://github.com/GloedenJoao/jogos-2d-pixelart/blob/main/docs/plano-90-dias.md)** escrito antes do primeiro jogo, com cada projeto introduzindo 1–2 sistemas novos.
- **Framework compartilhado** (addon Godot) com gerenciador de cenas, save/load, state machine, áudio e tema de UI. Cada jogo novo começa com isso pronto.

| # | Jogo | Sistema novo | Testes headless |
|---|---|---|---:|
| — | framework | cenas, save, state machine, áudio, UI | 16 |
| 1 | Blackjack | state machine de fases, HUD, persistência | 28 |
| 2 | Roguelike de caverna | geração procedural, IA de inimigo, meta-progressão | 97 |
| 3 | Andarilho das Eras (platformer) | física, animação, câmera, checkpoints | 80 |
| 4 | Eras da Civilização (idle) | economia, produção automática, progresso offline | 104 |
| 5 | Colônia Viva | moradores como agentes com IA de utilidade | 172 |
| 5 V2 | Colônia Viva (refeito) | sprites modulares, A* com trilhas, 7 ações autônomas | 271 |
| 7 | Reino em Construção | city-builder: recursos finitos, energia, população, névoa | 297 asserções |

## Práticas que transfiro para o trabalho

- **Testes que jogam o jogo.** No platformer, as fases são mapas ASCII e um bot percorre cada fase nos testes. Se um mapa novo ficar impossível, o teste quebra antes de alguém jogar. É o mesmo princípio das pós-condições de um pipeline.
- **Validação visual automatizada.** Cada projeto tem um script que gera screenshots dos cenários-chave sem clicar em nada, para revisar o visual sem abrir o editor.
- **Calibração por medição.** Constantes de balanceamento foram ajustadas rodando scripts de calibração (ex.: `calibrate_farm.gd`) e não no chute. Um bug de fila de contratação (a vila travava em população 2) foi achado pela suíte de testes.
- **Decisões registradas.** Trocas de escopo ficam escritas com o motivo, por exemplo: puzzle → blackjack, pivô de Travian/Factorio para Timberborn, combate fora do escopo, desbloqueio automático substituído por construção manual depois de jogar e sentir falta de agência.
- **Refazer quando vale a pena.** O Projeto 5 foi apagado e refeito (5 V2) quando os moradores não ficaram bons. Isso está no histórico, não escondido.
- **31 PRs**, um por fase/feature, cada um com mensagem descritiva (`feat(reino): Mina + Forja — terceira cadeia de recurso`).

## Estado

Sete jogos jogáveis com testes; a publicação no itch.io é o próximo passo do plano. É um projeto de estudo e não precisa estar "terminado" para mostrar o processo.
