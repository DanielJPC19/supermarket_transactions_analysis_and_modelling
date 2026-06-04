from __future__ import annotations
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

PALETTE = px.colors.qualitative.Plotly
TEMPLATE = "plotly_white"

_LAYOUT = dict(
    template=TEMPLATE,
    font=dict(family="Segoe UI, Arial, sans-serif", size=13),
    margin=dict(l=60, r=40, t=70, b=60),
    hoverlabel=dict(bgcolor="white", font_size=13),
)

_FEATURE_LABELS = {
    "mean_frequency": "Frecuencia",
    "mean_total_units": "Total unidades",
    "mean_unique_products": "Prod. distintos",
    "mean_unique_categories": "Cat. distintas",
    "mean_avg_basket_size": "Tamaño canasta",
}


def chart_scatter_clusters(assignments: list[dict]) -> str:
    """Scatter PCA1 vs PCA2 coloreado por cluster."""
    clusters = sorted({p["cluster"] for p in assignments})

    fig = go.Figure()
    for c in clusters:
        pts = [p for p in assignments if p["cluster"] == c]
        fig.add_trace(go.Scatter(
            x=[p["pca1"] for p in pts],
            y=[p["pca2"] for p in pts],
            mode="markers",
            name=f"Cluster {c}",
            marker=dict(color=PALETTE[c % len(PALETTE)], size=5, opacity=0.7),
            customdata=[[
                p["cliente_id"], p["frequency"], p["total_units"],
                p["unique_products"], p["unique_categories"],
            ] for p in pts],
            hovertemplate=(
                "<b>Cliente %{customdata[0]}</b><br>"
                "Frecuencia: %{customdata[1]:.0f}<br>"
                "Total unidades: %{customdata[2]:.0f}<br>"
                "Prod. distintos: %{customdata[3]:.0f}<br>"
                "Cat. distintas: %{customdata[4]:.0f}<extra></extra>"
            ),
        ))

    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Segmentación de Clientes — Proyección PCA 2D", x=0.5),
        xaxis_title="Componente Principal 1",
        yaxis_title="Componente Principal 2",
        legend=dict(title="Cluster", orientation="v"),
        height=520,
    )
    return fig.to_json()


def chart_cluster_profiles(profiles: list[dict]) -> str:
    """Barras agrupadas comparando las features medias por cluster (normalizadas 0-1)."""
    feature_keys = list(_FEATURE_LABELS.keys())
    feature_labels = list(_FEATURE_LABELS.values())
    clusters = sorted(profiles, key=lambda p: p["cluster"])

    # Normalizar cada feature al rango [0,1] entre clusters
    maxima = {
        k: max((p[k] for p in profiles), default=1) or 1
        for k in feature_keys
    }

    fig = go.Figure()
    for prof in clusters:
        c = prof["cluster"]
        vals_norm = [prof[k] / maxima[k] for k in feature_keys]
        vals_raw  = [prof[k] for k in feature_keys]
        fig.add_trace(go.Bar(
            name=f"Cluster {c} (n={prof['size']:,})",
            x=feature_labels,
            y=vals_norm,
            marker_color=PALETTE[c % len(PALETTE)],
            customdata=vals_raw,
            hovertemplate="<b>%{x}</b><br>Valor real: %{customdata:.2f}<br>Relativo: %{y:.2f}<extra></extra>",
        ))

    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Perfil Comparativo de Clusters (valores normalizados)", x=0.5),
        barmode="group",
        yaxis_title="Valor relativo (0–1)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        height=460,
    )
    return fig.to_json()


def chart_evaluation_metrics(metrics: dict) -> str:
    """Silhouette score + WSSSE vs K — curva del codo y silhouette."""
    results = sorted(metrics["results"], key=lambda r: r["k"])
    ks = [r["k"] for r in results]
    silhouettes = [r["silhouette"] for r in results]
    wssse_vals = [r["wssse"] for r in results]
    best_k = metrics["best_k"]

    # Normalizar WSSSE a [0,1] para poder graficarlo junto al silhouette
    max_w = max(wssse_vals) or 1
    wssse_norm = [w / max_w for w in wssse_vals]

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=ks, y=silhouettes, mode="lines+markers",
        name="Silhouette Score",
        line=dict(color="#1f77b4", width=2.5),
        marker=dict(size=9, color=["#d62728" if k == best_k else "#1f77b4" for k in ks]),
        hovertemplate="K=%{x}<br>Silhouette: %{y:.4f}<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=ks, y=wssse_norm, mode="lines+markers",
        name="WSSSE (norm.)",
        line=dict(color="#ff7f0e", width=2, dash="dot"),
        marker=dict(size=7),
        hovertemplate="K=%{x}<br>WSSSE norm: %{y:.4f}<extra></extra>",
    ), secondary_y=True)

    # Línea vertical en best_k
    fig.add_vline(
        x=best_k, line_width=1.5, line_dash="dash", line_color="gray",
        annotation_text=f"Mejor K={best_k}", annotation_position="top right",
    )

    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Evaluación K-Means: Silhouette Score y Curva del Codo", x=0.5),
        xaxis=dict(title="Número de clusters (K)", tickvals=ks, tickmode="array"),
        height=420,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_yaxes(title_text="Silhouette Score", secondary_y=False)
    fig.update_yaxes(title_text="WSSSE (normalizado)", secondary_y=True)

    return fig.to_json()


def chart_cluster_sizes(profiles: list[dict]) -> str:
    """Pie chart con tamaño de cada cluster."""
    clusters = sorted(profiles, key=lambda p: p["cluster"])
    labels = [f"Cluster {p['cluster']}" for p in clusters]
    sizes  = [p["size"] for p in clusters]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=sizes,
        marker=dict(colors=[PALETTE[p["cluster"] % len(PALETTE)] for p in clusters]),
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>Clientes: %{value:,}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        **_LAYOUT,
        title=dict(text="Distribución de Clientes por Cluster", x=0.5),
        showlegend=False,
        height=420,
    )
    return fig.to_json()
