"""CLI: `dq-kit perfil|duplicidades|checar|controle`."""

from __future__ import annotations

import argparse
import json
import sys

from . import tools


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dq-kit", description="Qualidade de dados em arquivos locais.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def source(p: argparse.ArgumentParser) -> None:
        p.add_argument("path", help="CSV, Parquet ou banco SQLite")
        p.add_argument("--table", help="tabela (SQLite)")
        p.add_argument("--query", help="SELECT/WITH (SQLite)")

    source(sub.add_parser("perfil", help="perfil por coluna"))
    p_dup = sub.add_parser("duplicidades", help="diagnóstico de chaves repetidas")
    source(p_dup)
    p_dup.add_argument("--keys", required=True, help="colunas-chave separadas por vírgula")
    p_chk = sub.add_parser("checar", help="roda checks declarados em JSON")
    source(p_chk)
    p_chk.add_argument("--spec", required=True, help="arquivo JSON com a lista de checks")
    p_ctl = sub.add_parser("controle", help="resumo da tabela de controle")
    p_ctl.add_argument("db_path")

    args = parser.parse_args(argv)
    if args.cmd == "perfil":
        out = tools.profile_dataset(args.path, args.table, args.query)
    elif args.cmd == "duplicidades":
        out = tools.duplicates_dataset(args.path, [k.strip() for k in args.keys.split(",")], args.table, args.query)
    elif args.cmd == "checar":
        with open(args.spec, encoding="utf-8") as fh:
            out = tools.check_dataset(args.path, json.load(fh), args.table, args.query)
    else:
        out = tools.control_summary(args.db_path)

    json.dump(out, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")
    if args.cmd == "checar" and not out["aprovado"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
