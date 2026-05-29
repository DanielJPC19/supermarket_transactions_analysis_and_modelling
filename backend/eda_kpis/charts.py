from __future__ import annotations
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

PALETTE = px.colors.qualitative.Plotly
PRIMARY_COLOR = "#1f77b4"
TEMPLATE = "plotly_white"

_LAYOUT = dict(
    template=TEMPLATE,
    font=dict(family="Segoe UI, Arial, sans-serif", size=13),
    margin=dict(l=60, r=40, t=70, b=60),
    hoverlabel=dict(bgcolor="white", font_size=13),
)


def chart_top10_productos(data: list[dict]) -> str:
    labels = [d["label"] for d in data]
    values = [d["total_cantidad"] for d in data]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=PALETTE[:len(data)],
        text=[f"{v:,}" for v in values],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Unidades: %{x:,}<extra></extra>",
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Top 10 Productos por Volumen de Ventas", x=0.5),
        xaxis_title="Total unidades vendidas",
        yaxis=dict(autorange="reversed"),
        height=420,
    )
    return fig.to_json()


def chart_top10_clientes(data: list[dict]) -> str:
    labels = [d["label"] for d in data]
    values = [d["n_transacciones"] for d in data]
    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker_color=PRIMARY_COLOR,
        text=[f"{v:,}" for v in values],
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Transacciones: %{x:,}<extra></extra>",
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Top 10 Clientes por Número de Transacciones", x=0.5),
        xaxis_title="Número de transacciones",
        yaxis=dict(autorange="reversed"),
        height=420,
    )
    return fig.to_json()


def chart_dias_pico(data: list[dict]) -> str:
    _dias = {1: "Dom", 2: "Lun", 3: "Mar", 4: "Mié", 5: "Jue", 6: "Vie", 7: "Sáb"}
    sorted_data = sorted(data, key=lambda d: d["fecha"])
    fechas  = [d["fecha"] for d in sorted_data]
    valores = [d["n_transacciones"] for d in sorted_data]
    colores = [PALETTE[d["dia_semana"] % len(PALETTE)] for d in sorted_data]
    hover  = [
        f"{d['fecha']}<br>{_dias.get(d['dia_semana'],'?')}<br>{d['n_transacciones']:,} transacciones"
        for d in sorted_data
    ]
    fig = go.Figure(go.Bar(
        x=fechas, y=valores,
        marker_color=colores,
        hovertext=hover, hoverinfo="text",
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Top 30 Días con Más Transacciones", x=0.5),
        xaxis_title="Fecha", yaxis_title="Transacciones",
        height=400,
    )
    return fig.to_json()


def chart_categorias(data: list[dict]) -> str:
    nombres = [d["nombre_categoria"] for d in data]
    totales = [d["total_cantidad"] for d in data]
    pcts    = [d["pct"] for d in data]

    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "pie"}, {"type": "bar"}]],
        subplot_titles=("Distribución relativa (%)", "Volumen absoluto (unidades)"),
    )
    fig.add_trace(go.Pie(
        labels=nombres, values=pcts, hole=0.35,
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>%{percent}<extra></extra>",
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=totales, y=nombres, orientation="h",
        marker_color=PALETTE[:len(nombres)],
        hovertemplate="<b>%{y}</b><br>%{x:,} unidades<extra></extra>",
    ), row=1, col=2)
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Categorías más Rentables por Volumen", x=0.5),
        showlegend=False,
        height=520,
    )
    return fig.to_json()


def chart_serie_tiempo(data: list[dict]) -> str:
    import pandas as pd
    pdf = pd.DataFrame(data).sort_values("fecha")
    pdf["rolling_7d"] = pdf["n_transacciones"].rolling(7, center=True).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pdf["fecha"], y=pdf["n_transacciones"],
        mode="lines", name="Diario",
        line=dict(color=PRIMARY_COLOR, width=1.5),
        fill="tozeroy", fillcolor="rgba(31,119,180,0.12)",
        hovertemplate="<b>%{x}</b><br>Transacciones: %{y:,}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=pdf["fecha"], y=pdf["rolling_7d"],
        mode="lines", name="Media móvil 7d",
        line=dict(color="#d62728", width=2.5, dash="dot"),
        hovertemplate="Media 7d: %{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Evolución Diaria de Transacciones (Ene–Jun 2013)", x=0.5),
        xaxis_title="Fecha", yaxis_title="Transacciones",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        height=450,
    )
    return fig.to_json()


def chart_boxplot(data: dict) -> str:
    """
    boxpoints='outliers': solo plotea los puntos que exceden 1.5*IQR.
    Con 131k valores, enviar todos los puntos al browser congelaría la UI.
    """
    fig = go.Figure(go.Box(
        y=data["values"],
        name="Total unidades / cliente",
        marker_color=PRIMARY_COLOR,
        boxmean=True,
        boxpoints="outliers",
        hovertemplate="Valor: %{y:,}<extra></extra>",
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Distribución de Unidades Compradas por Cliente", x=0.5),
        yaxis_title="Total unidades compradas",
        showlegend=False,
        height=450,
    )
    return fig.to_json()


def chart_heatmap(data: dict) -> str:
    _labels_es = {
        "frecuencia": "Frecuencia",
        "total_cantidad": "Total cantidad",
        "productos_distintos": "Prod. distintos",
        "categorias_distintas": "Cat. distintas",
    }
    labels = [_labels_es.get(l, l) for l in data["labels"]]
    fig = px.imshow(
        data["matrix"],
        x=labels, y=labels,
        color_continuous_scale="RdBu_r",
        zmin=-1, zmax=1,
        text_auto=".2f",
    )
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Correlación entre Variables de Comportamiento del Cliente", x=0.5),
        coloraxis_colorbar=dict(title="Pearson r"),
        height=480,
    )
    return fig.to_json()
