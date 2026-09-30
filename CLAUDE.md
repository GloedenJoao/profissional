# Portfólio profissional

Repositório-vitrine: projetos executáveis em `projetos/`, artefatos de IA em `ia/`, narrativa em `docs/`.

## Regras

- Todo dado é sintético ou público. Nunca adicionar extratos, holerites, bases de empregador ou nomes internos de segmentos/produtos.
- Cada projeto em `projetos/` é independente (`pyproject.toml` próprio) e precisa passar `python -m pytest -q` na sua pasta; a CI roda os três.
- Números citados nos READMEs (testes, commits, PRs, resultados) devem bater com o código e o histórico; ao mudar o código, atualize o README do projeto e a tabela do `README.md` raiz.
- Estudos de caso descrevem o processo real (commits, pivôs, decisões). Não inventar motivação que não esteja registrada.
- Textos em PT-BR; `README.en.md` é o resumo em inglês e acompanha o `README.md`.

## Comandos

```bash
cd projetos/<projeto> && pip install -e ".[dev]" && python -m pytest -q
python -m mensuracao --saida relatorio_exemplo      # em projetos/02-mensuracao-crm: regenera o relatório
python examples/pipeline_aquisicao_pj.py            # em projetos/01-data-quality-kit
```
