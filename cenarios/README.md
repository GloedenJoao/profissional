# Cenários paralelos

Cada pasta aqui é uma Capivara Asset paralela que roda **o mesmo motor e os mesmos times** (`gestora/`)
com dados, estado e memória próprios. O cenário principal ("Dia a dia") continua em `dados/` e `empresa/`
na raiz.

```
cenarios/<id>/
  cenario.json          nome, descrição, data de fundação (`inicio`), `issues` e `automatico`
  empresa/              políticas e diretrizes opcionais do conselho deste cenário
  dados/                escrito só pelo workflow `simulacao.yml` (não edite à mão)
```

Com `"automatico": {"dias_por_execucao": 1, "intervalo": "30 min"}`, o workflow **Simulação · avançar**
roda pela agenda (a cada 30 min) e simula o próximo dia útil com os dados reais daquele dia, sem nunca
passar de ontem; quando alcança o presente, passa a andar um dia por dia útil. Sem o campo, o cenário só
anda quando alguém manda: botão no Actions ou o comentário `/avancar N` na issue de controle.

Os times decidem tudo. Um arquivo em `empresa/decisoes/AAAA-MM-DD.json` é diretriz do conselho: vale
por cima dos times naquele dia. Com `"issues": false`, os alertas do cenário não viram issues (um cenário
que anda a cada meia hora encheria o repositório).

```bash
python -m gestora cenarios                       # lista os cenários
python -m gestora cenarios --pendentes           # automáticos com dia a simular
python -m gestora --cenario 2026 avancar --dias 5
python -m gestora --cenario 2026 validar
```

O acaso de cada cenário usa uma semente própria: a 2026 não sorteia os mesmos incidentes do dia a dia.
