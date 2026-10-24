"""Baixa os arquivos mensais do VRA (Voo Regular Ativo) publicados pela ANAC.

Uso:
    python src/download.py                      # out/2025 a set/2026 (padrão)
    python src/download.py --inicio 2024-01 --fim 2024-12
"""

import argparse
from pathlib import Path

import requests
from tqdm import tqdm

BASE_URL = "https://siros.anac.gov.br/siros/registros/diversos/vra/{ano}/VRA_{ano}_{mes:02d}.csv"
RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"


def meses(inicio: str, fim: str):
    ano, mes = map(int, inicio.split("-"))
    ano_fim, mes_fim = map(int, fim.split("-"))
    while (ano, mes) <= (ano_fim, mes_fim):
        yield ano, mes
        mes += 1
        if mes > 12:
            ano, mes = ano + 1, 1


def baixar(ano: int, mes: int, forcar: bool = False) -> Path:
    destino = RAW_DIR / f"VRA_{ano}_{mes:02d}.csv"
    if destino.exists() and not forcar:
        return destino

    url = BASE_URL.format(ano=ano, mes=mes)
    with requests.get(url, stream=True, timeout=60) as r:
        r.raise_for_status()
        tmp = destino.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
        tmp.replace(destino)
    return destino


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inicio", default="2025-10", help="AAAA-MM")
    parser.add_argument("--fim", default="2026-09", help="AAAA-MM")
    parser.add_argument("--forcar", action="store_true", help="baixa de novo mesmo se já existir")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    periodo = list(meses(args.inicio, args.fim))
    for ano, mes in tqdm(periodo, desc="Baixando VRA"):
        baixar(ano, mes, args.forcar)
    print(f"{len(periodo)} arquivos em {RAW_DIR}")


if __name__ == "__main__":
    main()
