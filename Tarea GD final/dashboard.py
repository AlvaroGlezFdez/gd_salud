"""K-Salud · Customer Analytics Dashboard

Proyecto Final — Gestión de Datos · UAX
Álvaro González Fernández

Ejecución:
    streamlit run dashboard.py
"""
from pathlib import Path
import sqlite3

import joblib
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve

# ─────────────────────────────────────────────────────────────────────────────
# 1. Configuración de página
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Customer Analytics · K-Salud",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────────────────────
# 2. Paleta
# ─────────────────────────────────────────────────────────────────────────────
PRIMARY  = "#1e3a5f"
ACCENT   = "#c8a951"
DANGER   = "#c0392b"
SUCCESS  = "#27ae60"
INFO     = "#2980b9"
BG       = "#ebe1cb"
CARD     = "#f5efdf"
CARD2    = "#faf5e6"
INK      = "#2b2b2b"
MUTED    = "#7a7363"

CLUSTER_COLORS = {
    "VIP Champion":   ACCENT,
    "Regular Activo": PRIMARY,
    "Perdido":        DANGER,
    "Devolutivo":     "#8e44ad",
}

# ─────────────────────────────────────────────────────────────────────────────
# 3. CSS — beige + EB Garamond + tabs centradas, sin sidebar
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=EB+Garamond:wght@300;400;500;600;700&display=swap');

        html, body, [class*="css"], button, input, textarea, select,
        .stMarkdown, .stMetric, .stDataFrame {{
            font-family: 'EB Garamond', Georgia, 'Times New Roman', serif !important;
            color: {INK};
            font-feature-settings: 'tnum' 1;
        }}

        .stApp {{ background-color: {BG}; }}
        section.main > div.block-container {{
            padding-top: 1.5rem;
            padding-bottom: 3rem;
            max-width: 1400px;
        }}

        /* Sidebar oculta por completo */
        section[data-testid="stSidebar"]   {{ display: none !important; }}
        button[kind="header"]              {{ display: none !important; }}
        [data-testid="collapsedControl"]   {{ display: none !important; }}

        /* Cabecera centrada */
        .hero {{
            text-align: center;
            padding: 1rem 0 0.6rem 0;
            margin-bottom: 0.5rem;
        }}
        .hero h1 {{
            color: {PRIMARY};
            font-size: 36px;
            font-weight: 600;
            margin: 0;
            letter-spacing: -0.02em;
        }}
        .hero .subtitle {{
            color: {MUTED};
            font-size: 13px;
            font-weight: 400;
            margin-top: 6px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }}
        .hero .rule {{
            width: 60px; height: 2px;
            background-color: {ACCENT};
            margin: 14px auto 0 auto;
        }}

        /* Tabs centradas como navegación principal.
           IMPORTANTE: NO aplicar display: flex al wrapper padre porque
           ese wrapper contiene tanto la tab-list como el tab-panel; haría
           que el panel se rendrice apretado a un lado en vez de a ancho completo.
           En su lugar centramos la tab-list con margin: auto. */
        div[data-baseweb="tab-list"] {{
            background-color: {CARD};
            border: 1px solid rgba(30, 58, 95, 0.10);
            border-radius: 10px;
            padding: 6px;
            margin: 0.5rem auto 1.5rem auto !important;
            width: fit-content;
            max-width: 100%;
            box-shadow: 0 2px 6px rgba(40, 30, 10, 0.05);
            gap: 4px !important;
        }}
        button[data-baseweb="tab"] {{
            padding: 10px 18px !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            color: {MUTED} !important;
            border-radius: 6px !important;
            border: none !important;
            background: transparent !important;
        }}
        button[data-baseweb="tab"]:hover {{
            background-color: rgba(30, 58, 95, 0.06) !important;
            color: {PRIMARY} !important;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: {PRIMARY} !important;
            font-weight: 600 !important;
            background-color: rgba(200, 169, 81, 0.18) !important;
        }}
        div[data-baseweb="tab-highlight"] {{ display: none !important; }}
        div[data-baseweb="tab-border"]    {{ display: none !important; }}

        /* Ventanas (st.container border=True) */
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background-color: {CARD};
            border: 1px solid rgba(30, 58, 95, 0.10) !important;
            border-radius: 8px;
            padding: 22px 26px !important;
            box-shadow: 0 1px 3px rgba(40, 30, 10, 0.04);
            margin-bottom: 18px;
        }}

        .window-title {{
            color: {PRIMARY};
            font-size: 17px;
            font-weight: 600;
            margin: 0 0 14px 0;
            padding-bottom: 6px;
            border-bottom: 1px solid rgba(30, 58, 95, 0.12);
        }}
        .window-subtitle {{
            color: {MUTED};
            font-size: 12px;
            margin: -8px 0 14px 0;
        }}

        /* KPI cards */
        div[data-testid="stMetric"] {{
            background-color: rgba(255, 253, 245, 0.65);
            border-left: 3px solid {PRIMARY};
            padding: 12px 14px;
            border-radius: 4px;
        }}
        div[data-testid="stMetricLabel"] p {{
            color: {PRIMARY};
            font-weight: 500;
            font-size: 11.5px;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
        div[data-testid="stMetricValue"] {{
            color: {INK};
            font-size: 23px;
            font-weight: 600;
        }}
        div[data-testid="stMetricDelta"] {{ font-size: 11px; }}

        /* Cards ROI */
        .roi-card {{
            background-color: rgba(255, 253, 245, 0.65);
            border-left: 3px solid {PRIMARY};
            padding: 14px 16px;
            border-radius: 4px;
            min-height: 88px;
        }}
        .roi-card.success {{ border-left-color: {SUCCESS}; }}
        .roi-card.danger  {{ border-left-color: {DANGER}; }}
        .roi-card .label  {{ color: {PRIMARY}; font-weight: 500; font-size: 12px;
                              text-transform: uppercase; letter-spacing: 0.04em; }}
        .roi-card .value  {{ font-size: 21px; font-weight: 600; margin-top: 6px; color: {INK}; }}

        .key-insight {{
            background-color: rgba(200, 169, 81, 0.14);
            border-left: 3px solid {ACCENT};
            padding: 14px 18px;
            border-radius: 4px;
            color: {INK};
            font-size: 14px;
            margin: 6px 0 18px 0;
        }}
        .key-insight b {{ color: {PRIMARY}; }}

        .info-box {{
            background-color: rgba(41, 128, 185, 0.10);
            border-left: 3px solid {INFO};
            padding: 10px 14px;
            border-radius: 4px;
            color: {INK};
            font-size: 13px;
            margin: 8px 0;
        }}

        button[kind="primary"] {{
            background-color: {PRIMARY} !important;
            border: none !important;
            font-weight: 500 !important;
        }}
        button[kind="primary"]:hover {{ background-color: #2c5485 !important; }}

        .footer-text {{
            text-align: center;
            color: {MUTED};
            font-size: 12px;
            margin-top: 1.5rem;
        }}
        .footer-text b {{ color: {PRIMARY}; font-weight: 600; }}

        /* Sección compacta */
        .section-label {{
            color: {PRIMARY};
            font-weight: 600;
            font-size: 13px;
            margin: 14px 0 6px 0;
            text-transform: uppercase;
            letter-spacing: 0.04em;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# 4. Loaders
# ─────────────────────────────────────────────────────────────────────────────
DATA_PATH  = Path("05_clustering/clientes_segmentados.csv")
MODEL_PATH = Path("05_clustering/modelo_churn.pkl")
DWH_PATH   = Path("02_dwh/saleshealth_dwh.db")


@st.cache_data(show_spinner=False)
def load_segmented() -> pd.DataFrame:
    return pd.read_csv(DATA_PATH)


@st.cache_data(show_spinner=False)
def load_customer_details() -> pd.DataFrame:
    conn = sqlite3.connect(DWH_PATH)
    try:
        df = pd.read_sql(
            "SELECT customer_id, first_name, last_name, email, phone FROM dim_customer",
            conn,
        )
    finally:
        conn.close()
    df["nombre"] = (df["first_name"].fillna("") + " " + df["last_name"].fillna("")).str.strip()
    return df


@st.cache_data(show_spinner=False)
def load_sales_facts() -> pd.DataFrame:
    conn = sqlite3.connect(DWH_PATH)
    try:
        df = pd.read_sql(
            """
            SELECT f.customer_id, f.sale_id, f.subtotal, f.margin,
                   d.date, d.year, d.month, d.quarter,
                   d.day_of_week, d.is_weekend
            FROM   fact_sales f
            JOIN   dim_date   d ON f.date_id = d.date_id
            """,
            conn,
        )
    finally:
        conn.close()
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_resource(show_spinner=False)
def load_model() -> dict:
    return joblib.load(MODEL_PATH)


with st.spinner("Cargando datos y modelo…"):
    for p in (DATA_PATH, MODEL_PATH, DWH_PATH):
        if not p.exists():
            st.error(f"No se encuentra `{p}`. Ejecuta antes las fases 1-6.")
            st.stop()
    df_seg       = load_segmented()
    df_cust      = load_customer_details()
    model_bundle = load_model()
    df_seg = df_seg.merge(
        df_cust[["customer_id", "nombre", "email", "phone"]],
        on="customer_id", how="left",
    )


# ─────────────────────────────────────────────────────────────────────────────
# 5. Helpers
# ─────────────────────────────────────────────────────────────────────────────
def themed(fig, height=420, title=None, legend_bottom=True, show_legend=True):
    fig.update_layout(
        template="simple_white",
        paper_bgcolor=CARD, plot_bgcolor=CARD,
        font=dict(family="EB Garamond, Georgia, serif", color=INK, size=12),
        title=dict(text=title or "", font=dict(color=PRIMARY, size=14)),
        height=height,
        margin=dict(l=10, r=10, t=40 if title else 20, b=10),
        showlegend=show_legend,
    )
    if legend_bottom and show_legend:
        fig.update_layout(legend=dict(orientation="h", yanchor="bottom",
                                       y=-0.22, xanchor="center", x=0.5,
                                       title_text=""))
    return fig


def window_title(text, subtitle=None):
    st.markdown(f"<div class='window-title'>{text}</div>", unsafe_allow_html=True)
    if subtitle:
        st.markdown(f"<div class='window-subtitle'>{subtitle}</div>",
                    unsafe_allow_html=True)


def key_insight(text):
    st.markdown(f"<div class='key-insight'>{text}</div>", unsafe_allow_html=True)


def info_box(text):
    st.markdown(f"<div class='info-box'>{text}</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# 6. PÁGINA 1 — VISIÓN GENERAL
# ─────────────────────────────────────────────────────────────────────────────
def page_vision_general():
    n_clientes        = len(df_seg)
    ingresos_totales  = df_seg["ingresos"].sum()
    margen_total      = (df_seg["ingresos"] * df_seg["margen_ratio"]).sum()
    cltv_medio        = df_seg["cltv"].mean()
    cltv_mediano      = df_seg["cltv"].median()
    ticket_medio      = (df_seg["ingresos"].sum()
                          / max(df_seg["items_comprados"].sum(), 1))
    pct_activos       = (df_seg["estado_churn"] == "Activo").mean() * 100
    pct_perdidos      = (df_seg["estado_churn"] == "Perdido").mean() * 100
    proba_mean        = df_seg["churn_proba"].dropna().mean() * 100
    return_rate_avg   = df_seg["return_rate"].mean() * 100

    # ── KPIs (2 filas) ──────────────────────────────────────────────────────
    with st.container(border=True):
        window_title("KPIs globales", "Estado de la cartera completa")

        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        r1c1.metric("Total clientes",       f"{n_clientes:,}")
        r1c2.metric("Ingresos totales",     f"€ {ingresos_totales:,.0f}")
        r1c3.metric("Margen total",         f"€ {margen_total:,.0f}")
        r1c4.metric("CLTV medio",           f"€ {cltv_medio:,.0f}")

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        r2c1.metric("CLTV mediano",         f"€ {cltv_mediano:,.0f}",
                     help="La asimetría entre media y mediana revela la cola larga de los VIPs")
        r2c2.metric("Ticket medio",         f"€ {ticket_medio:,.2f}")
        r2c3.metric("% Activos",            f"{pct_activos:.1f}%",
                     delta=f"-{100 - pct_activos - pct_perdidos:.1f}% en riesgo",
                     delta_color="off",
                     help="Clientes con última compra < 180 días")
        r2c4.metric("Return rate medio",    f"{return_rate_avg:.2f}%",
                     help="Tasa media global de devoluciones")

    # ── Insight clave ───────────────────────────────────────────────────────
    vip_share = (df_seg["cluster_label"] == "VIP Champion").mean() * 100
    vip_revenue_share = (
        df_seg.loc[df_seg["cluster_label"] == "VIP Champion", "ingresos"].sum()
        / ingresos_totales * 100
    )
    key_insight(
        f"Aquí está toda la cartera. El <b>{vip_share:.1f}%</b> de los clientes "
        f"(VIP Champions) genera el <b>{vip_revenue_share:.1f}%</b> de los ingresos. "
        f"La media de CLTV ({cltv_medio:,.0f} €) y la mediana ({cltv_mediano:,.0f} €) "
        f"difieren <b>{(cltv_medio / max(cltv_mediano, 1)):.0f}×</b>: la distribución es "
        f"extremadamente asimétrica."
    )

    # ── Burbujas + Donut ────────────────────────────────────────────────────
    with st.container(border=True):
        window_title("Cartera completa por segmento",
                      "Cada punto = un cliente. Tamaño = nº de compras, color = segmento")
        c1, c2 = st.columns([6, 4])
        with c1:
            bubble = df_seg.copy()
            bubble["cltv_pos"] = bubble["cltv"].clip(lower=1)
            fig = px.scatter(
                bubble, x="dias_ultima_compra", y="cltv_pos",
                size="frecuencia", color="cluster_label",
                color_discrete_map=CLUSTER_COLORS,
                log_y=True, size_max=24, opacity=0.75,
                labels={
                    "dias_ultima_compra": "Días desde última compra",
                    "cltv_pos":           "CLTV (€, escala log)",
                    "cluster_label":      "Segmento",
                    "frecuencia":         "Frecuencia",
                },
                hover_data={"customer_id": True, "cltv": ":,.0f",
                            "cltv_pos": False, "frecuencia": True,
                            "dias_ultima_compra": True},
            )
            fig.add_vline(x=180, line_dash="dash", line_color=MUTED, opacity=0.6,
                           annotation_text="180d", annotation_position="top")
            fig.add_vline(x=365, line_dash="dash", line_color=DANGER, opacity=0.6,
                           annotation_text="365d", annotation_position="top")
            st.plotly_chart(themed(fig, height=460,
                                    title="CLTV vs recencia"),
                            use_container_width=True)
        with c2:
            seg_counts = df_seg["cluster_label"].value_counts().reset_index()
            seg_counts.columns = ["Segmento", "Clientes"]
            fig = go.Figure(go.Pie(
                labels=seg_counts["Segmento"], values=seg_counts["Clientes"],
                hole=0.55,
                marker=dict(colors=[CLUSTER_COLORS[s] for s in seg_counts["Segmento"]],
                            line=dict(color=CARD, width=2)),
                textinfo="percent+label", textposition="auto",
                hovertemplate="<b>%{label}</b><br>%{value:,} clientes<br>%{percent}<extra></extra>",
            ))
            st.plotly_chart(themed(fig, height=460,
                                    title="Distribución de segmentos",
                                    show_legend=False),
                            use_container_width=True)

    # ── Ingresos por segmento + Curva de Pareto ─────────────────────────────
    with st.container(border=True):
        window_title("Ingresos por segmento + Pareto",
                      "¿Qué porcentaje de la cartera concentra el grueso de los ingresos?")
        c1, c2 = st.columns(2)
        with c1:
            seg_rev = (df_seg.groupby("cluster_label")["ingresos"].sum()
                              .sort_values(ascending=True).reset_index())
            fig = go.Figure(go.Bar(
                x=seg_rev["ingresos"], y=seg_rev["cluster_label"], orientation="h",
                marker=dict(color=[CLUSTER_COLORS[s] for s in seg_rev["cluster_label"]],
                            line=dict(color="white", width=1)),
                text=[f"€ {v:,.0f}" for v in seg_rev["ingresos"]],
                textposition="outside",
            ))
            fig.update_xaxes(title="Ingresos acumulados (€)",
                              range=[0, seg_rev["ingresos"].max() * 1.25])
            st.plotly_chart(themed(fig, height=340, legend_bottom=False,
                                    title="Ingresos totales por segmento",
                                    show_legend=False),
                            use_container_width=True)
        with c2:
            # Curva de Pareto
            sorted_rev = np.sort(df_seg["ingresos"].values)[::-1]
            cum_rev = np.cumsum(sorted_rev) / sorted_rev.sum() * 100
            cum_cust = np.arange(1, len(sorted_rev) + 1) / len(sorted_rev) * 100
            idx_80 = int(np.argmax(cum_rev >= 80))
            pct_cust_80 = cum_cust[idx_80]

            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=cum_cust, y=cum_rev, mode="lines",
                line=dict(color=PRIMARY, width=2.5),
                fill="tozeroy", fillcolor="rgba(30, 58, 95, 0.10)",
                name="Curva real",
            ))
            fig.add_trace(go.Scatter(
                x=[0, 100], y=[0, 100], mode="lines",
                line=dict(color=MUTED, dash="dash"),
                name="Distribución uniforme",
            ))
            fig.add_vline(x=pct_cust_80, line_color=ACCENT, line_dash="dot")
            fig.add_hline(y=80, line_color=ACCENT, line_dash="dot",
                           annotation_text=f"{pct_cust_80:.1f}% genera 80% €",
                           annotation_position="bottom right")
            fig.update_xaxes(title="% clientes acumulado (ordenados de mayor a menor)",
                              range=[0, 100])
            fig.update_yaxes(title="% ingresos acumulado", range=[0, 105])
            st.plotly_chart(themed(fig, height=340, title="Curva de Pareto"),
                            use_container_width=True)

    # ── Tabla resumen por segmento ──────────────────────────────────────────
    with st.container(border=True):
        window_title("Resumen por segmento",
                      "Métricas clave de cada cluster en una tabla")
        summary = df_seg.groupby("cluster_label").agg(
            clientes=("customer_id", "count"),
            cltv_medio=("cltv", "mean"),
            cltv_mediano=("cltv", "median"),
            ingresos_total=("ingresos", "sum"),
            freq_media=("frecuencia", "mean"),
            recencia_media=("dias_ultima_compra", "mean"),
            return_rate_medio=("return_rate", "mean"),
            churn_proba_media=("churn_proba", "mean"),
        ).reset_index()
        summary["pct_cartera"] = summary["clientes"] / summary["clientes"].sum() * 100
        summary["pct_ingresos"] = summary["ingresos_total"] / summary["ingresos_total"].sum() * 100
        summary = summary.sort_values("cltv_medio", ascending=False)
        summary_display = summary[["cluster_label", "clientes", "pct_cartera",
                                    "cltv_medio", "cltv_mediano",
                                    "ingresos_total", "pct_ingresos",
                                    "freq_media", "recencia_media",
                                    "return_rate_medio", "churn_proba_media"]].copy()
        summary_display["pct_cartera"]       = summary_display["pct_cartera"].round(1)
        summary_display["pct_ingresos"]      = summary_display["pct_ingresos"].round(1)
        summary_display["cltv_medio"]        = summary_display["cltv_medio"].round(0)
        summary_display["cltv_mediano"]      = summary_display["cltv_mediano"].round(0)
        summary_display["ingresos_total"]    = summary_display["ingresos_total"].round(0)
        summary_display["freq_media"]        = summary_display["freq_media"].round(2)
        summary_display["recencia_media"]    = summary_display["recencia_media"].round(0)
        summary_display["return_rate_medio"] = summary_display["return_rate_medio"].round(3)
        summary_display["churn_proba_media"] = (summary_display["churn_proba_media"] * 100).round(1)
        summary_display.columns = ["Segmento", "Clientes", "% cartera",
                                    "CLTV medio (€)", "CLTV mediano (€)",
                                    "Ingresos (€)", "% ingresos",
                                    "Frecuencia", "Recencia (días)",
                                    "Return rate", "Churn risk (%)"]
        st.dataframe(summary_display, use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────────────────
# 7. PÁGINA 2 — ANÁLISIS DE SEGMENTOS
# ─────────────────────────────────────────────────────────────────────────────
def page_segmentos():
    all_segments = ["VIP Champion", "Regular Activo", "Perdido", "Devolutivo"]

    with st.container(border=True):
        window_title("Selector de segmento")
        selected = st.radio(
            "Segmento", options=all_segments, horizontal=True,
            label_visibility="collapsed",
        )

    sub    = df_seg[df_seg["cluster_label"] == selected]
    others = df_seg[df_seg["cluster_label"] != selected]
    color  = CLUSTER_COLORS[selected]

    # ── KPIs del segmento (2 filas) ─────────────────────────────────────────
    with st.container(border=True):
        window_title(f"KPIs · {selected}",
                      f"Vista exhaustiva del segmento ({len(sub):,} clientes)")
        r1c1, r1c2, r1c3, r1c4 = st.columns(4)
        r1c1.metric("Clientes",          f"{len(sub):,}",
                     delta=f"{len(sub)/max(len(df_seg),1)*100:.1f}% de la cartera",
                     delta_color="off")
        r1c2.metric("CLTV medio",        f"€ {sub['cltv'].mean():,.0f}")
        r1c3.metric("Frecuencia media",  f"{sub['frecuencia'].mean():.1f}")
        r1c4.metric("Return rate medio", f"{sub['return_rate'].mean():.3f}")

        ingresos_seg  = sub["ingresos"].sum()
        pct_ingresos  = ingresos_seg / max(df_seg["ingresos"].sum(), 1) * 100
        anios_medio   = sub["anios_relacion"].mean()
        dias_medio    = sub["dias_ultima_compra"].mean()
        churn_risk    = sub["churn_proba"].dropna().mean() * 100

        r2c1, r2c2, r2c3, r2c4 = st.columns(4)
        r2c1.metric("Ingresos segmento", f"€ {ingresos_seg:,.0f}",
                     delta=f"{pct_ingresos:.1f}% del total",
                     delta_color="off")
        r2c2.metric("CLTV mediano",      f"€ {sub['cltv'].median():,.0f}")
        r2c3.metric("Días sin comprar",  f"{dias_medio:.0f}")
        r2c4.metric("Churn risk medio",
                     f"{churn_risk:.1f}%" if not np.isnan(churn_risk) else "—")

    # ── Histograma CLTV + Radar comparativo ─────────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        with st.container(border=True):
            window_title("Distribución de CLTV",
                          "Eje X en log10 para apreciar la cola larga")
            cltv_pos = sub["cltv"].clip(lower=1)
            fig = px.histogram(
                x=np.log10(cltv_pos), nbins=30,
                color_discrete_sequence=[color],
            )
            fig.add_vline(x=np.log10(max(sub["cltv"].median(), 1)),
                           line_dash="dash", line_color=PRIMARY,
                           annotation_text=f"Mediana €{sub['cltv'].median():,.0f}",
                           annotation_position="top right")
            fig.update_xaxes(title="log₁₀(CLTV)")
            fig.update_yaxes(title="Nº clientes")
            st.plotly_chart(themed(fig, height=380, legend_bottom=False,
                                    show_legend=False),
                            use_container_width=True)

    with c2:
        with st.container(border=True):
            window_title("Perfil vs media global",
                          "Mayor área = perfil más fuerte en esa dimensión")

            def norm_metric(v, max_v, invert=False):
                v = float(np.clip(v, 0, max_v))
                pct = v / max_v if max_v > 0 else 0
                return (1 - pct) * 100 if invert else pct * 100

            max_cltv = df_seg["cltv"].max()
            max_freq = df_seg["frecuencia"].max()
            max_dias = df_seg["dias_ultima_compra"].max()
            max_rr   = max(df_seg["return_rate"].max(), 1.0)

            axes = ["Valor (CLTV)", "Frecuencia",
                    "Recencia (recientes)", "Calidad (1-RR)"]

            seg_vals = [
                norm_metric(sub["cltv"].mean(),               max_cltv),
                norm_metric(sub["frecuencia"].mean(),         max_freq),
                norm_metric(sub["dias_ultima_compra"].mean(), max_dias, invert=True),
                norm_metric(sub["return_rate"].mean(),        max_rr,   invert=True),
            ]
            glob_vals = [
                norm_metric(df_seg["cltv"].mean(),               max_cltv),
                norm_metric(df_seg["frecuencia"].mean(),         max_freq),
                norm_metric(df_seg["dias_ultima_compra"].mean(), max_dias, invert=True),
                norm_metric(df_seg["return_rate"].mean(),        max_rr,   invert=True),
            ]

            fig = go.Figure()
            fig.add_trace(go.Scatterpolar(
                r=glob_vals + [glob_vals[0]], theta=axes + [axes[0]],
                fill="toself", name="Media global",
                line=dict(color=MUTED), opacity=0.55,
            ))
            fig.add_trace(go.Scatterpolar(
                r=seg_vals + [seg_vals[0]], theta=axes + [axes[0]],
                fill="toself", name=selected,
                line=dict(color=color, width=2), opacity=0.85,
            ))
            fig.update_layout(
                polar=dict(
                    bgcolor=CARD,
                    radialaxis=dict(visible=True, range=[0, 100],
                                     showticklabels=False,
                                     gridcolor="rgba(0,0,0,0.08)"),
                    angularaxis=dict(gridcolor="rgba(0,0,0,0.08)"),
                ),
            )
            st.plotly_chart(themed(fig, height=380), use_container_width=True)

    # ── Boxplot CLTV vs otros + Churn distribution ─────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        with st.container(border=True):
            window_title("CLTV: este segmento vs los otros",
                          "Boxplot para comparar dispersión y outliers")
            bp_df = df_seg.copy()
            bp_df["grupo"] = np.where(bp_df["cluster_label"] == selected,
                                       selected, "Otros segmentos")
            bp_df["cltv_log"] = np.log10(bp_df["cltv"].clip(lower=1))
            fig = px.box(
                bp_df, x="grupo", y="cltv_log",
                color="grupo",
                color_discrete_map={selected: color, "Otros segmentos": MUTED},
                points="outliers",
            )
            fig.update_yaxes(title="log₁₀(CLTV)")
            fig.update_xaxes(title="")
            st.plotly_chart(themed(fig, height=360, legend_bottom=False,
                                    show_legend=False),
                            use_container_width=True)

    with c2:
        with st.container(border=True):
            window_title("Distribución de estado de churn dentro del segmento")
            churn_dist = sub["estado_churn"].value_counts().reindex(
                ["Activo", "En riesgo", "Perdido"]).fillna(0).reset_index()
            churn_dist.columns = ["Estado", "Clientes"]
            color_map_churn = {"Activo": SUCCESS, "En riesgo": ACCENT, "Perdido": DANGER}
            fig = go.Figure(go.Bar(
                x=churn_dist["Estado"], y=churn_dist["Clientes"],
                marker=dict(color=[color_map_churn[s] for s in churn_dist["Estado"]]),
                text=[f"{v:,.0f}" for v in churn_dist["Clientes"]],
                textposition="outside",
            ))
            fig.update_xaxes(title="")
            fig.update_yaxes(title="Nº clientes")
            st.plotly_chart(themed(fig, height=360, legend_bottom=False,
                                    show_legend=False),
                            use_container_width=True)

    # ── Tabla comparativa segmento vs otros ─────────────────────────────────
    with st.container(border=True):
        window_title("Comparativa numérica",
                      f"{selected} vs media de los otros 3 segmentos")
        compare = pd.DataFrame({
            "Métrica": ["CLTV medio (€)", "CLTV mediano (€)",
                         "Ingresos medios (€)", "Frecuencia media",
                         "Días sin comprar", "Return rate", "Churn risk (%)"],
            selected: [
                sub["cltv"].mean(), sub["cltv"].median(),
                sub["ingresos"].mean(), sub["frecuencia"].mean(),
                sub["dias_ultima_compra"].mean(), sub["return_rate"].mean(),
                sub["churn_proba"].dropna().mean() * 100,
            ],
            "Otros (media)": [
                others["cltv"].mean(), others["cltv"].median(),
                others["ingresos"].mean(), others["frecuencia"].mean(),
                others["dias_ultima_compra"].mean(), others["return_rate"].mean(),
                others["churn_proba"].dropna().mean() * 100,
            ],
        })
        compare["Δ relativo"] = [
            (compare.loc[i, selected] / max(compare.loc[i, "Otros (media)"], 1e-6) - 1) * 100
            for i in compare.index
        ]
        for col in [selected, "Otros (media)"]:
            compare[col] = compare[col].round(2)
        compare["Δ relativo"] = compare["Δ relativo"].apply(lambda v: f"{v:+.1f}%")
        st.dataframe(compare, use_container_width=True, hide_index=True)

    # ── Top 20 ──────────────────────────────────────────────────────────────
    with st.container(border=True):
        window_title(f"Top 20 clientes · {selected}",
                      "Ordenados por CLTV descendente")
        cols = ["customer_id", "nombre", "email", "cltv", "frecuencia",
                "dias_ultima_compra", "return_rate", "churn_proba"]
        top20 = sub[cols].sort_values("cltv", ascending=False).head(20).copy()
        top20["cltv"]        = top20["cltv"].round(2)
        top20["return_rate"] = top20["return_rate"].round(3)
        top20["churn_proba"] = (top20["churn_proba"] * 100).round(1)
        top20.columns = ["ID", "Nombre", "Email", "CLTV (€)", "Frecuencia",
                          "Días última compra", "Return rate", "Churn risk (%)"]
        st.dataframe(top20, use_container_width=True, hide_index=True, height=400)

    key_insight(
        "Cada segmento tiene un comportamiento muy distinto y necesita "
        "<b>una estrategia distinta</b>. La tabla comparativa muestra exactamente "
        "dónde está el desfase del segmento respecto al resto de la cartera."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 8. PÁGINA 3 — PLAN DE CHOQUE
# ─────────────────────────────────────────────────────────────────────────────
def page_plan_choque():
    all_segments = ["VIP Champion", "Regular Activo", "Perdido", "Devolutivo"]

    # Estado para presets
    if "preset" not in st.session_state:
        st.session_state.preset = None

    # ── Quick presets ───────────────────────────────────────────────────────
    with st.container(border=True):
        window_title("Presets rápidos",
                      "Configuraciones de filtros pre-cargadas para casos típicos")
        p1, p2, p3, p4, p5 = st.columns(5)
        if p1.button("VIPs en riesgo",  use_container_width=True):
            st.session_state.preset = "vip_risk"
        if p2.button("Recuperar VIPs perdidos", use_container_width=True):
            st.session_state.preset = "vip_lost"
        if p3.button("Devolutivos activos", use_container_width=True):
            st.session_state.preset = "dev_active"
        if p4.button("Convertir Regular Activos",  use_container_width=True):
            st.session_state.preset = "reg_active"
        if p5.button("Reset",  use_container_width=True):
            st.session_state.preset = None

    preset_defaults = {
        "vip_risk":   {"segments": ["VIP Champion"], "churn": "En riesgo",
                        "cltv_range": (10000.0, float(df_seg["cltv"].max()) + 1)},
        "vip_lost":   {"segments": ["VIP Champion"], "churn": "Perdido",
                        "cltv_range": (10000.0, float(df_seg["cltv"].max()) + 1)},
        "dev_active": {"segments": ["Devolutivo"],   "churn": "Activo",
                        "cltv_range": (0.0, float(df_seg["cltv"].max()) + 1)},
        "reg_active": {"segments": ["Regular Activo"], "churn": "Activo",
                        "cltv_range": (0.0, float(df_seg["cltv"].max()) + 1)},
    }
    defaults = preset_defaults.get(st.session_state.preset,
                                    {"segments": all_segments, "churn": "Todos",
                                     "cltv_range": (0.0, float(df_seg["cltv"].max()) + 1)})

    # ── Filtros ─────────────────────────────────────────────────────────────
    with st.container(border=True):
        window_title("Filtros manuales")
        f1, f2, f3 = st.columns([3, 2, 3])
        with f1:
            segments = st.multiselect("Segmento", options=all_segments,
                                       default=defaults["segments"])
        with f2:
            churn_options = ["Todos", "Activo", "En riesgo", "Perdido"]
            churn_status = st.selectbox(
                "Estado Churn", options=churn_options,
                index=churn_options.index(defaults["churn"]),
            )
        with f3:
            cltv_max = float(df_seg["cltv"].max())
            cltv_range = st.slider(
                "Rango CLTV (€)",
                min_value=0.0, max_value=float(int(cltv_max) + 1),
                value=defaults["cltv_range"], step=100.0,
            )

    # Aplicar filtros
    filtered = df_seg[df_seg["cluster_label"].isin(segments)] if segments else df_seg.iloc[0:0]
    filtered = filtered[
        (filtered["cltv"] >= cltv_range[0]) & (filtered["cltv"] <= cltv_range[1])
    ]
    if churn_status != "Todos":
        filtered = filtered[filtered["estado_churn"] == churn_status]

    # ── KPIs de la selección ────────────────────────────────────────────────
    with st.container(border=True):
        window_title("KPIs de la selección",
                      "Resumen de los clientes filtrados — sobre los que se actuará")
        n               = len(filtered)
        ingresos_sel    = filtered["ingresos"].sum() if n > 0 else 0
        cltv_total_sel  = filtered["cltv"].sum() if n > 0 else 0
        churn_avg       = (filtered["churn_proba"].dropna().mean() * 100) if n > 0 else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Clientes filtrados",  f"{n:,}",
                   delta=f"{n / max(len(df_seg), 1) * 100:.1f}% cartera",
                   delta_color="off")
        k2.metric("Ingresos generados",  f"€ {ingresos_sel:,.0f}")
        k3.metric("CLTV total",          f"€ {cltv_total_sel:,.0f}")
        k4.metric("Churn risk medio",
                   f"{churn_avg:.1f}%" if not np.isnan(churn_avg) else "—")

    # ── Distribución del riesgo + Breakdown segmento ────────────────────────
    if n > 0:
        c1, c2 = st.columns(2)
        with c1:
            with st.container(border=True):
                window_title("Distribución de churn risk en la selección")
                proba_data = filtered["churn_proba"].dropna()
                if len(proba_data) == 0:
                    st.info("Sin datos de churn_proba.")
                else:
                    fig = go.Figure(go.Histogram(
                        x=proba_data, nbinsx=25,
                        marker=dict(color=PRIMARY, line=dict(color=CARD, width=1)),
                    ))
                    fig.add_vline(x=0.30, line_dash="dash", line_color=ACCENT,
                                   annotation_text="30%", annotation_position="top")
                    fig.add_vline(x=0.70, line_dash="dash", line_color=DANGER,
                                   annotation_text="70%", annotation_position="top")
                    fig.update_xaxes(title="Probabilidad de churn")
                    fig.update_yaxes(title="Nº clientes")
                    st.plotly_chart(themed(fig, height=300, legend_bottom=False,
                                            show_legend=False),
                                    use_container_width=True)

        with c2:
            with st.container(border=True):
                window_title("Breakdown por segmento")
                seg_count = filtered["cluster_label"].value_counts().reset_index()
                seg_count.columns = ["Segmento", "Clientes"]
                fig = go.Figure(go.Bar(
                    x=seg_count["Clientes"], y=seg_count["Segmento"], orientation="h",
                    marker=dict(color=[CLUSTER_COLORS[s] for s in seg_count["Segmento"]]),
                    text=[f"{v:,}" for v in seg_count["Clientes"]],
                    textposition="outside",
                ))
                fig.update_xaxes(title="Clientes")
                st.plotly_chart(themed(fig, height=300, legend_bottom=False,
                                        show_legend=False),
                                use_container_width=True)

    # ── Tabla de prioridad estratégica ──────────────────────────────────────
    if n > 0:
        with st.container(border=True):
            window_title("Top 20 por prioridad estratégica",
                          "Ordenados por CLTV × Churn risk — alto valor con alto riesgo de fuga")
            pf = filtered.copy()
            pf["priority_score"] = pf["cltv"] * pf["churn_proba"].fillna(0)
            cols_pri = ["customer_id", "nombre", "email", "phone",
                         "cluster_label", "cltv", "churn_proba",
                         "dias_ultima_compra", "priority_score"]
            top_pri = pf[cols_pri].sort_values("priority_score", ascending=False).head(20).copy()
            top_pri["cltv"]           = top_pri["cltv"].round(2)
            top_pri["churn_proba"]    = (top_pri["churn_proba"] * 100).round(1)
            top_pri["priority_score"] = top_pri["priority_score"].round(0)
            top_pri.columns = ["ID", "Nombre", "Email", "Teléfono",
                                "Segmento", "CLTV (€)", "Churn risk (%)",
                                "Días última compra", "Prioridad"]
            st.dataframe(top_pri, use_container_width=True, hide_index=True, height=400)

    # ── Tabla completa + descarga ───────────────────────────────────────────
    with st.container(border=True):
        window_title(f"Lista de clientes filtrados ({len(filtered):,})",
                      "Tabla completa con datos de contacto — descargable como CSV")

        cols_show = ["customer_id", "nombre", "email", "phone",
                     "cluster_label", "cltv", "dias_ultima_compra",
                     "frecuencia", "churn_proba", "return_rate"]
        display_df = (filtered[cols_show]
                       .sort_values("cltv", ascending=False)
                       .head(1000).copy())
        display_df["cltv"]        = display_df["cltv"].round(2)
        display_df["return_rate"] = display_df["return_rate"].round(3)
        display_df["churn_proba"] = (display_df["churn_proba"] * 100).round(1)
        display_df.columns = ["ID", "Nombre", "Email", "Teléfono",
                               "Segmento", "CLTV (€)", "Días última compra",
                               "Frecuencia", "Churn risk (%)", "Return rate"]
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=420)
        st.caption(f"Mostrando los primeros 1.000 sobre {len(filtered):,} filtrados.")

        csv_bytes = (filtered[cols_show]
                      .sort_values("cltv", ascending=False)
                      .to_csv(index=False).encode("utf-8"))
        st.download_button(
            label="Descargar lista completa para CRM / email marketing",
            data=csv_bytes,
            file_name=f"clientes_plan_choque_{len(filtered)}.csv",
            mime="text/csv", type="primary",
        )

    # ── Calculadora ROI + Sensibilidad ──────────────────────────────────────
    with st.container(border=True):
        window_title("Calculadora de ROI",
                      "Define los parámetros y mira el retorno esperado")
        cltv_avg = filtered["cltv"].mean() if len(filtered) > 0 else 100.0
        if pd.isna(cltv_avg) or cltv_avg <= 0:
            cltv_avg = 100.0

        ic1, ic2, ic3 = st.columns(3)
        with ic1:
            cost_per = st.number_input("Coste por cliente (€)",
                                        min_value=0.0, max_value=500.0,
                                        value=5.0, step=0.5)
        with ic2:
            success_rate = st.slider("Tasa de éxito estimada (%)", 1, 30, 5)
        with ic3:
            avg_revenue = st.number_input(
                "Ingreso medio por cliente recuperado (€)",
                min_value=0.0, max_value=1_000_000.0,
                value=float(round(cltv_avg, 2)), step=50.0,
            )

        n_filt          = len(filtered)
        recovered       = int(round(n_filt * success_rate / 100))
        total_cost      = n_filt * cost_per
        expected_revenue = recovered * avg_revenue
        roi = ((expected_revenue - total_cost) / total_cost * 100) if total_cost > 0 else 0.0

        def card(col, label, value, kind=""):
            cls = "roi-card"
            if kind == "success": cls += " success"
            elif kind == "danger": cls += " danger"
            col.markdown(
                f"<div class='{cls}'><div class='label'>{label}</div>"
                f"<div class='value'>{value}</div></div>",
                unsafe_allow_html=True,
            )

        st.write("")
        c1, c2, c3, c4, c5 = st.columns(5)
        card(c1, "Clientes contactados",  f"{n_filt:,}")
        card(c2, "Recuperados estimados", f"{recovered:,}")
        card(c3, "Coste total",           f"€ {total_cost:,.0f}")
        card(c4, "Ingreso esperado",      f"€ {expected_revenue:,.0f}")
        card(c5, "ROI", f"{roi:+,.1f}%",
              kind="success" if roi > 0 else "danger")

        # Sensibilidad
        st.markdown("<div class='section-label'>Análisis de sensibilidad</div>",
                    unsafe_allow_html=True)
        st.caption("Cómo varía el ROI según la tasa de éxito de la campaña.")
        scenarios = []
        for rate in [2, 3, 5, 8, 10, 15, 20, 25]:
            rec = int(round(n_filt * rate / 100))
            cost = n_filt * cost_per
            rev = rec * avg_revenue
            sroi = (rev - cost) / cost * 100 if cost > 0 else 0
            scenarios.append({
                "Tasa éxito (%)": rate, "Recuperados": rec,
                "Coste (€)": f"{cost:,.0f}", "Ingreso (€)": f"{rev:,.0f}",
                "ROI (%)": f"{sroi:+.1f}",
            })
        st.dataframe(pd.DataFrame(scenarios), use_container_width=True, hide_index=True)

    key_insight(
        "Esta es la <b>lista exacta</b> de clientes a los que llamar mañana. "
        "El bloque de prioridad estratégica destaca los <b>VIPs en riesgo</b>, "
        "donde cada euro invertido tiene el mayor retorno. "
        "El análisis de sensibilidad sirve para defender la campaña ante dirección."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 9. PÁGINA 4 — INTELIGENCIA DEL MODELO
# ─────────────────────────────────────────────────────────────────────────────
def page_inteligencia():
    model     = model_bundle["model"]
    feat_cols = model_bundle["feature_cols"]
    auc       = model_bundle.get("auc_test", 0)
    name      = model_bundle.get("model_name", "modelo")
    cutoff    = model_bundle.get("cutoff_date", "—")[:10]

    # ── KPIs del modelo ─────────────────────────────────────────────────────
    with st.container(border=True):
        window_title("Estadísticas del modelo",
                      "Resumen del clasificador entrenado en la Fase 6")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Algoritmo",       name)
        k2.metric("AUC-ROC test",    f"{auc:.4f}")
        k3.metric("Features",        f"{len(feat_cols)}")
        k4.metric("Fecha de corte",  cutoff)

    # ── Feature importance ──────────────────────────────────────────────────
    with st.container(border=True):
        window_title("Importancia de variables",
                      "Cuánto contribuye cada feature a la predicción del modelo")
        imp = (pd.Series(model.feature_importances_, index=feat_cols)
                 .sort_values(ascending=True))
        imp_pct = imp / imp.sum() * 100

        c1, c2 = st.columns([3, 2])
        with c1:
            fig = go.Figure(go.Bar(
                x=imp.values, y=imp.index, orientation="h",
                marker=dict(color=PRIMARY, line=dict(color="white", width=1)),
                text=[f"{v:.3f}" for v in imp.values],
                textposition="outside",
            ))
            fig.update_xaxes(title="Importancia (gain XGBoost)")
            st.plotly_chart(themed(fig, height=360, legend_bottom=False,
                                    show_legend=False),
                            use_container_width=True)
        with c2:
            imp_table = pd.DataFrame({
                "Variable": imp.index[::-1],
                "Importancia": imp.values[::-1].round(4),
                "% del total": imp_pct.values[::-1].round(1),
            })
            st.dataframe(imp_table, use_container_width=True, hide_index=True,
                         height=360)

        st.markdown("**Lectura en lenguaje de negocio:**")
        explanations = {
            "frecuencia":   "**Número de tickets distintos.** Predictor **dominante** en este dataset: un cliente con una sola compra antes del corte tiene una probabilidad altísima de no volver, mientras que con dos o más se forma el hábito.",
            "recencia":     "**Días desde la última compra.** Aporta refinamiento sobre la frecuencia: clientes con misma frecuencia pero distinta recencia se separan mejor.",
            "cltv_parcial": "**CLTV acumulado hasta el corte.** Combina ingresos, margen y duración. Refleja el valor económico del cliente.",
            "avg_ticket":   "**Ticket medio.** Tamaño promedio de cada compra. Tickets bajos correlacionan con volatilidad.",
            "return_rate":  "**Tasa de devolución.** Un return rate alto puede señalar insatisfacción.",
            "margen_ratio": "**Margen relativo.** Estable en el dataset (~0.40), aporta poca señal predictiva.",
        }
        for feat in imp.index[::-1]:
            if feat in explanations:
                st.markdown(f"- {explanations[feat]}")

    # ── Histograma global + Boxplot por segmento ────────────────────────────
    c1, c2 = st.columns(2)

    with c1:
        with st.container(border=True):
            window_title("Distribución global de churn_proba",
                          "Todos los clientes con predicción disponible")
            proba_global = df_seg["churn_proba"].dropna()
            fig = go.Figure(go.Histogram(
                x=proba_global, nbinsx=30,
                marker=dict(color=PRIMARY, line=dict(color=CARD, width=1)),
            ))
            fig.add_vline(x=0.30, line_dash="dash", line_color=ACCENT,
                           annotation_text="30%", annotation_position="top")
            fig.add_vline(x=0.70, line_dash="dash", line_color=DANGER,
                           annotation_text="70%", annotation_position="top")
            fig.update_xaxes(title="Probabilidad de churn")
            fig.update_yaxes(title="Nº clientes")
            st.plotly_chart(themed(fig, height=380, legend_bottom=False,
                                    show_legend=False),
                            use_container_width=True)

    with c2:
        with st.container(border=True):
            window_title("Churn risk por segmento")
            sub = df_seg.dropna(subset=["churn_proba"]).copy()
            fig = px.box(
                sub, x="cluster_label", y="churn_proba",
                color="cluster_label", color_discrete_map=CLUSTER_COLORS,
                points="outliers",
            )
            fig.update_xaxes(title="Segmento")
            fig.update_yaxes(title="Probabilidad de churn", range=[-0.02, 1.02])
            st.plotly_chart(themed(fig, height=380, legend_bottom=False,
                                    show_legend=False),
                            use_container_width=True)

    # ── Matriz confusión proxy + ROC ────────────────────────────────────────
    sub_eval = df_seg.dropna(subset=["churn_proba"]).copy()
    if len(sub_eval) > 0:
        # Usamos estado_churn == "Perdido" como verdad binaria proxy
        truth = (sub_eval["estado_churn"] == "Perdido").astype(int).values
        pred  = (sub_eval["churn_proba"] > 0.5).astype(int).values

        c1, c2 = st.columns(2)

        with c1:
            with st.container(border=True):
                window_title("Matriz de confusión (proxy)",
                              "Predicho (proba > 0.5) vs estado_churn == 'Perdido'")
                cm = confusion_matrix(truth, pred)
                cm_df = pd.DataFrame(
                    cm,
                    index=["Real: No perdido", "Real: Perdido"],
                    columns=["Pred: No churn", "Pred: Churn"],
                )
                fig = px.imshow(
                    cm_df, text_auto=True,
                    color_continuous_scale=[[0, CARD], [1, PRIMARY]],
                    aspect="auto",
                )
                fig.update_layout(coloraxis_showscale=False)
                st.plotly_chart(themed(fig, height=340, legend_bottom=False,
                                        show_legend=False),
                                use_container_width=True)
                tn, fp, fn, tp = cm.ravel()
                acc  = (tp + tn) / max(tp + tn + fp + fn, 1) * 100
                prec = tp / max(tp + fp, 1) * 100
                rec  = tp / max(tp + fn, 1) * 100
                st.caption(
                    f"Accuracy: **{acc:.1f}%** · Precision: **{prec:.1f}%** · "
                    f"Recall: **{rec:.1f}%**"
                )

        with c2:
            with st.container(border=True):
                window_title("Curva ROC (proxy)",
                              "AUC sobre el proxy estado_churn=='Perdido'")
                try:
                    fpr, tpr, _ = roc_curve(truth, sub_eval["churn_proba"].values)
                    auc_proxy = roc_auc_score(truth, sub_eval["churn_proba"].values)
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=fpr, y=tpr, mode="lines",
                        line=dict(color=PRIMARY, width=2.5),
                        fill="tozeroy", fillcolor="rgba(30, 58, 95, 0.10)",
                        name=f"Modelo (AUC={auc_proxy:.3f})",
                    ))
                    fig.add_trace(go.Scatter(
                        x=[0, 1], y=[0, 1], mode="lines",
                        line=dict(color=MUTED, dash="dash"),
                        name="Aleatorio",
                    ))
                    fig.update_xaxes(title="FPR")
                    fig.update_yaxes(title="TPR")
                    st.plotly_chart(themed(fig, height=340), use_container_width=True)
                except Exception as e:
                    st.warning(f"No se pudo calcular ROC: {e}")

    # ── Heatmap correlación ─────────────────────────────────────────────────
    with st.container(border=True):
        window_title("Correlación entre variables del cliente",
                      "Coeficientes de Pearson sobre todas las features observables")
        cols_corr = ["cltv", "ingresos", "frecuencia", "anios_relacion",
                     "dias_ultima_compra", "return_rate", "items_comprados",
                     "items_devueltos", "churn_proba"]
        corr = df_seg[cols_corr].corr().round(2)
        fig = px.imshow(
            corr, text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1, zmax=1, aspect="auto",
        )
        fig.update_layout(coloraxis_colorbar=dict(title="ρ", thickness=12))
        st.plotly_chart(themed(fig, height=440, legend_bottom=False, show_legend=False),
                        use_container_width=True)

    key_insight(
        "La <b>frecuencia de compra</b> es el predictor dominante en este dataset: "
        "una única compra antes del corte predice churn casi de forma determinista. "
        "La acción clave es <b>conseguir la segunda compra</b> — convertir al cliente "
        "one-shot en cliente recurrente es lo que marca la diferencia."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 10. PÁGINA 5 — EVOLUCIÓN TEMPORAL
# ─────────────────────────────────────────────────────────────────────────────
def page_evolucion():
    sales = load_sales_facts()

    # Precálculos
    sales_m = sales.copy()
    sales_m["ym"] = sales_m["date"].dt.to_period("M").astype(str)
    monthly_rev    = sales_m.groupby("ym")["subtotal"].sum().reset_index()
    monthly_tickets = sales_m.groupby("ym")["sale_id"].nunique().reset_index(name="tickets")
    monthly_merged = monthly_rev.merge(monthly_tickets, on="ym")
    monthly_merged["ticket_medio"] = monthly_merged["subtotal"] / monthly_merged["tickets"]
    monthly_merged["acumulado"]    = monthly_merged["subtotal"].cumsum()

    first_sale = sales.groupby("customer_id")["date"].min().reset_index()
    first_sale["ym"] = first_sale["date"].dt.to_period("M").astype(str)
    first_sale["cohort_year"] = first_sale["date"].dt.year
    new_monthly = first_sale.groupby("ym").size().reset_index(name="nuevos")

    cohort_cltv = (
        first_sale.merge(df_seg[["customer_id", "cltv"]], on="customer_id")
                   .groupby("cohort_year")["cltv"]
                   .agg(["mean", "median", "count"]).reset_index()
    )

    # KPIs de evolución
    years_pres   = sorted(sales["year"].unique())
    if len(years_pres) >= 2:
        ly = years_pres[-1]; py = years_pres[-2]
        rev_ly = sales[sales["year"] == ly]["subtotal"].sum()
        rev_py = sales[sales["year"] == py]["subtotal"].sum()
        yoy = (rev_ly - rev_py) / max(rev_py, 1) * 100
    else:
        ly = years_pres[-1] if years_pres else None
        rev_ly = sales[sales["year"] == ly]["subtotal"].sum() if ly else 0
        yoy = 0
    new_clients_ly = first_sale[first_sale["date"].dt.year == ly].shape[0] if ly else 0

    # ── KPIs ────────────────────────────────────────────────────────────────
    with st.container(border=True):
        window_title("KPIs temporales",
                      "Evolución comercial del último periodo registrado")
        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Periodo cubierto",
                   f"{sales['date'].min().date()} →" if ly else "—",
                   delta=f"{sales['date'].max().date()}", delta_color="off")
        k2.metric(f"Ingresos {ly}", f"€ {rev_ly:,.0f}")
        k3.metric("Crecimiento YoY",
                   f"{yoy:+.1f}%",
                   delta=f"vs {years_pres[-2] if len(years_pres) >= 2 else '—'}",
                   delta_color=("normal" if yoy >= 0 else "inverse"))
        k4.metric(f"Nuevos clientes {ly}", f"{new_clients_ly:,}")

    # ── Ventas mensuales + acumulado (doble eje) ────────────────────────────
    with st.container(border=True):
        window_title("Ventas mensuales + acumulado",
                      "Línea = ventas del mes · área = ingresos acumulados")
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(
            x=monthly_merged["ym"], y=monthly_merged["subtotal"],
            name="Mensual", marker=dict(color=PRIMARY),
            hovertemplate="%{x}<br>€%{y:,.0f}<extra></extra>",
        ), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=monthly_merged["ym"], y=monthly_merged["acumulado"],
            mode="lines+markers", name="Acumulado",
            line=dict(color=ACCENT, width=2.5),
            marker=dict(size=5),
            hovertemplate="%{x}<br>€%{y:,.0f} acum<extra></extra>",
        ), secondary_y=True)
        fig.update_xaxes(title="Mes")
        fig.update_yaxes(title="Ingresos del mes (€)", secondary_y=False)
        fig.update_yaxes(title="Ingresos acumulados (€)", secondary_y=True)
        st.plotly_chart(themed(fig, height=380),
                        use_container_width=True)

    # ── Nuevos clientes + Ticket medio ──────────────────────────────────────
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            window_title("Nuevos clientes por mes",
                          "Adquisición mensual de cuentas únicas")
            fig = go.Figure(go.Bar(
                x=new_monthly["ym"], y=new_monthly["nuevos"],
                marker=dict(color=PRIMARY, line=dict(color="white", width=0.5)),
            ))
            fig.update_xaxes(title="Mes")
            fig.update_yaxes(title="Nuevos clientes")
            st.plotly_chart(themed(fig, height=340, legend_bottom=False,
                                    show_legend=False),
                            use_container_width=True)

    with c2:
        with st.container(border=True):
            window_title("Ticket medio mensual",
                          "Ingresos / nº tickets por mes")
            fig = go.Figure(go.Scatter(
                x=monthly_merged["ym"], y=monthly_merged["ticket_medio"],
                mode="lines+markers",
                line=dict(color=ACCENT, width=2.2),
                marker=dict(size=5, color=PRIMARY),
                fill="tozeroy", fillcolor="rgba(200, 169, 81, 0.15)",
            ))
            fig.update_xaxes(title="Mes")
            fig.update_yaxes(title="Ticket medio (€)")
            st.plotly_chart(themed(fig, height=340, legend_bottom=False,
                                    show_legend=False),
                            use_container_width=True)

    # ── Heatmap calendario año × mes ────────────────────────────────────────
    with st.container(border=True):
        window_title("Mapa de calor de ingresos: año × mes",
                      "Mirada compacta para detectar patrones estacionales y tendencia")
        pivot = sales.pivot_table(values="subtotal", index="year",
                                   columns="month", aggfunc="sum").fillna(0)
        mes_labels = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                      "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        pivot.columns = [mes_labels[m - 1] for m in pivot.columns]
        fig = px.imshow(
            pivot, text_auto=".2s",
            color_continuous_scale="YlOrBr", aspect="auto",
        )
        fig.update_layout(coloraxis_colorbar=dict(title="€", thickness=12))
        fig.update_xaxes(title="Mes")
        fig.update_yaxes(title="Año")
        st.plotly_chart(themed(fig, height=320, legend_bottom=False, show_legend=False),
                        use_container_width=True)

    # ── Cohortes ────────────────────────────────────────────────────────────
    with st.container(border=True):
        window_title("Análisis de cohortes (por año de alta)",
                      "Tamaño + CLTV medio + CLTV mediano de cada cohorte")
        c1, c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Bar(
                x=cohort_cltv["cohort_year"].astype(str),
                y=cohort_cltv["count"],
                marker=dict(color=PRIMARY),
                text=[f"{v:,}" for v in cohort_cltv["count"]],
                textposition="outside",
            ))
            fig.update_xaxes(title="Año de alta")
            fig.update_yaxes(title="Nº clientes")
            st.plotly_chart(themed(fig, height=320, legend_bottom=False,
                                    title="Tamaño de cohorte",
                                    show_legend=False),
                            use_container_width=True)
        with c2:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=cohort_cltv["cohort_year"].astype(str),
                y=cohort_cltv["mean"],
                name="CLTV medio",
                marker=dict(color=ACCENT, line=dict(color=PRIMARY, width=1)),
                text=[f"€{v:,.0f}" for v in cohort_cltv["mean"]],
                textposition="outside",
            ))
            fig.add_trace(go.Scatter(
                x=cohort_cltv["cohort_year"].astype(str),
                y=cohort_cltv["median"],
                mode="lines+markers", name="CLTV mediano",
                line=dict(color=PRIMARY, width=2),
                marker=dict(size=8),
            ))
            fig.update_xaxes(title="Año de alta")
            fig.update_yaxes(title="CLTV (€)")
            st.plotly_chart(themed(fig, height=320,
                                    title="CLTV medio vs mediano"),
                            use_container_width=True)

    # ── Estacionalidad ──────────────────────────────────────────────────────
    with st.container(border=True):
        window_title("Estacionalidad",
                      "Día de la semana · Mes del año")

        dow_labels = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
        sales_dow = (sales.groupby("day_of_week")["subtotal"].sum()
                            .reindex(range(1, 8)).fillna(0).reset_index())
        sales_dow["dia"] = [dow_labels[d - 1] for d in sales_dow["day_of_week"]]

        mes_labels2 = ["Ene", "Feb", "Mar", "Abr", "May", "Jun",
                        "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
        sales_month = (sales.groupby("month")["subtotal"].sum()
                              .reindex(range(1, 13)).fillna(0).reset_index())
        sales_month["mes"] = [mes_labels2[m - 1] for m in sales_month["month"]]

        c1, c2 = st.columns(2)
        with c1:
            colors_dow = [DANGER if d >= 6 else PRIMARY for d in sales_dow["day_of_week"]]
            fig = go.Figure(go.Bar(
                x=sales_dow["dia"], y=sales_dow["subtotal"],
                marker=dict(color=colors_dow),
                text=[f"€{v/1000:,.0f}K" for v in sales_dow["subtotal"]],
                textposition="outside",
            ))
            fig.update_yaxes(title="Ingresos (€)")
            st.plotly_chart(themed(fig, height=320, title="Por día de la semana",
                                    legend_bottom=False, show_legend=False),
                            use_container_width=True)
        with c2:
            fig = go.Figure(go.Bar(
                x=sales_month["mes"], y=sales_month["subtotal"],
                marker=dict(color=PRIMARY),
                text=[f"€{v/1000:,.0f}K" for v in sales_month["subtotal"]],
                textposition="outside",
            ))
            fig.update_yaxes(title="Ingresos (€)")
            st.plotly_chart(themed(fig, height=320, title="Por mes del año",
                                    legend_bottom=False, show_legend=False),
                            use_container_width=True)

    # Insight final
    best_dow_idx = sales_dow["subtotal"].idxmax()
    best_dow = sales_dow.loc[best_dow_idx, "dia"]
    oldest = cohort_cltv.iloc[0]
    newest = cohort_cltv.iloc[-1]
    key_insight(
        f"El negocio tiene <b>estacionalidad clara</b> (pico en <b>{best_dow}</b>). "
        f"La cohorte de <b>{int(oldest['cohort_year'])}</b> tiene un CLTV medio "
        f"<b>{oldest['mean'] / max(newest['mean'], 1):.1f}×</b> superior a la de "
        f"<b>{int(newest['cohort_year'])}</b>: el tiempo de relación importa "
        f"enormemente para el valor del cliente, y el crecimiento YoY "
        f"actual es del <b>{yoy:+.1f}%</b>."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 11. Layout: hero + tabs centradas
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="hero">
        <h1>K-Salud Analytics</h1>
        <div class="subtitle">Customer Intelligence Dashboard</div>
        <div class="rule"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_v, tab_s, tab_p, tab_i, tab_e = st.tabs([
    "Visión General",
    "Análisis de Segmentos",
    "Plan de Choque",
    "Inteligencia del Modelo",
    "Evolución Temporal",
])

with tab_v:
    page_vision_general()
with tab_s:
    page_segmentos()
with tab_p:
    page_plan_choque()
with tab_i:
    page_inteligencia()
with tab_e:
    page_evolucion()

# ─────────────────────────────────────────────────────────────────────────────
# 12. Footer
# ─────────────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class='footer-text'>
        <b>Proyecto Final · Gestión de Datos · UAX 2026</b><br>
        Álvaro González Fernández
    </div>
    """,
    unsafe_allow_html=True,
)
