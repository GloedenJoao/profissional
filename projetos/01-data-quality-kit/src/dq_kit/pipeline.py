"""Validação de pipeline em 3 camadas.

    pré-condições  → os insumos estão em condições de serem processados?
    durante        → os passos intermediários se comportaram como esperado?
                     (ex.: um join não multiplicou linhas)
    pós-condições  → a saída respeita o contrato de quem vai consumi-la?

Cada camada roda todos os seus checks, grava tudo na tabela de controle e só
então decide: se algum check de severidade `error` falhou, o passo para com
`ValidationError`. Checks `warn` ficam registrados, mas não interrompem.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping

from .checks import Check, CheckResult
from .control_table import ControlRecord, ControlTable

PRE, DURING, POST = "pre", "durante", "pos"


class ValidationError(Exception):
    def __init__(self, step: str, layer: str, failures: list[CheckResult]) -> None:
        self.step, self.layer, self.failures = step, layer, failures
        lines = "; ".join(f"{f.check} (observado={f.observed}, {f.detail})" for f in failures)
        super().__init__(f"[{step}/{layer}] {len(failures)} check(s) bloqueante(s) falharam: {lines}")


class StepContext:
    """Entregue ao `transform` para validar resultados intermediários."""

    def __init__(self, pipeline: "Pipeline", step: str) -> None:
        self._pipeline, self._step = pipeline, step

    def checkpoint(self, dataset: str, df: Any, checks: Iterable[Check]) -> Any:
        self._pipeline._validate(self._step, DURING, dataset, df, checks)
        return df


class Pipeline:
    def __init__(
        self,
        name: str,
        control_table: ControlTable | None = None,
        *,
        run_id: str | None = None,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.name = name
        self.control_table = control_table
        self.run_id = run_id or uuid.uuid4().hex[:12]
        self.clock = clock
        self.records: list[ControlRecord] = []

    def step(
        self,
        name: str,
        *,
        inputs: Mapping[str, Any],
        transform: Callable[..., Any],
        pre: Mapping[str, Iterable[Check]] | None = None,
        post: Iterable[Check] | None = None,
        output_name: str | None = None,
    ) -> Any:
        for dataset, checks in (pre or {}).items():
            if dataset not in inputs:
                raise KeyError(f"pré-condição para '{dataset}', que não está entre os inputs {list(inputs)}")
        self._validate_many(name, PRE, {ds: (inputs[ds], checks) for ds, checks in (pre or {}).items()})

        output = transform(StepContext(self, name), **inputs)

        if post:
            self._validate(name, POST, output_name or name, output, post)
        return output

    # -- internos ---------------------------------------------------------

    def _validate(self, step: str, layer: str, dataset: str, df: Any, checks: Iterable[Check]) -> None:
        self._validate_many(step, layer, {dataset: (df, checks)})

    def _validate_many(self, step: str, layer: str, targets: Mapping[str, tuple[Any, Iterable[Check]]]) -> None:
        now = self.clock()
        batch: list[ControlRecord] = []
        for dataset, (df, checks) in targets.items():
            for check in checks:
                batch.append(ControlRecord(self.run_id, self.name, step, layer, dataset, check(df), now))
        self.records.extend(batch)
        if self.control_table is not None:
            self.control_table.write(batch)

        blocking = [r.result for r in batch if not r.result.passed and r.result.severity == "error"]
        if blocking:
            raise ValidationError(step, layer, blocking)

    def report(self) -> str:
        """Resumo legível para log de execução."""
        icon = {"passou": "OK ", "falhou": "ERR"}
        lines = [f"Pipeline {self.name} · run {self.run_id}"]
        for rec in self.records:
            r = rec.result
            mark = icon[r.status] if r.passed or r.severity == "error" else "WRN"
            extra = f" — {r.detail}" if r.detail else ""
            lines.append(f"  [{mark}] {rec.step:<22} {rec.layer:<8} {rec.dataset:<18} {r.check}{extra}")
        return "\n".join(lines)
