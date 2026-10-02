# Simulação

Cada pasta aqui é uma Capivara Asset que roda **o mesmo motor e os mesmos times** (`gestora/`) do Experimento,
com dados, estado e memória próprios. Hoje há uma: `2026`, a mesma empresa refazendo 2026 desde 1º de janeiro, para
testar o experimento (veja `IDEIA.md`). O Experimento continua em `dados/` e `empresa/` na raiz.

```
cenarios/<id>/
  cenario.json          nome, descrição e data de fundação (`inicio`)
  empresa/              políticas e diretrizes opcionais do conselho desta simulação
  dados/                escrito só pelo workflow `simulacao.yml` (não edite à mão)
```

A simulação só anda quando o dono manda: o botão "Simular próximo dia" do site ou do app (dispara o workflow
**Simulação · avançar** pela API e acompanha cada passo), o botão "Run workflow" ou o comentário `/avancar N` na
issue de controle. Cada avanço simula os dias úteis com os dados reais daqueles dias, sem nunca passar de ontem e sem
olhar o futuro dentro do dia. `recomecar: true` (botão "Recomeçar do zero" na aba Validação) volta a simulação à
fundação, com as regras de agora: é assim que se testa uma regra nova antes de levá-la ao experimento.

Um arquivo em `empresa/decisoes/AAAA-MM-DD.json` é diretriz do conselho: vale por cima dos times naquele dia. Os
alertas da simulação não viram issues (`"issues": false` por padrão).

```bash
python -m gestora cenarios                          # lista os cenários
python -m gestora --cenario 2026 avancar --dias 5   # precisa das fontes (ou --sem-extracao)
python -m gestora --cenario 2026 recomecar
python -m gestora --cenario 2026 validar
python -m gestora --cenario 2026 auditar
```

O teste de estresse de cada cenário usa uma semente própria: a simulação não sorteia as mesmas falhas do experimento.
