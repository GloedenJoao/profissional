"""Acesso às séries reais extraídas, com corte por data (sem olhar o futuro)."""
from __future__ import annotations

import bisect
from datetime import date
from pathlib import Path

from . import armazem, config


class Mercado:
    def __init__(self, pasta: Path | None = None):
        self.pasta = pasta or config.SERIES
        self._series: dict[str, list[tuple[str, float]]] = {}
        self._tesouro: dict[tuple[str, str], list[tuple[str, float, float]]] | None = None

    def serie(self, nome: str) -> list[tuple[str, float]]:
        if nome not in self._series:
            linhas = armazem.ler_serie(nome, self.pasta)
            self._series[nome] = sorted((ln["data"], ln["valor"]) for ln in linhas)
        return self._series[nome]

    def ultimo(self, nome: str, ate: date | str) -> tuple[str, float] | None:
        s = self.serie(nome)
        i = bisect.bisect_right(s, (str(ate), float("inf")))
        return s[i - 1] if i else None

    def historico(self, nome: str, ate: date | str, n: int) -> list[tuple[str, float]]:
        s = self.serie(nome)
        i = bisect.bisect_right(s, (str(ate), float("inf")))
        return s[max(0, i - n):i]

    def ultima_data(self, nome: str) -> str | None:
        if nome == "tesouro":
            datas = [h[-1][0] for h in self.tesouro().values() if h]
            return max(datas, default=None)
        s = self.serie(nome)
        return s[-1][0] if s else None

    # ------------------------------------------------------------ Tesouro
    def tesouro(self) -> dict[tuple[str, str], list[tuple[str, float, float]]]:
        if self._tesouro is None:
            t: dict[tuple[str, str], list[tuple[str, float, float]]] = {}
            for ln in armazem.ler_serie("tesouro", self.pasta):
                t.setdefault((ln["tipo"], ln["vencimento"]), []).append((ln["data"], ln["taxa"], ln["pu"]))
            for v in t.values():
                v.sort()
            self._tesouro = t
        return self._tesouro

    def titulo(self, tipo: str, vencimento: str, ate: date | str) -> tuple[str, float, float] | None:
        h = self.tesouro().get((tipo, vencimento), [])
        i = bisect.bisect_right(h, (str(ate), float("inf"), float("inf")))
        return h[i - 1] if i else None

    def escolher_titulo(self, tipo: str, anos: int, ate: date) -> str | None:
        """Vencimento com prazo mais próximo do alvo entre os títulos com preço até `ate`."""
        alvo = date(ate.year + anos, ate.month, min(ate.day, 28)).isoformat()
        candidatos = []
        for (t, venc), h in self.tesouro().items():
            if t != tipo or venc <= str(ate):
                continue
            if self.titulo(t, venc, ate):
                candidatos.append(venc)
        if not candidatos:
            return None
        return min(candidatos, key=lambda v: abs(date.fromisoformat(v).toordinal() - date.fromisoformat(alvo).toordinal()))
