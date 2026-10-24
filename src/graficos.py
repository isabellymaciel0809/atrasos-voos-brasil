"""Estilo visual e funções de gráfico usadas no notebook de análise."""

from pathlib import Path

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
from matplotlib.colors import LinearSegmentedColormap

FIG_DIR = Path(__file__).resolve().parents[1] / "reports" / "figures"

# Paleta (validada para daltonismo): cor por entidade, nunca por posição no ranking.
AZUL = "#2a78d6"
LARANJA = "#eb6834"
VERDE_AGUA = "#1baf7a"
CINZA = "#b9b8b2"
TEXTO = "#0b0b0b"
TEXTO_2 = "#52514e"
GRADE = "#e6e5e0"
FUNDO = "#fcfcfb"

MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]

CORES_EMPRESA ={"LATAM": AZUL, "Azul": LARANJA, "Gol": VERDE_AGUA, "Outras": CINZA}

RAMPA_AZUL = LinearSegmentedColormap.from_list(
    "azul", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
)


def aplicar_estilo():
    plt.rcParams.update({
        "figure.facecolor": FUNDO,
        "axes.facecolor": FUNDO,
        "savefig.facecolor": FUNDO,
        "figure.dpi": 110,
        "savefig.dpi": 160,
        "font.family": "DejaVu Sans",
        "font.size": 10,
        "axes.edgecolor": GRADE,
        "axes.labelcolor": TEXTO_2,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlecolor": TEXTO,
        "axes.titlelocation": "left",
        "axes.titlepad": 22,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": GRADE,
        "grid.linewidth": 0.8,
        "axes.axisbelow": True,
        "xtick.color": TEXTO_2,
        "ytick.color": TEXTO_2,
        "xtick.major.size": 0,
        "ytick.major.size": 0,
        "legend.frameon": False,
    })


def _subtitulo(ax, texto):
    ax.text(0, 1.02, texto, transform=ax.transAxes, color=TEXTO_2, fontsize=9.5, va="bottom")


def _fonte(fig):
    fig.text(0.01, 0.005, "Fonte: ANAC - Voo Regular Ativo (VRA), out/2025 a set/2026. "
             "Atraso = chegada > 15 min após o previsto.", color=TEXTO_2, fontsize=7.5)


def salvar(fig, nome):
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    _fonte(fig)
    fig.savefig(FIG_DIR / f"{nome}.png", bbox_inches="tight")
    return fig


def pct_axis(ax, eixo="y"):
    fmt = mtick.PercentFormatter(1, decimals=0)
    (ax.yaxis if eixo == "y" else ax.xaxis).set_major_formatter(fmt)


def ranking_aeroportos(df, destaque="SBGR", media=None):
    """Barras horizontais: % de chegadas atrasadas por aeroporto de origem."""
    df = df.sort_values("pct_atraso")
    fig, ax = plt.subplots(figsize=(8, 7))
    cores = [LARANJA if i == destaque else CINZA for i in df["origem_icao"]]
    rotulos = df["origem_cidade"].str.title() + " (" + df["origem_icao"] + ")"
    ax.barh(rotulos, df["pct_atraso"], color=cores, height=0.7)
    ax.grid(axis="y", visible=False)
    pct_axis(ax, "x")
    for y, (v, icao) in enumerate(zip(df["pct_atraso"], df["origem_icao"])):
        if icao == destaque or y >= len(df) - 3 or y < 2:
            ax.text(v + 0.003, y, f"{v:.1%}", va="center", fontsize=8.5, color=TEXTO)
    if media is not None:
        ax.axvline(media, color=TEXTO_2, linewidth=1)
        ax.text(media, len(df) - 0.4, f" média Brasil {media:.1%}", color=TEXTO_2, fontsize=8.5)
    ax.set_title("Guarulhos é o gargalo da aviação doméstica")
    _subtitulo(ax, "% de voos que chegaram atrasados, por aeroporto de origem (mín. 5 mil voos)")
    return fig


def atraso_por_hora(df):
    """Barras verticais: % de atraso por hora prevista de partida."""
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.bar(df["hora"], df["pct_atraso"], color=AZUL, width=0.8)
    ax.set_xticks(range(0, 24, 2), [f"{h}h" for h in range(0, 24, 2)])
    ax.grid(axis="x", visible=False)
    pct_axis(ax)
    ax.set_xlabel("Hora prevista de partida")
    manha = df.loc[df["hora"].between(5, 6), "pct_atraso"].mean()
    noite = df.loc[df["hora"].between(18, 19), "pct_atraso"].mean()
    ax.annotate(f"5h-6h: {manha:.0%}", xy=(5.5, manha), xytext=(2, manha + 0.08),
                color=TEXTO, fontsize=9, arrowprops=dict(arrowstyle="-", color=TEXTO_2))
    ax.annotate(f"18h-19h: {noite:.0%}", xy=(18.5, noite), xytext=(14, noite + 0.04),
                color=TEXTO, fontsize=9, arrowprops=dict(arrowstyle="-", color=TEXTO_2))
    ax.set_ylim(0, df["pct_atraso"].max() * 1.35)
    ax.set_title("O atraso acumula ao longo do dia")
    _subtitulo(ax, "% de voos que chegaram atrasados, por hora prevista de partida")
    return fig


def heatmap_dia_hora(pivot):
    """Heatmap dia da semana x hora (rampa sequencial de um só tom)."""
    fig, ax = plt.subplots(figsize=(11, 3.8))
    im = ax.imshow(pivot.values, cmap=RAMPA_AZUL, aspect="auto", vmin=0)
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    ax.set_xticks(range(len(pivot.columns)), [f"{h}h" for h in pivot.columns], fontsize=8)
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)
    cbar = fig.colorbar(im, ax=ax, fraction=0.025, pad=0.01, format=mtick.PercentFormatter(1, 0))
    cbar.outline.set_visible(False)
    cbar.ax.tick_params(colors=TEXTO_2, labelsize=8)
    ax.set_title("Quinta e sexta à noite: a pior combinação")
    _subtitulo(ax, "% de voos que chegaram atrasados, por dia da semana e hora prevista de partida")
    return fig


def serie_diaria(df, anomalias=None):
    """Linha: % de atraso diário com média móvel de 7 dias."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    ax.plot(df["data_voo"], df["pct_atraso"], color=CINZA, linewidth=1, label="Diário")
    ax.plot(df["data_voo"], df["media_7d"], color=AZUL, linewidth=2, label="Média móvel 7 dias")
    pct_axis(ax)
    ax.grid(axis="x", visible=False)
    for data, texto in (anomalias or {}).items():
        v = df.loc[df["data_voo"] == data, "pct_atraso"].iloc[0]
        ax.scatter([data], [v], s=36, color=LARANJA, zorder=3, edgecolor=FUNDO, linewidth=2)
        ax.annotate(texto, xy=(data, v), xytext=(12, -4), textcoords="offset points",
                    fontsize=9, color=TEXTO)
    ax.legend(loc="upper right", fontsize=9)
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
    ax.xaxis.set_major_formatter(mtick.FuncFormatter(
        lambda x, _: f"{MESES[mdates.num2date(x).month - 1]}/{mdates.num2date(x):%y}"))
    ax.set_title("Dezembro concentra os piores dias do ano")
    _subtitulo(ax, "% de voos que chegaram atrasados por dia")
    return fig


def empresas_com_e_sem_gru(df):
    """Dumbbell: % de atraso por companhia em todos os voos vs. excluindo Guarulhos."""
    df = df.sort_values("todos")
    fig, ax = plt.subplots(figsize=(8, 3.6))
    for y, linha in enumerate(df.itertuples()):
        cor = CORES_EMPRESA[linha.grupo_empresa]
        ax.plot([linha.sem_gru, linha.todos], [y, y], color=GRADE, linewidth=3, zorder=1)
        ax.scatter(linha.todos, y, s=90, color=cor, zorder=3, edgecolor=FUNDO, linewidth=2)
        ax.scatter(linha.sem_gru, y, s=90, facecolor=FUNDO, edgecolor=cor, linewidth=2, zorder=3)
        ax.text(linha.todos + 0.004, y, f"{linha.todos:.1%}", va="center", fontsize=9)
        ax.text(linha.sem_gru - 0.004, y, f"{linha.sem_gru:.1%}", va="center", ha="right", fontsize=9)
    ax.set_yticks(range(len(df)), df["grupo_empresa"])
    ax.grid(axis="y", visible=False)
    pct_axis(ax, "x")
    lo, hi = df[["todos", "sem_gru"]].min().min(), df[["todos", "sem_gru"]].max().max()
    ax.set_xlim(lo - 0.03, hi + 0.03)
    ax.set_ylim(-0.6, len(df) - 0.4)
    ax.scatter([], [], s=60, color=TEXTO_2, label="Todos os voos")
    ax.scatter([], [], s=60, facecolor=FUNDO, edgecolor=TEXTO_2, linewidth=2, label="Sem voos de/para GRU")
    ax.legend(loc="lower right", fontsize=8.5)
    ax.set_title("Sem Guarulhos, o ranking das companhias muda")
    _subtitulo(ax, "% de voos que chegaram atrasados")
    return fig
