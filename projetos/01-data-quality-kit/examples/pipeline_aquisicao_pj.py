"""Exemplo ponta a ponta: pipeline de conversão de leads PJ em contas.

Roda duas vezes o mesmo pipeline:
1. com dados limpos → todas as camadas passam;
2. com um problema clássico de origem (conta cadastrada duas vezes com
   segmentos diferentes) → a camada "durante" detecta o fan-out do join
   antes de a tabela final ser gravada, e o diagnóstico de duplicidade
   aponta a coluna culpada.

Dados 100% sintéticos.
    python examples/pipeline_aquisicao_pj.py
"""

from __future__ import annotations

import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from dq_kit import ControlTable, Pipeline, ValidationError, checks as C, find_duplicates

CANAIS = ["crm", "midia_paga", "mgm", "gerente"]


def gerar_dados(seed: int = 7, n_leads: int = 500, com_problema: bool = False) -> tuple[pd.DataFrame, pd.DataFrame]:
    rnd = random.Random(seed)
    inicio = date(2026, 6, 1)
    leads = pd.DataFrame(
        {
            "cnpj": [f"{i:014d}" for i in range(n_leads)],
            "canal": [rnd.choice(CANAIS) for _ in range(n_leads)],
            "dt_lead": [inicio + timedelta(days=rnd.randint(0, 60)) for _ in range(n_leads)],
        }
    )
    convertidos = leads.sample(frac=0.3, random_state=seed)
    contas = pd.DataFrame(
        {
            "cnpj": convertidos["cnpj"].values,
            "dt_abertura": [d + timedelta(days=rnd.randint(0, 20)) for d in convertidos["dt_lead"]],
            "segmento": [rnd.choice(["pequena", "media", "grande"]) for _ in range(len(convertidos))],
        }
    )
    if com_problema:  # a mesma conta chega duas vezes da origem, com segmentos diferentes
        repetidas = contas.head(4).assign(segmento="corporate")
        contas = pd.concat([contas, repetidas], ignore_index=True)
    return leads, contas


def consolidar(ctx, leads: pd.DataFrame, contas: pd.DataFrame) -> pd.DataFrame:
    base = leads.merge(contas, on="cnpj", how="left")
    ctx.checkpoint("join_leads_contas", base, [C.row_count_equals(len(leads))])

    base["convertido"] = base["dt_abertura"].notna()
    base["dias_para_conversao"] = (
        pd.to_datetime(base["dt_abertura"]) - pd.to_datetime(base["dt_lead"])
    ).dt.days
    return base


def rodar(pipeline: Pipeline, leads: pd.DataFrame, contas: pd.DataFrame) -> pd.DataFrame:
    return pipeline.step(
        "consolida_conversoes",
        inputs={"leads": leads, "contas": contas},
        transform=consolidar,
        pre={
            "leads": [C.row_count_between(min_rows=1), C.not_null("cnpj"), C.unique("cnpj"),
                      C.accepted_values("canal", CANAIS)],
            "contas": [C.not_null(["cnpj", "dt_abertura"])],
        },
        post=[
            C.unique("cnpj"),
            C.values_between("dias_para_conversao", min_value=0, max_value=30).as_warning(),
        ],
        output_name="fato_conversao_pj",
    )


def main(db_path: str | Path = "controle_dq.db") -> None:
    ct = ControlTable(db_path)

    print("== Execução 1: dados limpos ==")
    p1 = Pipeline("aquisicao_pj", ct)
    fato = rodar(p1, *gerar_dados())
    print(p1.report())
    print(f"-> fato_conversao_pj gravada com {len(fato)} linhas, taxa de conversão {fato['convertido'].mean():.1%}\n")

    print("== Execução 2: origem com contas duplicadas ==")
    leads, contas = gerar_dados(com_problema=True)
    p2 = Pipeline("aquisicao_pj", ct)
    try:
        rodar(p2, leads, contas)
    except ValidationError as exc:
        print(p2.report())
        print(f"-> execução interrompida antes de gravar: {exc}\n")
        diag = find_duplicates(contas, ["cnpj"])
        print("Diagnóstico da origem 'contas':", diag.summary())

    print("\nTabela de controle (resumo por execução e camada):")
    for row in ct.summary():
        print(" ", row)
    ct.close()


if __name__ == "__main__":
    main()
