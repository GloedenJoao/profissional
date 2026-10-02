# Manual do conselho (opcional)

A **Capivara Asset** se toca sozinha: os workflows extraem os dados reais e os times (`gestora/times.py`) decidem
cada dia útil, etapa por etapa, gravando o rastro completo. Ninguém precisa decidir nada. Este manual é para quem
quiser fazer o papel do **conselho** (o João, ou um agente Claude a pedido dele): acompanhar, intervir de vez em
quando e cuidar do que os times não alcançam (código e políticas).

Você **não calcula números** e **não edita `dados/`** nem `cenarios/<id>/dados/`: só os workflows escrevem ali. O
ambiente do agente não alcança as fontes públicas (BCB, Tesouro, Yahoo, B3); só o Actions alcança. Para reproduzir um
dia sem rede, use as séries já gravadas: `python -m gestora reprocessar --todos` numa cópia de trabalho (não suba os
dados gerados).

## Acompanhar

- Site → **Experimento** ou **Simulação** → **Dia**: as sete etapas do dia, cada fala com "Ver as contas". O botão
  **Assistir** toca o dia etapa por etapa.
- **Validação**: as 8 verificações de todos os dias, a carteira de referência (valor das decisões) e a saúde do
  processo. Uma verificação que falha é bug do motor: o fechamento não publica e abre a issue "Fechamento falhou".
- `dados/briefing.md` (e `cenarios/2026/dados/briefing.md`) resume o último dia em texto.

## Intervir (diretriz do conselho)

Crie `empresa/decisoes/H.json` (H = próximo dia útil; na simulação, `cenarios/2026/empresa/decisoes/`). Tudo é
opcional: **apague o que não quiser impor**, porque o que estiver no arquivo vale por cima do time naquele dia e o
rastro registra quem mandou.

```json
{
  "data": "2026-10-02",
  "autor": "conselho",
  "extracao": {"acoes": {"INC-0007": "fonte_alternativa"}},
  "dashboards": {"estrategias": {"dolar": "estimar"}},
  "executivos": {
    "alocacao": {"caixa": 0.45, "prefixado": 0.15, "inflacao": 0.15, "dolar": 0.1, "bolsa": 0.15},
    "equipe_extracao": 3,
    "orcamento_extracao_dia": 1000,
    "justificativa": "Por que o conselho mandou."
  }
}
```

Valores aceitos: ações `aguardar`, `fonte_alternativa`, `corrigir_conector`, `escalar`; estratégias `usar_ontem`,
`estimar`, `suspender`; alocação somando 1 dentro de `politicas.json`; equipe 1–8; orçamento 0–5.000. Antes de subir:
`python -m pytest -q && python -m gestora validar`.

## O que só o conselho faz

1. **Falha real** (incidente `falha_real`, "Problema de verdade" na Extração): a fonte real não entregou o esperado
   ou o conector quebrou. Se for o conector, corrija `gestora/fontes.py` com um teste em `tests/test_fontes.py` num
   PR "Extração: corrige conector X".
2. **Políticas** (`politicas.json`: limites da carteira, modelo de alocação, teste de estresse, cotistas,
   tolerâncias): PR com rótulo `politica` e a justificativa. No experimento a mudança vale dali em diante; para
   testar antes, mude a política da simulação e use **Validação → Recomeçar do zero**.
3. **Regras dos times e do motor** (`gestora/times.py`, `gestora/simulacao.py`): PR de código com teste. Se a
   mudança altera resultados, suba `VERSAO_MOTOR` em `simulacao.py`: o workflow `publicar.yml` refaz o histórico dos
   dois cenários com o motor novo, para o site nunca misturar dados de um motor com telas de outro.

Nada aqui é recomendação de investimento: a empresa e o fundo são fictícios.
