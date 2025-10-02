import io
import requests
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import folium
import plotly.express as px

st.set_page_config(page_title="Hospitales del Perú — Geoanálisis", layout="wide")

# --------- Fuente (Google Sheets) ---------
SHEET_ID = "10vy5pyNvLUAb2pCJLye7gaOPHOIhjdmzUTKdiUbF5oI"
GID = "0"  # <-- cambia por el gid real de la pestaña que usarás
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(show_spinner=True)
def load_data(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=30); r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    # Normaliza nombres de columnas
    df.columns = (df.columns.str.strip().str.lower()
                  .str.normalize('NFKD').str.encode('ascii', 'ignore').str.decode('utf-8')
                  .str.replace(r'[^a-z0-9]+','_', regex=True).str.strip('_'))
    # Limpieza básica
    for c in df.columns:
        if df[c].dtype == 'object':
            df[c] = df[c].fillna('').astype(str).str.strip()
    return df

st.title("Tarea: Análisis geoespacial de hospitales en el Perú")
st.caption("0) Medio ambiente y reproducibilidad — plantilla funcional con filtros, KPIs, gráfico y mapa.")

try:
    df = load_data(CSV_URL)
except Exception as e:
    st.error(f"No pude leer la hoja. Verifica el `gid` o permisos. Detalle: {e}")
    st.stop()

# Detección flexible de columnas
lat_col = next((c for c in ["lat","latitude","latitud"] if c in df.columns), None)
lon_col = next((c for c in ["lon","lng","longitude","longitud"] if c in df.columns), None)
dep_col = next((c for c in ["departamento","region","ambito","dep"] if c in df.columns), None)
tipo_col = next((c for c in ["tipo","categoria","nivel","clasificacion"] if c in df.columns), None)
name_col = next((c for c in ["establecimiento","hospital","nombre","name"] if c in df.columns), None)

# Sidebar filtros
st.sidebar.header("Filtros")
dep_sel = "Todos"
tipo_sel = "Todos"
texto = ""

if dep_col:
    deps = ["Todos"] + sorted(x for x in df[dep_col].dropna().astype(str).unique())
    dep_sel = st.sidebar.selectbox("Departamento/Región", deps, index=0)
if tipo_col:
    tipos = ["Todos"] + sorted(x for x in df[tipo_col].dropna().astype(str).unique())
    tipo_sel = st.sidebar.selectbox("Tipo/Categoría", tipos, index=0)
if name_col:
    texto = st.sidebar.text_input("Buscar por nombre (contiene)", "")

# Aplicar filtros
df_f = df.copy()
if dep_col and dep_sel != "Todos":
    df_f = df_f[df_f[dep_col].astype(str) == dep_sel]
if tipo_col and tipo_sel != "Todos":
    df_f = df_f[df_f[tipo_col].astype(str) == tipo_sel]
if name_col and texto:
    df_f = df_f[df_f[name_col].str.contains(texto, case=False, na=False)]

# KPIs
col_a, col_b, col_c = st.columns(3)
col_a.metric("Total de registros", f"{len(df):,}")
col_b.metric("Registros filtrados", f"{len(df_f):,}")
col_c.metric("Departamentos/Regiones", f"{df[dep_col].nunique():,}" if dep_col else "s/d")
st.divider()

# Gráfico
st.subheader("Distribución (Top 10)")
group_col = dep_col or tipo_col
if group_col:
    top = (df_f[group_col].replace("", "s/d")
           .value_counts().head(10).reset_index())
    top.columns = [group_col, "conteo"]
    fig = px.bar(top, x="conteo", y=group_col, orientation="h",
                 labels={"conteo":"N° establecimientos", group_col:group_col.capitalize()},
                 height=420)
    fig.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(l=10,r=10,t=10,b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No encontré columnas para agrupar (departamento/tipo).")
st.divider()

# Mapa
st.subheader("Mapa de establecimientos")
if not lat_col or not lon_col:
    st.warning("Faltan columnas de coordenadas (lat/lon). Agrega 'lat' y 'lon' o equivalentes.")
else:
    dmv = df_f.dropna(subset=[lat_col, lon_col]).copy()
    if dmv.empty:
        st.info("No hay filas con coordenadas válidas tras aplicar filtros.")
    else:
        dmv[lat_col] = dmv[lat_col].astype(float)
        dmv[lon_col] = dmv[lon_col].astype(float)
        center = [dmv[lat_col].mean(), dmv[lon_col].mean()]
        m = folium.Map(location=center, zoom_start=5, tiles="cartodbpositron")

        for _, r in dmv.iterrows():
            nombre = r[name_col] if name_col else "Establecimiento"
            folium.CircleMarker(
                location=[r[lat_col], r[lon_col]],
                radius=4, fill=True,
                tooltip=nombre,
                popup=folium.Popup(
                    f"<b>{nombre}</b><br>"
                    + (f"{dep_col.capitalize()}: {r[dep_col]}<br>" if dep_col else "")
                    + (f"{tipo_col.capitalize()}: {r[tipo_col]}<br>" if tipo_col else "")
                    + f"Lat: {r[lat_col]:.4f} · Lon: {r[lon_col]:.4f}",
                    max_width=300
                )
            ).add_to(m)

        st_folium(m, height=560, use_container_width=True)

st.divider()
st.subheader("Vista previa de datos")
st.dataframe(df_f.head(50), use_container_width=True)
