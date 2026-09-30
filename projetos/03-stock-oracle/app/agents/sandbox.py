import ast
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any

from app.agents.strategy_types import StrategyContext, StrategySignal


class StrategySandboxError(ValueError):
    pass


SAFE_BUILTINS: Mapping[str, Any] = MappingProxyType(
    {
        "abs": abs,
        "bool": bool,
        "float": float,
        "int": int,
        "len": len,
        "max": max,
        "min": min,
        "range": range,
        "round": round,
        "sum": sum,
    }
)

BANNED_CALLS = {"eval", "exec", "open", "__import__", "compile", "globals", "locals", "vars", "dir"}
BANNED_NODES = (
    ast.AsyncFunctionDef,
    ast.Attribute,
    ast.Await,
    ast.ClassDef,
    ast.Delete,
    ast.Global,
    ast.Import,
    ast.ImportFrom,
    ast.Lambda,
    ast.Nonlocal,
    ast.Raise,
    ast.Try,
    ast.While,
    ast.With,
    ast.Yield,
    ast.YieldFrom,
)


class StrategyExecutor:
    """Executes trusted local strategy code after a small AST safety pass."""

    def execute(self, code: str, context: StrategyContext) -> StrategySignal:
        tree = ast.parse(code)
        self._validate_tree(tree)
        namespace: dict[str, Any] = {}
        compiled = compile(tree, filename="<strategy>", mode="exec")
        exec(compiled, {"__builtins__": SAFE_BUILTINS}, namespace)
        predict = namespace.get("predict")
        if not callable(predict):
            raise StrategySandboxError("strategy code must define predict(context)")
        result = predict(context.to_sandbox_dict())
        if not isinstance(result, dict):
            raise StrategySandboxError("predict(context) must return a dictionary")
        return StrategySignal.from_mapping(result)

    def _validate_tree(self, tree: ast.AST) -> None:
        has_predict = False
        for node in ast.walk(tree):
            if isinstance(node, BANNED_NODES):
                raise StrategySandboxError(f"{type(node).__name__} is not allowed in strategy code")
            if isinstance(node, ast.Name):
                self._validate_identifier(node.id)
            if isinstance(node, ast.FunctionDef):
                self._validate_identifier(node.name)
                if node.name == "predict":
                    has_predict = True
            if isinstance(node, ast.Call):
                self._validate_call(node)
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if "__" in node.value:
                    raise StrategySandboxError("dunder strings are not allowed in strategy code")
        if not has_predict:
            raise StrategySandboxError("strategy code must define predict(context)")

    @staticmethod
    def _validate_identifier(identifier: str) -> None:
        if "__" in identifier:
            raise StrategySandboxError("dunder identifiers are not allowed in strategy code")
        if identifier in BANNED_CALLS:
            raise StrategySandboxError(f"{identifier} is not allowed in strategy code")

    @staticmethod
    def _validate_call(node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            name = node.func.id
            if name in BANNED_CALLS:
                raise StrategySandboxError(f"{name} is not allowed in strategy code")
            if name not in SAFE_BUILTINS and name != "predict":
                raise StrategySandboxError(f"function call {name} is not allowed in strategy code")
            return
        raise StrategySandboxError("only direct calls to allowed builtins are supported")
