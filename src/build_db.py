"""Constrói o banco DuckDB (data/voos.duckdb) executando os scripts de sql/ em ordem."""

import sys
import time
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "voos.duckdb"
SQL_DIR = ROOT / "sql"


def main():
    scripts = sorted(SQL_DIR.glob("[0-9][0-9]_*.sql"))
    if not list((ROOT / "data" / "raw").glob("VRA_*.csv")):
        sys.exit("Nenhum CSV em data/raw. Rode antes: python src/download.py")

    con = duckdb.connect(str(DB_PATH))
    # os caminhos nos .sql são relativos à raiz do projeto
    con.execute(f"set file_search_path = '{ROOT.as_posix()}'")
    for script in scripts:
        inicio = time.perf_counter()
        con.execute(script.read_text(encoding="utf-8"))
        print(f"{script.name:<20} ok ({time.perf_counter() - inicio:.1f}s)")

    for tabela in ("stg_voos", "dim_aeroporto", "fct_voos", "vw_voos_pontualidade"):
        n = con.execute(f"select count(*) from {tabela}").fetchone()[0]
        print(f"  {tabela:<22} {n:>10,} linhas")
    con.close()


if __name__ == "__main__":
    main()
