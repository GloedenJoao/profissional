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

Um cenário só anda quando o dono manda: o botão "Simular próximo dia" do app Android ou do site (que
dispara o workflow **Simulação · avançar** pela API), o botão no Actions ou o comentário `/avancar N` na
issue de controle. Cada avanço simula os dias úteis com os dados reais daqueles dias, sem nunca passar de
ontem.

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
