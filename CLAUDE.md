# Capivara Asset

Gestora fictícia que roda só no GitHub sobre dados públicos reais. A ideia está em `IDEIA.md`.
Quem decide são os times (`gestora/times.py`), dentro do motor; o dono só assiste (aba Ao vivo do site)
e, se quiser, intervém com uma diretriz do conselho (`OPERACAO.md`).

- `gestora/`: motor em Python puro (só biblioteca padrão). `python -m gestora --help`.
- `dados/`: escrito apenas pelo workflow `fechamento.yml`. Não edite à mão.
- `empresa/`: políticas e diretrizes opcionais do conselho (`decisoes/`). Muda por PR.
- `cenarios/<id>/`: cenários paralelos (hoje: `2026`, fundada em 01/01/2026, anda sozinha a cada 30 min
  pelo `simulacao.yml` enquanto houver dia a simular; ritmo em `cenario.json → automatico`). Mesma estrutura de `dados/` + `empresa/`; `cenarios/<id>/dados/` também não se edita à mão.
  Comandos aceitam `--cenario <id>` (`python -m gestora --cenario 2026 avancar --dias 5`).
- `site/`: a Central e o modo Ao vivo (HTML/JS estático: `cenarios.json`, `painel.json` e `dias/*.json` com
  a ata de cada cenário), montada por `python -m gestora site _site` e publicada no GitHub Pages. A página se
  atualiza sozinha via `versao.json`; não use nomes de arquivo sem `?v=__CODIGO__` no `index.html`.
- Testes: `python -m pytest -q`. Validação de decisões: `python -m gestora validar`.
- Este ambiente não alcança as fontes públicas; extração real só no GitHub Actions.
- Textos, commits e PRs em português.
