"""Gera uma base sintética de aquisição de clientes PJ em SQLite.

A graça de simular é conhecer a verdade: o efeito real da campanha de CRM é
um parâmetro (`lift_real`). Assim dá para verificar se a mensuração
(grupo de controle, atribuição) recupera o número certo — e mostrar onde
métodos ingênuos erram.

Modelo:
- prospects PJ elegíveis a uma campanha; 10% sorteados como grupo de controle
  (não recebem a comunicação);
- todos podem ser tocados por outros canais (mídia paga, MGM, gerente);
- conversão de base `taxa_base` para todos, espalhada pela janela, e
  `lift_real` adicional só para quem recebeu o CRM, nos dias após o disparo;
- toques de CRM acontecem para todo o grupo tratamento, converta ou não.
"""

from __future__ import annotations

import random
import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

SCHEMA = """
CREATE TABLE clientes (cliente_id INTEGER PRIMARY KEY, porte TEXT, regiao TEXT);
CREATE TABLE canais (canal TEXT PRIMARY KEY, prioridade INTEGER, descricao TEXT);
CREATE TABLE campanhas (campanha_id INTEGER PRIMARY KEY, nome TEXT, canal TEXT, dt_inicio TEXT, dt_fim TEXT);
CREATE TABLE publico_campanha (campanha_id INTEGER, cliente_id INTEGER, grupo TEXT CHECK (grupo IN ('tratamento','controle')));
CREATE TABLE toques (cliente_id INTEGER, canal TEXT, dt_toque TEXT);
CREATE TABLE conversoes (cliente_id INTEGER, dt_conversao TEXT, produto TEXT);
"""

# prioridade de desempate quando dois toques caem no mesmo dia (1 = vence)
CANAIS = [
    ("gerente", 1, "Contato humano do gerente de relacionamento"),
    ("mgm", 2, "Indicação (member get member)"),
    ("crm", 3, "Comunicação da régua de CRM (e-mail/push/SMS)"),
    ("midia_paga", 4, "Tráfego pago"),
]


@dataclass(frozen=True)
class Parametros:
    n_clientes: int = 20_000
    pct_controle: float = 0.10
    taxa_base: float = 0.040
    lift_real: float = 0.015
    janela_dias: int = 30
    inicio: date = date(2026, 7, 1)
    seed: int = 42


def gerar(caminho: str | Path, p: Parametros = Parametros()) -> Path:
    caminho = Path(caminho)
    caminho.unlink(missing_ok=True)
    rnd = random.Random(p.seed)
    fim_envio = p.inicio + timedelta(days=6)

    clientes, publico, toques, conversoes = [], [], [], []
    for cid in range(1, p.n_clientes + 1):
        clientes.append((cid, rnd.choice(["micro", "pequena", "media"]), rnd.choice(["SE", "S", "NE", "CO", "N"])))
        grupo = "controle" if rnd.random() < p.pct_controle else "tratamento"
        publico.append((1, cid, grupo))

        dt_crm = None
        if grupo == "tratamento":
            dt_crm = p.inicio + timedelta(days=rnd.randint(0, 6))
            toques.append((cid, "crm", dt_crm.isoformat()))

        # outros canais atingem qualquer cliente, independentemente do grupo
        for canal, prob in (("midia_paga", 0.25), ("mgm", 0.03), ("gerente", 0.05)):
            if rnd.random() < prob:
                toques.append((cid, canal, (p.inicio + timedelta(days=rnd.randint(-10, p.janela_dias))).isoformat()))

        # conversão de base: acontece com ou sem campanha, espalhada pela janela;
        # conversão incremental: só no tratamento, nos dias seguintes ao CRM
        u = rnd.random()
        dt_conv = None
        if u < p.taxa_base:
            dt_conv = p.inicio + timedelta(days=rnd.randint(0, p.janela_dias - 1))
        elif dt_crm is not None and u < p.taxa_base + p.lift_real:
            dt_conv = dt_crm + timedelta(days=rnd.randint(0, 14))
        if dt_conv is not None:
            conversoes.append((cid, dt_conv.isoformat(), rnd.choice(["conta_pj", "conta_pj", "maquininha"])))

    with sqlite3.connect(caminho) as conn:
        conn.executescript(SCHEMA)
        conn.executemany("INSERT INTO canais VALUES (?,?,?)", CANAIS)
        conn.execute(
            "INSERT INTO campanhas VALUES (1, 'Boas-vindas PJ — julho', 'crm', ?, ?)",
            (p.inicio.isoformat(), fim_envio.isoformat()),
        )
        conn.executemany("INSERT INTO clientes VALUES (?,?,?)", clientes)
        conn.executemany("INSERT INTO publico_campanha VALUES (?,?,?)", publico)
        conn.executemany("INSERT INTO toques VALUES (?,?,?)", toques)
        conn.executemany("INSERT INTO conversoes VALUES (?,?,?)", conversoes)
    return caminho
