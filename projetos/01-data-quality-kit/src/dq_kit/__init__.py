"""dq_kit — validação de pipelines de dados em 3 camadas, com tabela de controle."""

from . import checks
from .checks import Check, CheckResult, from_spec, run_checks
from .control_table import ControlTable, hive_ddl
from .duplicates import DuplicateReport, find_duplicates
from .pipeline import Pipeline, ValidationError
from .profiling import load, profile

__all__ = [
    "Check", "CheckResult", "ControlTable", "DuplicateReport", "Pipeline", "ValidationError",
    "checks", "find_duplicates", "from_spec", "hive_ddl", "load", "profile", "run_checks",
]
__version__ = "0.1.0"
