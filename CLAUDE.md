# Capivara Asset

Gestora fictícia que roda só no GitHub sobre dados públicos reais. A ideia está em `IDEIA.md`;
o manual do dia útil do agente está em `OPERACAO.md`.

- `gestora/`: motor em Python puro (só biblioteca padrão). `python -m gestora --help`.
- `dados/`: escrito apenas pelo workflow `fechamento.yml`. Não edite à mão.
- `empresa/`: intenções (políticas, decisões, diário). Muda por PR.
- `site/`: painéis (HTML/JS estático, lê `painel.json`), publicado no GitHub Pages.
- Testes: `python -m pytest -q`. Validação de decisões: `python -m gestora validar`.
- Este ambiente não alcança as fontes públicas; extração real só no GitHub Actions.
- Textos, commits e PRs em português.
