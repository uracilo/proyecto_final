
import io
import sys
import math
import numpy as np
import pandas as pd
import streamlit as st
import seaborn as sns
import matplotlib.pyplot as plt
from typing import Optional

st.set_page_config(page_title="Netflix Data Dashboard", layout="wide")

# ----------------------
# Helpers
# ----------------------
@st.cache_data(show_spinner=False)
def load_csv(file) -> pd.DataFrame:
    return pd.read_csv(file)

def coerce_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # release_year -> numeric
    if "release_year" in out.columns:
        out["release_year_num"] = pd.to_numeric(out["release_year"], errors="coerce")
    # duration -> numeric (minutes for Movies / seasons for TV Show)
    if "duration" in out.columns:
        extracted = out["duration"].astype(str).str.extract(r"(\d+)")[0]
        out["duration_num"] = pd.to_numeric(extracted, errors="coerce")
    return out

def count_by_year(df: pd.DataFrame, content_type: Optional[str] = None) -> pd.Series:
    q = df
    if content_type in ("Movie", "TV Show"):
        q = q[q["type"] == content_type]
    if "release_year_num" not in q.columns:
        return pd.Series(dtype="int64")
    return q["release_year_num"].dropna().astype(int).value_counts().sort_index()

# ----------------------
# Sidebar
# ----------------------
st.sidebar.title("🎛️ Controles")

uploaded = st.sidebar.file_uploader("Sube tu CSV de Netflix (Kaggle)", type=["csv"])
sample_notice = """
**Nota**: Este dashboard está pensado para el dataset de Kaggle (Netflix Movies and TV Shows). 
Si tu CSV tiene columnas diferentes, ajusta las opciones de columnas más abajo.
"""
st.sidebar.info(sample_notice, icon="ℹ️")

pairplot_rows = st.sidebar.slider("Límite de filas para Pairplot (muestra aleatoria)", 200, 5000, 1000, step=100)
show_reg = st.sidebar.checkbox("Agregar línea de regresión en scatter (regplot)", value=False)
content_filter = st.sidebar.selectbox("Filtrar por tipo", ["Todos", "Movie", "TV Show"])

# ----------------------
# Main
# ----------------------
st.title("📺 Netflix Data Dashboard")

if uploaded is None:
    st.warning("Sube un CSV para comenzar (por ejemplo, `netflix_titles.csv`).")
    st.stop()

try:
    data = load_csv(uploaded)
except Exception as e:
    st.error(f"No se pudo leer el CSV: {e}")
    st.stop()

# Column mapping helpers (in case user CSV differs slightly)
default_release_col = "release_year" if "release_year" in data.columns else None
default_duration_col = "duration" if "duration" in data.columns else None
default_type_col = "type" if "type" in data.columns else None

with st.expander("⚙️ Mapear columnas (opcional)", expanded=False):
    release_col = st.selectbox("Columna de año de estreno", [None] + list(data.columns), index=(list(data.columns).index(default_release_col)+1 if default_release_col in data.columns else 0))
    duration_col = st.selectbox("Columna de duración", [None] + list(data.columns), index=(list(data.columns).index(default_duration_col)+1 if default_duration_col in data.columns else 0))
    type_col = st.selectbox("Columna de tipo (Movie / TV Show)", [None] + list(data.columns), index=(list(data.columns).index(default_type_col)+1 if default_type_col in data.columns else 0))

# If user mapped different names, align to canonical ones
data = data.copy()
if release_col and release_col != "release_year":
    data["release_year"] = data[release_col]
if duration_col and duration_col != "duration":
    data["duration"] = data[duration_col]
if type_col and type_col != "type":
    data["type"] = data[type_col]

df = coerce_numeric_columns(data)

if content_filter in ("Movie", "TV Show") and "type" in df.columns:
    df_view = df[df["type"] == content_filter]
else:
    df_view = df

# ----------------------
# KPIs
# ----------------------
left, mid, right = st.columns(3)
with left:
    total = len(df_view)
    st.metric("Registros", f"{total:,}")
with mid:
    if "release_year_num" in df_view.columns:
        years = df_view["release_year_num"].dropna()
        if not years.empty:
            st.metric("Rango de años", f"{int(years.min())} — {int(years.max())}")
        else:
            st.metric("Rango de años", "N/D")
    else:
        st.metric("Rango de años", "N/D")
with right:
    if "duration_num" in df_view.columns:
        d = df_view["duration_num"].dropna()
        if not d.empty:
            st.metric("Duración/Temporadas (mediana)", f"{np.median(d):.0f}")
        else:
            st.metric("Duración/Temporadas (mediana)", "N/D")
    else:
        st.metric("Duración/Temporadas (mediana)", "N/D")

st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📈 Tendencias", "🧪 Pairplot", "🔗 Correlaciones", "📊 Scatter"])

# ----------------------
# Tab 1: Trends
# ----------------------
with tab1:
    st.subheader("Títulos por año de estreno")
    counts = count_by_year(df_view, content_type=None if content_filter == "Todos" else content_filter)
    if counts.empty:
        st.info("No hay datos suficientes para esta vista.")
    else:
        fig, ax = plt.subplots(figsize=(10, 4))
        sns.lineplot(x=counts.index, y=counts.values, ax=ax)
        ax.set_xlabel("Año")
        ax.set_ylabel("Cantidad")
        st.pyplot(fig, clear_figure=True)

# ----------------------
# Tab 2: Pairplot (numeric relations)
# ----------------------
with tab2:
    st.subheader("Relaciones entre columnas numéricas (pairplot)")
    numeric_cols = df_view.select_dtypes(include="number").columns.tolist()
    if not numeric_cols:
        st.info("No hay columnas numéricas para mostrar. Asegúrate de haber convertido `release_year` y `duration`.")
    else:
        sel = st.multiselect("Selecciona columnas numéricas", numeric_cols, default=numeric_cols[:min(4,len(numeric_cols))])
        if len(sel) < 2:
            st.info("Selecciona al menos dos columnas.")
        else:
            # Sample to keep it lightweight
            plot_df = df_view[sel].dropna()
            if len(plot_df) > pairplot_rows:
                plot_df = plot_df.sample(pairplot_rows, random_state=42)
            with st.spinner("Generando pairplot..."):
                g = sns.pairplot(plot_df, diag_kind="hist")
                st.pyplot(g.fig, clear_figure=True)

# ----------------------
# Tab 3: Correlations
# ----------------------
with tab3:
    st.subheader("Matriz de correlación")
    numeric_df = df_view.select_dtypes(include="number").dropna(axis=1, how="all")
    if numeric_df.empty or numeric_df.shape[1] < 2:
        st.info("No hay suficientes columnas numéricas para calcular correlaciones.")
    else:
        corr = numeric_df.corr(numeric_only=True)
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.heatmap(corr, annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
        st.pyplot(fig, clear_figure=True)

# ----------------------
# Tab 4: Scatter / Regresiones
# ----------------------
with tab4:
    st.subheader("Relación con el año de estreno")
    if "release_year_num" not in df_view.columns:
        st.info("No existe `release_year_num`. Mapea y convierte primero la columna de año.")
    else:
        numeric_cols = [c for c in df_view.select_dtypes(include="number").columns if c != "release_year_num"]
        if not numeric_cols:
            st.info("No hay columnas numéricas para comparar.")
        else:
            ycol = st.selectbox("Variable numérica (Y)", numeric_cols, index=0)
            plot_df = df_view[["release_year_num", ycol]].dropna()
            if plot_df.empty:
                st.info("No hay datos suficientes para graficar.")
            else:
                fig, ax = plt.subplots(figsize=(10, 4))
                if show_reg:
                    sns.regplot(x="release_year_num", y=ycol, data=plot_df, ax=ax, scatter_kws=dict(s=20, alpha=0.6))
                else:
                    sns.scatterplot(x="release_year_num", y=ycol, data=plot_df, ax=ax, s=20)
                ax.set_xlabel("Año de estreno")
                ax.set_ylabel(ycol)
                st.pyplot(fig, clear_figure=True)

st.caption("Hecho con Streamlit • Seaborn • Matplotlib • Pandas")
