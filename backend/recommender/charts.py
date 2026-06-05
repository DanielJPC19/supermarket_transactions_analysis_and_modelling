from __future__ import annotations

import json


_PALETTE = [
    "#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A",
    "#19D3F3", "#FF6692", "#B6E880", "#FF97FF", "#FECB52",
]

_LAYOUT_BASE = dict(
    template="plotly_white",
    font=dict(family="Segoe UI, Arial, sans-serif", size=13),
    margin=dict(l=60, r=30, t=50, b=60),
)


def chart_evaluation_metrics(metrics: dict) -> str:
    """Bar chart con Precision@10 y Recall@10."""
    import plotly.graph_objects as go

    precision = metrics.get("precision_at_10", 0)
    recall    = metrics.get("recall_at_10", 0)
    n_users   = metrics.get("num_users_evaluated", 0)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Precision@10",
        x=["Precision@10"],
        y=[round(precision, 6)],
        marker_color=_PALETTE[0],
        text=[f"{precision:.4%}"],
        textposition="outside",
    ))
    fig.add_trace(go.Bar(
        name="Recall@10",
        x=["Recall@10"],
        y=[round(recall, 6)],
        marker_color=_PALETTE[1],
        text=[f"{recall:.4%}"],
        textposition="outside",
    ))

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text=f"Métricas de Evaluación del Recomendador (n={n_users:,} usuarios)", x=0.5),
        yaxis=dict(title="Valor", tickformat=".4%", rangemode="tozero"),
        barmode="group",
        showlegend=True,
    )

    return json.dumps(fig.to_dict(), ensure_ascii=False)


def chart_top_products_heatmap(customer_recs: dict, cluster_profiles: list | None = None) -> str:
    """
    Heatmap: clusters en eje Y, top productos en eje X, intensidad = score promedio.
    Se construye agregando los scores de customer_recs por cluster.
    """
    import plotly.graph_objects as go
    from collections import defaultdict

    # Agregar scores por (cluster, producto_id)
    cluster_product_scores: dict[int, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
    for customer_data in customer_recs.values():
        cluster = customer_data.get("cluster", -1)
        for rec in customer_data.get("recommendations", []):
            pid = rec["producto_id"]
            score = rec["score"]
            cluster_product_scores[cluster][pid].append(score)

    if not cluster_product_scores:
        import plotly.graph_objects as go
        fig = go.Figure()
        fig.update_layout(**_LAYOUT_BASE, title="Sin datos de recomendaciones")
        return json.dumps(fig.to_dict(), ensure_ascii=False)

    # Para cada cluster, obtener top-10 productos por score medio
    cluster_top: dict[int, list[tuple[int, float]]] = {}
    for cluster, prod_scores in cluster_product_scores.items():
        avg_scores = {pid: sum(scores) / len(scores) for pid, scores in prod_scores.items()}
        top10 = sorted(avg_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        cluster_top[cluster] = top10

    # Unión de todos los productos top
    all_products = sorted({pid for tops in cluster_top.values() for pid, _ in tops})
    clusters = sorted(cluster_top.keys())

    # Construir matriz [cluster × producto]
    z = []
    for c in clusters:
        prod_map = dict(cluster_top[c])
        row = [prod_map.get(pid, 0.0) for pid in all_products]
        z.append(row)

    x_labels = [f"Prod {pid}" for pid in all_products]
    y_labels = [f"Cluster {c}" for c in clusters]

    fig = go.Figure(go.Heatmap(
        z=z,
        x=x_labels,
        y=y_labels,
        colorscale="Blues",
        colorbar=dict(title="Score"),
        hoverongaps=False,
        hovertemplate="Cluster %{y}<br>%{x}<br>Score: %{z:.4f}<extra></extra>",
    ))

    fig.update_layout(
        **_LAYOUT_BASE,
        title=dict(text="Top Productos por Cluster (Score promedio de recomendación)", x=0.5),
        xaxis=dict(title="Producto", tickangle=-45),
        yaxis=dict(title="Cluster"),
        margin=dict(l=100, r=30, t=60, b=120),
    )

    return json.dumps(fig.to_dict(), ensure_ascii=False)
