"""Comandos de texto vindos de comentários em issues de controle (ex.: `/avancar 5`)."""
from __future__ import annotations

import re
from datetime import date, datetime

MAX_DIAS = 120


def interpretar(texto: str) -> dict:
    """`/avancar`, `/avancar 5`, `/avancar ate 2026-03-31` ou `/avancar até 31/03/2026`.

    Devolve {"dias": int} ou {"ate": "AAAA-MM-DD"}; levanta ValueError se não entender."""
    linha = (texto or "").strip().splitlines()[0].strip() if (texto or "").strip() else ""
    m = re.fullmatch(r"/avan[cç]ar(?:\s+(.*))?", linha, flags=re.IGNORECASE)
    if not m:
        raise ValueError("o comentário precisa começar com /avancar")
    resto = (m.group(1) or "").strip().lower()
    resto = re.sub(r"^(at[eé]|para)\s+", "", resto)
    if not resto:
        return {"dias": 1}
    if re.fullmatch(r"\d{1,3}", resto):
        dias = int(resto)
        if not 1 <= dias <= MAX_DIAS:
            raise ValueError(f"avance entre 1 e {MAX_DIAS} dias úteis por vez")
        return {"dias": dias}
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return {"ate": datetime.strptime(resto, formato).date().isoformat()}
        except ValueError:
            pass
    raise ValueError(f"não entendi {resto!r}: use /avancar, /avancar 5 ou /avancar ate 2026-03-31")


def alvo(base: date, dias: int | None, ate: date | None, limite: date, proximo) -> date:
    """Data até onde avançar: N dias úteis depois de `base` ou a data pedida, nunca depois de `limite`."""
    if ate is None:
        ate = base
        for _ in range(dias or 1):
            ate = proximo(ate)
    return min(ate, limite)
