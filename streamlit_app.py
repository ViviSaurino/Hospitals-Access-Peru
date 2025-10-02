import io
import requests
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium
import folium
import plotly.express as px

st.set_page_config(page_title="Hospitales del Perú — Geoanálisis", layout="wide")

# --------- Fuente (Google Sheets) ---------
SHEET_ID = "1xOkeqlTCWVifWmfcVlvo2geTjDvoTAS8DIvkaCW9u64"
GID = "287328050"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

@st.cache_data(show_spinner=True)
def load_data(url: str) -> pd.DataFrame:
    r = requests.get(url, timeout=30); r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    # Normaliza nombres de columnas
    df.columns = (df.columns.str.strip().str.lower()
                  .str.normalize('NFKD').str.encode('ascii', 'ignore').str.decode('utf-8')
                  .str.replace(r'[^a-z0-9]+', '_', regex=True).str.strip('_'))
    # Limpieza básica
    for c in df.columns:
        if df[c].dtype == 'object':
            df[c] = df[c].fillna('').astype(str).str.strip()
    return df

st.title("Tarea: Análisis geoespacial de hospitales en el Perú")
st.caption("0) Medio ambiente y reproducibilidad — plantilla funcional con filtros, KPIs, gráfico y mapa.")

# ---------------- Carga de datos ----------------
try:
    df = load_data(CSV_URL)
except Exception as e:
    st.error(f"No pude leer la hoja. Verifica el `gid` o permisos. Detalle: {e}")
    st.stop()

# ---------------- Asignación de columnas (auto + manual) ----------------
# Candidatos por heurística con las columnas ya normalizadas
cand_lat  = [c for c in df.columns if 'lat' in c]
cand_lon  = [c for c in df.columns if ('lon' in c) or ('lng' in c) or ('long' in c)]
cand_dep  = [c for c in ['departamento', 'region', 'región', 'ambito', 'ambito_', 'dep'] if c in df.columns]
cand_tipo = [c for c in ['tipo', 'categoria', 'nivel', 'clasificacion', 'clasificación'] if c in df.columns]
cand_name = [c for c in ['establecimiento', 'hospital', 'nombre', 'name'] if c in df.columns]

st.sidebar.subheader("Asignar columnas (opcional)")
pick_lat  = st.sidebar.selectbox("Latitud", ["(auto)"] + list(df.columns), index=0)
pick_lon  = st.sidebar.selectbox("Longitud", ["(auto)"] + list(df.columns), index=0)
pick_dep  = st.sidebar.selectbox("Departamento/Región", ["(auto)"] + list(df.columns), index=0)
pick_tipo = st.sidebar.selectbox("Tipo/Categoría", ["(auto)"] + list(df.columns), index=0)
pick_name = st.sidebar.selectbox("Nombre del establecimiento", ["(auto)"] + list(df.columns), index=0)

def _auto_or_pick(pick, candidates):
    if pick != "(auto)":
        return pick
    for c in candidates:
        if c in df.columns:
            return c
    return None

lat_col  = _auto_or_pick(pick_lat,  cand_lat)
lon_col  = _auto_or_pick(pick_lon,  cand_lon)
dep_col  = _auto_or_pick(pick_dep,  cand_dep)
tipo_col = _auto_or_pick(pick_tipo, cand_tipo)
name_col = _auto_or_pick(pick_name, cand_name)

# ---------------- Filtros ----------------
st.sidebar.header("Filtros")
dep_sel, tipo_sel, texto = "Todos", "Todos", ""

if dep_col:
    deps = ["Todos"] + sorted(x for x in df[dep_col].dropna().astype(str).unique())
    dep_sel = st.sidebar.selectbox("Departamento/Región (filtro)", deps, index=0)
if tipo_col:
    tipos = ["Todos"] + sorted(x for x in df[tipo_col].dropna().astype(str).unique())
    tipo_sel = st.sidebar.selectbox("Tipo/Categoría (filtro)", tipos, index=0)
if name_col:
    texto = st.sidebar.text_input("Buscar por nombre (contiene)", "")

df_f = df.copy()
if dep_col and dep_sel != "Todos":
    df_f = df_f[df_f[dep_col].astype(str) == dep_sel]
if tipo_col and tipo_sel != "Todos":
    df_f = df_f[df_f[tipo_col].astype(str) == tipo_sel]
if name_col and texto:
    df_f = df_f[df_f[name_col].str.contains(texto, case=False, na=False)]

# ---------------- KPIs ----------------
col_a, col_b, col_c = st.columns(3)
col_a.metric("Total de registros", f"{len(df):,}")
col_b.metric("Registros filtrados", f"{len(df_f):,}")
col_c.metric("Departamentos/Regiones", f"{df[dep_col].nunique():,}" if dep_col else "s/d")
st.divider()

# ---------------- Gráfico (Top 10) ----------------
st.subheader("Distribución (Top 10)")
text_cols = [c for c in df.columns if df[c].dtype == 'object']
group_pick = st.sidebar.selectbox("Columna para el gráfico (Top 10)", ["(auto)"] + text_cols, index=0)
group_col = (dep_col or tipo_col) if group_pick == "(auto)" else group_pick

if group_col:
    top = (df_f[group_col].replace("", "s/d")
           .value_counts().head(10).reset_index())
    top.columns = [group_col, "conteo"]
    fig = px.bar(
        top, x="conteo", y=group_col, orientation="h",
        labels={"conteo": "N° establecimientos", group_col: group_col.capitalize()},
        height=420
    )
    fig.update_layout(yaxis={'categoryorder': 'total ascending'}, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Selecciona una columna de texto para el gráfico en la barra lateral.")
st.divider()

# ---------------- Mapa ----------------
st.subheader("Mapa de establecimientos")
if not lat_col or not lon_col:
    st.warning("Faltan columnas de coordenadas (lat/lon). Usa los selectores de la izquierda o agrega columnas 'lat' y 'lon'.")
else:
    dmv = df_f.copy()
    dmv[lat_col] = pd.to_numeric(dmv[lat_col], errors='coerce')
    dmv[lon_col] = pd.to_numeric(dmv[lon_col], errors='coerce')
    dmv = dmv.dropna(subset=[lat_col, lon_col])

    if dmv.empty:
        st.info("No hay filas con coordenadas válidas tras aplicar filtros.")
    else:
        center = [dmv[lat_col].mean(), dmv[lon_col].mean()]
        m = folium.Map(location=center, zoom_start=5, tiles="cartodbpositron")

        for _, r in dmv.iterrows():
            nombre = (r[name_col] if name_col and pd.notna(r.get(name_col, None)) and str(r[name_col]).strip()
                      else "Establecimiento")
            pop_lines = [f"<b>{nombre}</b>"]
            if dep_col:  pop_lines.append(f"{dep_col.capitalize()}: {r[dep_col]}")
            if tipo_col: pop_lines.append(f"{tipo_col.capitalize()}: {r[tipo_col]}")
            pop_lines.append(f"Lat: {r[lat_col]:.5f} · Lon: {r[lon_col]:.5f}")

            folium.CircleMarker(
                location=[float(r[lat_col]), float(r[lon_col])],
                radius=4, fill=True, weight=1,
                tooltip=nombre,
                popup=folium.Popup("<br>".join(pop_lines), max_width=320)
            ).add_to(m)

        st_folium(m, height=560, use_container_width=True)

st.divider()
st.subheader("Vista previa de datos")
st.dataframe(df_f.head(50), use_container_width=True)
