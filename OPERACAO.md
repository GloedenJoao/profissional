# Manual do conselho (opcional)

A **Capivara Asset** se toca sozinha: os workflows extraem os dados reais e os times (`gestora/times.py`)
decidem cada dia útil. Ninguém precisa decidir nada. Este manual é para quem quiser fazer o papel do
**conselho** (o João, ou um agente Claude a pedido dele): acompanhar, intervir de vez em quando e cuidar
do que os times não alcançam (código e políticas).

Você **não calcula números** e **não edita `dados/`** nem `cenarios/<id>/dados/`: só os workflows
escrevem ali. O ambiente do agente não alcança as fontes públicas (BCB, Tesouro, Yahoo, B3); só o
Actions alcança.

## Acompanhar

- Site → aba **Ao vivo** do cenário: as reuniões fala por fala. `dados/briefing.md` tem o resumo do
  último dia, com as decisões dos times.
- O fechamento do dia a dia roda seg–sex às 08h; a Simulação 2026 anda a cada 30 min. Se um deles falhar,
  aparece como tarefa urgente na Central e (no dia a dia) como issue "Fechamento falhou".

## Intervir (diretriz do conselho)

Crie `empresa/decisoes/H.json` (H = próximo dia útil; no cenário, `cenarios/<id>/empresa/decisoes/`).
O botão "Intervir" do site abre o arquivo já preenchido. Tudo é opcional: **apague o que não quiser
impor**, porque o que estiver no arquivo vale por cima do time naquele dia.

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

Valores aceitos: ações `aguardar`, `fonte_alternativa`, `corrigir_conector`, `escalar`; estratégias
`usar_ontem`, `estimar`, `suspender`; alocação somando 1 dentro de `empresa/politicas.json`; equipe 1–8;
orçamento 0–5.000. Antes de subir: `python -m pytest -q && python -m gestora validar`.

## O que só o conselho faz

1. **Falha real de conector** (`falha_real`, "⚠️ Falha REAL" no briefing): os times só conseguem esperar.
   Corrija `gestora/fontes.py` com um teste em `tests/test_fontes.py` num PR "Extração: corrige conector X".
2. **Políticas** (`empresa/politicas.json`: limites da carteira, estratégia padrão, tolerâncias): PR com
   rótulo `politica` e a justificativa.
3. **Regras dos times** (`gestora/times.py`): se um time decide mal de forma sistemática, mude a regra
   num PR de código com teste em `tests/test_times.py`.

Nada aqui é recomendação de investimento: a empresa e o fundo são fictícios.
