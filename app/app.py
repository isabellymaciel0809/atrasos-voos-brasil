"""Painel interativo de atrasos de voos domésticos no Brasil (dados ANAC/VRA).

Rodar localmente, a partir da raiz do projeto:
    streamlit run app/app.py
"""

from pathlib import Path

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

DATA_DIR = Path(__file__).parent / "data"
REPO_URL = "https://github.com/isabellymaciel0809/atrasos-voos-brasil"

AZUL = "#2a78d6"
LARANJA = "#eb6834"
VERDE_AGUA = "#1baf7a"
CINZA = "#b9b8b2"
TEXTO_2 = "#52514e"
GRADE = "#e6e5e0"
CORES_EMPRESA = {"LATAM": AZUL, "Azul": LARANJA, "Gol": VERDE_AGUA, "Outras": CINZA}
RAMPA_AZUL = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
MESES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
DIAS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

st.set_page_config(page_title="Atrasos de voos no Brasil", page_icon="✈️", layout="wide")


# ---------------------------------------------------------------- dados

@st.cache_resource
def conexao():
    con = duckdb.connect()
    con.execute(f"create view voos as select * from '{(DATA_DIR / 'voos.parquet').as_posix()}'")
    con.execute(f"create view aeroportos as select * from '{(DATA_DIR / 'aeroportos.parquet').as_posix()}'")
    return con


def sql(query, params=None):
    return conexao().execute(query, params or []).df()


@st.cache_data
def opcoes():
    meses = sql("select distinct date_trunc('month', data_voo)::date as mes from voos order by 1")["mes"].tolist()
    aeroportos = sql("""
        select v.origem_icao as icao, a.cidade, a.uf, count(*) as voos
        from voos v join aeroportos a on a.icao = v.origem_icao
        group by all
        having voos >= 1000
        order by voos desc
    """)
    return meses, aeroportos


def rotulo_mes(d):
    return f"{MESES[d.month - 1]}/{d:%y}"


def pct(v, casas=1):
    return "–" if pd.isna(v) else f"{v:.{casas}%}".replace(".", ",")


# ---------------------------------------------------------------- estilo dos gráficos

def estilizar(fig, titulo, subtitulo, altura=420):
    fig.update_layout(
        title=dict(text=f"<b>{titulo}</b><br><span style='font-size:13px;color:{TEXTO_2}'>{subtitulo}</span>",
                   x=0, xanchor="left", y=0.97),
        height=altura,
        margin=dict(l=10, r=20, t=80, b=40),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", size=13, color="#0b0b0b"),
        hoverlabel=dict(bgcolor="white", font_size=13),
        separators=",.",  # padrão brasileiro: vírgula decimal, ponto de milhar
        showlegend=False,
    )
    fig.update_xaxes(gridcolor=GRADE, zeroline=False, linecolor=GRADE)
    fig.update_yaxes(gridcolor=GRADE, zeroline=False, linecolor=GRADE)
    return fig


# ---------------------------------------------------------------- filtros

meses, aeroportos = opcoes()

with st.sidebar:
    st.header("Filtros")
    inicio, fim = st.select_slider(
        "Período", options=meses, value=(meses[0], meses[-1]), format_func=rotulo_mes
    )
    empresas = st.multiselect("Companhias", list(CORES_EMPRESA), default=list(CORES_EMPRESA))
    nomes_aeroporto = {r.icao: f"{r.cidade.title()} ({r.icao}) – {r.uf}" for r in aeroportos.itertuples()}
    origem = st.selectbox(
        "Aeroporto de origem", ["Todos", *nomes_aeroporto],
        format_func=lambda x: "Todos os aeroportos" if x == "Todos" else nomes_aeroporto[x],
    )
    limiar = st.radio(
        "Considerar atrasado a partir de", [15, 30, 60], horizontal=True,
        format_func=lambda m: f"{m} min",
        help="15 min é o padrão internacional (OTP15). A ANAC usa 30 min na sua classificação.",
    )
    st.divider()
    st.caption(
        "Fonte: [ANAC – Voo Regular Ativo (VRA)](https://siros.anac.gov.br/siros/registros/diversos/vra/). "
        f"Voos domésticos de passageiros. [Código e análise completa]({REPO_URL})."
    )

if not empresas:
    st.warning("Selecione ao menos uma companhia.")
    st.stop()

fim_exclusivo = (pd.Timestamp(fim) + pd.offsets.MonthBegin(1)).date()
filtro_periodo = "data_voo >= ? and data_voo < ?"
params_periodo = [inicio, fim_exclusivo]
filtro_empresa = f"grupo_empresa in ({', '.join('?' * len(empresas))})"
filtro_base = f"{filtro_periodo} and {filtro_empresa}"
params_base = params_periodo + empresas
if origem != "Todos":
    filtro = f"{filtro_base} and origem_icao = ?"
    params = params_base + [origem]
else:
    filtro, params = filtro_base, params_base

# voos realizados (base de pontualidade)
REALIZADOS = "not cancelado"
ATRASADO = f"(atraso_chegada_min > {int(limiar)})::int"


# ---------------------------------------------------------------- cabeçalho e KPIs

st.title("✈️ Atrasos de voos no Brasil")
local = "todos os aeroportos" if origem == "Todos" else nomes_aeroporto[origem]
st.markdown(
    f"Voos domésticos de **{rotulo_mes(inicio)} a {rotulo_mes(fim)}**, saindo de **{local}**. "
    f"Atrasado = chegada mais de **{limiar} min** após o horário previsto."
)

kpi = sql(f"""
    select
        count(*) filter (where {REALIZADOS})                                  as voos,
        avg({ATRASADO}) filter (where {REALIZADOS})                           as pct_atraso,
        avg(atraso_chegada_min) filter (where {REALIZADOS}
                                        and atraso_chegada_min > {int(limiar)}) as atraso_medio,
        avg(cancelado::int)                                                   as pct_cancelado
    from voos where {filtro}
""", params).iloc[0]

brasil = sql(f"""
    select avg({ATRASADO}) filter (where {REALIZADOS}) as pct_atraso, avg(cancelado::int) as pct_cancelado
    from voos where {filtro_periodo}
""", params_periodo).iloc[0]

if not kpi["voos"]:
    st.info("Nenhum voo encontrado com esses filtros.")
    st.stop()

def delta_brasil(coluna):
    """Diferença em pontos percentuais vs. Brasil no mesmo período (só faz sentido com filtro ativo)."""
    if origem == "Todos" and len(empresas) == len(CORES_EMPRESA):
        return None
    pp = f"{(kpi[coluna] - brasil[coluna]) * 100:+.1f}".replace(".", ",")
    return f"{pp} p.p. vs. Brasil"


c1, c2, c3, c4 = st.columns(4)
c1.metric("Voos realizados", f"{int(kpi['voos']):,}".replace(",", "."))
c2.metric("Chegaram atrasados", pct(kpi["pct_atraso"]), delta=delta_brasil("pct_atraso"), delta_color="inverse")
c3.metric("Atraso médio (quando atrasa)", f"{kpi['atraso_medio']:.0f} min" if pd.notna(kpi["atraso_medio"]) else "–")
c4.metric("Cancelados", pct(kpi["pct_cancelado"]), delta=delta_brasil("pct_cancelado"), delta_color="inverse")
if kpi["voos"] < 300:
    st.warning(f"Amostra pequena ({int(kpi['voos'])} voos): os percentuais abaixo variam muito e não permitem conclusões.")

aba_aero, aba_hora, aba_emp, aba_tempo, aba_rotas = st.tabs(
    ["📍 Aeroportos", "🕔 Horários", "🏢 Companhias", "📈 Evolução", "🛫 Rotas"]
)


# ---------------------------------------------------------------- aeroportos

with aba_aero:
    min_voos = st.slider("Mínimo de voos no período", 500, 10000, 3000, step=500)
    df = sql(f"""
        select v.origem_icao as icao, a.cidade, a.uf, count(*) as voos, avg({ATRASADO}) as pct_atraso
        from voos v join aeroportos a on a.icao = v.origem_icao
        where {filtro_base} and {REALIZADOS}
        group by all
        having voos >= ?
        order by pct_atraso
    """, params_base + [min_voos])
    if df.empty:
        st.info("Nenhum aeroporto atinge o mínimo de voos com esses filtros.")
    else:
        df["rotulo"] = df["cidade"].str.title() + " (" + df["icao"] + ")"
        destaque = origem if origem != "Todos" else df["icao"].iloc[-1]
        fig = go.Figure(go.Bar(
            x=df["pct_atraso"], y=df["rotulo"], orientation="h",
            marker_color=[LARANJA if i == destaque else CINZA for i in df["icao"]],
            customdata=df[["voos", "uf"]],
            hovertemplate="<b>%{y}</b> – %{customdata[1]}<br>%{x:.1%} atrasados<br>%{customdata[0]:,} voos<extra></extra>",
        ))
        media = sql(f"select avg({ATRASADO}) as m from voos where {filtro_base} and {REALIZADOS}", params_base)["m"].iloc[0]
        fig.add_vline(x=media, line_color=TEXTO_2, line_width=1,
                      annotation_text=f"média {pct(media)}", annotation_position="top")
        fig.update_xaxes(tickformat=".0%")
        fig.update_yaxes(showgrid=False)
        st.plotly_chart(
            estilizar(fig, "Pontualidade por aeroporto de origem", "% de voos que chegaram atrasados",
                      altura=max(380, 22 * len(df) + 120)),
            width="stretch",
        )


# ---------------------------------------------------------------- horários

with aba_hora:
    df = sql(f"""
        select hora, count(*) as voos, avg({ATRASADO}) as pct_atraso
        from voos where {filtro} and {REALIZADOS} and hora is not null
        group by 1 order by 1
    """, params)
    fig = go.Figure(go.Bar(
        x=df["hora"], y=df["pct_atraso"], marker_color=AZUL, customdata=df["voos"],
        hovertemplate="<b>%{x}h</b><br>%{y:.1%} atrasados<br>%{customdata:,} voos<extra></extra>",
    ))
    fig.update_xaxes(tickmode="array", tickvals=list(range(0, 24, 2)),
                     ticktext=[f"{h}h" for h in range(0, 24, 2)], showgrid=False, title="Hora prevista de partida")
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(estilizar(fig, "O atraso acumula ao longo do dia",
                              "% de voos que chegaram atrasados, por hora prevista de partida"),
                    width="stretch")

    df = sql(f"""
        select isodow(data_voo) as dia, hora, count(*) as voos, avg({ATRASADO}) as pct_atraso
        from voos where {filtro} and {REALIZADOS} and hora is not null
        group by all
    """, params)
    matriz = df.pivot(index="dia", columns="hora", values="pct_atraso").reindex(index=range(1, 8), columns=range(24))
    volumes = df.pivot(index="dia", columns="hora", values="voos").reindex(index=range(1, 8), columns=range(24))
    fig = go.Figure(go.Heatmap(
        z=matriz.values, x=[f"{h}h" for h in range(24)], y=DIAS, customdata=volumes.values,
        colorscale=RAMPA_AZUL, zmin=0, colorbar=dict(tickformat=".0%", outlinewidth=0, thickness=12),
        xgap=2, ygap=2,
        hovertemplate="<b>%{y}, %{x}</b><br>%{z:.1%} atrasados<br>%{customdata:,.0f} voos<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(showgrid=False)
    st.plotly_chart(estilizar(fig, "Dia da semana × hora",
                              "% de voos que chegaram atrasados", altura=360),
                    width="stretch")

    bola = sql(f"""
        select
            avg({ATRASADO}) filter (where atraso_partida_min > 15)   as saiu_atrasado,
            avg({ATRASADO}) filter (where atraso_partida_min <= 15)  as saiu_no_horario
        from voos where {filtro} and {REALIZADOS}
    """, params).iloc[0]
    a, b = st.columns(2)
    a.metric("Saíram atrasados → chegaram atrasados", pct(bola["saiu_atrasado"], 0))
    b.metric("Saíram no horário → chegaram atrasados", pct(bola["saiu_no_horario"], 0))
    st.caption("O atraso se decide no solo: quem sai atrasado quase nunca recupera o tempo no ar.")


# ---------------------------------------------------------------- companhias

with aba_emp:
    filtro_emp = f"{filtro_periodo} and {filtro_empresa}"
    df = sql(f"""
        select
            grupo_empresa,
            count(*)                                                                as voos,
            avg({ATRASADO})                                                         as todos,
            avg({ATRASADO}) filter (where origem_icao <> 'SBGR' and destino_icao <> 'SBGR') as sem_gru,
            avg((origem_icao = 'SBGR')::int)                                        as share_gru
        from voos where {filtro_emp} and {REALIZADOS}
        group by 1 order by todos
    """, params_base)
    fig = go.Figure()
    for linha in df.itertuples():
        cor = CORES_EMPRESA[linha.grupo_empresa]
        fig.add_trace(go.Scatter(
            x=[linha.sem_gru, linha.todos], y=[linha.grupo_empresa] * 2, mode="lines",
            line=dict(color=GRADE, width=4), hoverinfo="skip",
        ))
        fig.add_trace(go.Scatter(
            x=[linha.sem_gru], y=[linha.grupo_empresa], mode="markers+text",
            marker=dict(size=14, color="white", line=dict(color=cor, width=3)),
            text=[pct(linha.sem_gru)], textposition="middle left",
            hovertemplate=f"<b>{linha.grupo_empresa}</b><br>Sem GRU: %{{x:.1%}}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[linha.todos], y=[linha.grupo_empresa], mode="markers+text",
            marker=dict(size=14, color=cor, line=dict(color="white", width=2)),
            text=[pct(linha.todos)], textposition="middle right",
            hovertemplate=(f"<b>{linha.grupo_empresa}</b><br>Todos os voos: %{{x:.1%}}"
                           f"<br>{linha.share_gru:.0%} das partidas saem de GRU<extra></extra>"),
        ))
    fig.update_xaxes(tickformat=".0%")
    fig.update_yaxes(showgrid=False)
    st.plotly_chart(estilizar(fig, "Sem Guarulhos, o ranking das companhias muda",
                              "● todos os voos   ○ sem voos de/para GRU", altura=340),
                    width="stretch")
    st.markdown(
        "Comparar companhias sem controlar o aeroporto pune quem opera mais no aeroporto mais congestionado. "
        "A tabela abaixo compara as companhias **no mesmo aeroporto**."
    )

    tabela = sql(f"""
        select v.origem_icao as icao, a.cidade, grupo_empresa, avg({ATRASADO}) as p, count(*) as n
        from voos v join aeroportos a on a.icao = v.origem_icao
        where {filtro_emp} and {REALIZADOS} and grupo_empresa <> 'Outras'
        group by all
    """, params_base)
    volume = tabela.groupby("icao")["n"].sum().nlargest(12).index
    tabela = tabela[tabela["icao"].isin(volume) & (tabela["n"] >= 300)]
    tabela["aeroporto"] = tabela["cidade"].str.title() + " (" + tabela["icao"] + ")"
    pivot = tabela.pivot(index="aeroporto", columns="grupo_empresa", values="p").rename_axis(
        index="Aeroporto", columns=None)
    st.dataframe(
        pivot.style.format(pct, na_rep="–").background_gradient(cmap="Blues", axis=None),
        width="stretch",
    )
    st.caption("% de voos atrasados por companhia, nos 12 aeroportos com mais voos (mín. 300 voos por célula).")


# ---------------------------------------------------------------- evolução

with aba_tempo:
    df = sql(f"""
        select data_voo, count(*) filter (where {REALIZADOS}) as voos,
               avg({ATRASADO}) filter (where {REALIZADOS}) as pct_atraso
        from voos where {filtro}
        group by 1 order by 1
    """, params)
    df["media_7d"] = df["pct_atraso"].rolling(7, center=True, min_periods=4).mean()
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["data_voo"], y=df["pct_atraso"], mode="lines", line=dict(color=CINZA, width=1),
        name="Diário", customdata=df["voos"],
        hovertemplate="%{x|%d/%m/%Y}<br>%{y:.1%} atrasados<br>%{customdata:,} voos<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["data_voo"], y=df["media_7d"], mode="lines", line=dict(color=AZUL, width=2.5),
        name="Média móvel 7 dias", hovertemplate="Média 7 dias: %{y:.1%}<extra></extra>",
    ))
    pior = df.loc[df["pct_atraso"].idxmax()]
    fig.add_annotation(x=pior["data_voo"], y=pior["pct_atraso"], showarrow=True, arrowcolor=TEXTO_2,
                       text=f"{pior['data_voo']:%d/%m}: {pct(pior['pct_atraso'], 0)}", ax=50, ay=0)
    fig.update_yaxes(tickformat=".0%")
    marcas = pd.date_range(df["data_voo"].min(), df["data_voo"].max(), freq="MS")
    passo = 1 if len(marcas) <= 6 else 2
    fig.update_xaxes(showgrid=False, tickvals=marcas[::passo], ticktext=[rotulo_mes(m) for m in marcas[::passo]])
    estilizar(fig, "Evolução diária", "% de voos que chegaram atrasados por dia", altura=440)
    fig.update_layout(showlegend=True, hovermode="x unified",
                      legend=dict(orientation="h", y=1.02, x=1, xanchor="right", yanchor="bottom"))
    st.plotly_chart(fig, width="stretch")


# ---------------------------------------------------------------- rotas

with aba_rotas:
    col_a, col_b = st.columns([1, 1])
    min_rota = col_a.number_input("Mínimo de voos por rota", 100, 5000, 500, step=100)
    ordem = col_b.radio("Ordenar por", ["Mais atrasadas", "Mais pontuais"], horizontal=True)
    df = sql(f"""
        select
            o.cidade || ' (' || v.origem_icao || ')'   as origem,
            d.cidade || ' (' || v.destino_icao || ')'  as destino,
            count(*)                                    as voos,
            avg({ATRASADO})                             as pct_atraso,
            median(atraso_chegada_min)                  as mediana_min
        from voos v
        join aeroportos o on o.icao = v.origem_icao
        join aeroportos d on d.icao = v.destino_icao
        where {filtro} and {REALIZADOS}
        group by all
        having voos >= ?
        order by pct_atraso {'desc' if ordem == 'Mais atrasadas' else 'asc'}
        limit 25
    """, params + [min_rota])
    df["origem"] = df["origem"].str.title().str.replace(r"\((\w+)\)", lambda m: m.group(0).upper(), regex=True)
    df["destino"] = df["destino"].str.title().str.replace(r"\((\w+)\)", lambda m: m.group(0).upper(), regex=True)
    st.dataframe(
        df,
        hide_index=True,
        width="stretch",
        column_config={
            "origem": "Origem",
            "destino": "Destino",
            "voos": st.column_config.NumberColumn("Voos", format="%d"),
            "pct_atraso": st.column_config.ProgressColumn(
                "% atrasados", format="percent", min_value=0, max_value=max(0.5, df["pct_atraso"].max() if len(df) else 0)
            ),
            "mediana_min": st.column_config.NumberColumn("Atraso mediano (min)", format="%d"),
        },
    )
