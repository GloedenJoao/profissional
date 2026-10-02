# Capivara Asset

Gestora fictícia que roda só no GitHub sobre dados públicos reais. A ideia está em `IDEIA.md`;
o manual do dia útil do agente está em `OPERACAO.md`.

- `gestora/`: motor em Python puro (só biblioteca padrão). `python -m gestora --help`.
- `dados/`: escrito apenas pelo workflow `fechamento.yml`. Não edite à mão.
- `empresa/`: intenções (políticas, decisões, diário). Muda por PR.
- `cenarios/<id>/`: cenários paralelos (hoje: `2026`, fundada em 01/01/2026, avançada à mão pelo
  `simulacao.yml`). Mesma estrutura de `dados/` + `empresa/`; `cenarios/<id>/dados/` também não se edita à mão.
  Comandos aceitam `--cenario <id>` (`python -m gestora --cenario 2026 avancar --dias 5`).
- `site/`: a Central (HTML/JS estático, lê `cenarios.json` e o `painel.json` de cada cenário), montada
  por `python -m gestora site _site` e publicada no GitHub Pages.
- Testes: `python -m pytest -q`. Validação de decisões: `python -m gestora validar`.
- Este ambiente não alcança as fontes públicas; extração real só no GitHub Actions.
- Textos, commits e PRs em português.
