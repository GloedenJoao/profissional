"""Servidor MCP: dá a um agente de IA (Claude Code, Claude Desktop...) as
ferramentas de qualidade de dados deste pacote.

Uso típico: o agente escreve uma query nova, e antes de propor o PR chama
`perfil_dataset` e `checar_dataset` sobre uma amostra para provar que a saída
respeita o contrato — em vez de só afirmar que "deve estar certo".

Rodar:  dq-kit-mcp          (stdio)
Config (Claude Code):  claude mcp add dq-kit -- dq-kit-mcp
"""

from __future__ import annotations

from typing import Any

from . import tools

try:  # SDK mcp >= 2
    from mcp.server.mcpserver import MCPServer as _Server
except ImportError:  # SDK mcp 1.x
    from mcp.server.fastmcp import FastMCP as _Server

server = _Server(
    "dq-kit",
    instructions=(
        "Ferramentas de qualidade de dados sobre arquivos locais (CSV, Parquet, SQLite). "
        "Use perfil_dataset antes de propor checks; use checar_dataset para validar uma saída; "
        "use duplicidades_dataset para diagnosticar chaves repetidas. Nenhuma ferramenta altera dados."
    ),
)


@server.tool()
def perfil_dataset(path: str, table: str | None = None, query: str | None = None) -> dict[str, Any]:
    """Perfil por coluna: tipo, % nulos, distintos, min/max e se é candidata a chave."""
    return tools.profile_dataset(path, table, query)


@server.tool()
def duplicidades_dataset(path: str, keys: list[str], table: str | None = None,
                         query: str | None = None) -> dict[str, Any]:
    """Grupos de chave repetida, classificados em 'exata' ou 'divergente' com as colunas que divergem."""
    return tools.duplicates_dataset(path, keys, table, query)


@server.tool()
def checar_dataset(path: str, specs: list[dict[str, Any]], table: str | None = None,
                   query: str | None = None) -> dict[str, Any]:
    """Roda checks declarativos. Ex. de spec: {"type": "unique", "keys": ["id"]},
    {"type": "not_null", "columns": ["id", "dt"]}, {"type": "values_between", "column": "valor", "min_value": 0}."""
    return tools.check_dataset(path, specs, table, query)


@server.tool()
def resumo_controle(db_path: str) -> list[dict[str, Any]]:
    """Resumo da tabela de controle: checks que passaram/falharam por execução e camada."""
    return tools.control_summary(db_path)


def main() -> None:
    server.run()


if __name__ == "__main__":
    main()
