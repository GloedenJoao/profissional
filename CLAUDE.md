# Capivara Asset

Gestora fictícia que roda só no GitHub sobre dados públicos reais. A ideia desenvolvida está em `IDEIA.md` (leia
antes de mudar motor ou telas). São duas coisas com o mesmo motor: o **Experimento** (`dados/` + `empresa/`, anda
sozinho seg–sex 08h) e a **Simulação** (`cenarios/2026/`, refaz 2026 um dia por clique para testar o experimento).
Quem decide são os times (`gestora/times.py`); o dono assiste no site e, se quiser, intervém (`OPERACAO.md`).

- `gestora/`: motor em Python puro (só biblioteca padrão). `python -m gestora --help`.
  - `simulacao.py`: as sete etapas do dia (Herança → Extração → Dashboards → Comitê → Fundo → Empresa →
    Verificações). Cada etapa grava no rastro (`rastro.py`) entradas, regra, conta e origem de cada número; as falas
    saem do rastro e apontam para o bloco que as sustenta. Não escreva fala sem número de um bloco por trás.
  - Nada do futuro: as reuniões só usam o publicado até as 08h (`config.PUBLICACAO`); a marcação, preços até o dia.
  - Mudou o resultado do motor? Suba `VERSAO_MOTOR`: fechamento, simulação e `publicar.yml` refazem o histórico.
- `dados/` e `cenarios/<id>/dados/`: escritos apenas pelos workflows. Não edite à mão nem suba dados gerados
  localmente (`reprocessar` local é só para conferir).
- `empresa/` e `cenarios/<id>/empresa/`: políticas (todos os parâmetros do modelo) e diretrizes opcionais. Muda por PR.
- Não avance a simulação por conta própria: só o dono manda ("Simular próximo dia" no site/app).
- `site/`: HTML/JS estático (`cenarios.json`, `painel.json`, `dias/*.json`), montado por `python -m gestora site
  _site`. A página se atualiza sozinha via `versao.json`; não use nomes de arquivo sem `?v=__CODIGO__` no
  `index.html`. O `painel.json` mantém os campos antigos (o app Android lê).
- Testes: `python -m pytest -q`. Validação: `python -m gestora validar`. Auditoria: `python -m gestora auditar --todos`.
- Este ambiente não alcança as fontes públicas; extração real só no GitHub Actions.
- Textos, commits e PRs em português.
