# Cenários paralelos

Cada pasta aqui é uma Capivara Asset paralela que roda **o mesmo motor** (`gestora/`) com dados,
estado e decisões próprios. O cenário principal ("ao vivo") continua em `dados/` e `empresa/` na raiz.

```
cenarios/<id>/
  cenario.json          nome, descrição, data de fundação (`inicio`) e modo
  empresa/              políticas, decisões e diário deste cenário (mudam por commit ou PR)
  dados/                escrito só pelo workflow `simulacao.yml` (não edite à mão)
```

Um cenário `manual` só anda quando alguém manda: o workflow **Simulação · avançar** (botão no Actions,
ou o comentário `/avancar N` na issue de controle do cenário) simula os próximos N dias úteis com os
dados reais daqueles dias, sem nunca passar de ontem. Sem arquivo em `empresa/decisoes/`, o fundo segue
no piloto automático.

```bash
python -m gestora cenarios                       # lista os cenários
python -m gestora --cenario 2026 avancar --dias 5
python -m gestora --cenario 2026 validar
```

O acaso de cada cenário usa uma semente própria: a 2026 não sorteia os mesmos incidentes do ao vivo.
