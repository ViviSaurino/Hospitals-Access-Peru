import io
import os
import json
import requests
import pandas as pd

# ---- GeoPandas opcional (no romper en Streamlit Cloud) ----
try:
    import geopandas as gpd
    GEOPANDAS_OK = True
except Exception:
    gpd = None
    GEOPANDAS_OK = False

import streamlit as st
from streamlit_folium import st_folium
import folium
from folium.plugins import MarkerCluster  # lo usabas en Tab 3
import plotly.express as px
import matplotlib.pyplot as plt

# ============================
# Configuración de la app
# ============================
st.set_page_config(page_title="Hospitales del Perú — Geoanálisis", layout="wide")
# Crear tabs
tab1, tab2, tab3 = st.tabs(["Tab 1: Data Description", "Tab 2: Static Maps & Department Analysis", "Tab 3: Dynamic Maps"])

with tab1:
    st.header("Tab 1: Data Description")

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

# ============================
# TAB 2
# ============================
with tab2:
    st.header("Tab 2: Static Maps & Department Analysis")

    # Si las variables requeridas no existen o no hay GeoPandas, evitamos errores
    if not GEOPANDAS_OK or not all(v in globals() for v in ["gdf_dist_cnt", "dep_tbl", "dep_text_col"]):
        st.info("Sección en construcción o GeoPandas no disponible. "
                "Para habilitar estos mapas estáticos, defina gdf_dist_cnt/dep_tbl/dep_text_col "
                "y ejecute en un entorno con GeoPandas.")
    else:
        # -------- Map 1: Total hospitals per district --------
        fig = plt.figure(figsize=(8, 9))
        ax = plt.gca()
        gdf_dist_cnt.plot(column="hospitales", legend=True, ax=ax)
        ax.set_title("Map 1 — Hospitals per District (Total)")
        ax.set_axis_off()
        plt.tight_layout()
        st.pyplot(fig)

        # -------- Map 2: Highlight districts with zero hospitals --------
        gdf_zero = gdf_dist_cnt[gdf_dist_cnt["hospitales"] == 0]
        fig = plt.figure(figsize=(8, 9))
        ax = plt.gca()
        gdf_dist_cnt.plot(ax=ax, alpha=0.12)   # base layer faint
        gdf_zero.plot(ax=ax, linewidth=1.0)    # overlay zeros
        ax.set_title("Map 2 — Districts with ZERO Hospitals (highlighted)")
        ax.set_axis_off()
        plt.tight_layout()
        st.pyplot(fig)

        # -------- Map 3: Top 10 districts with highest number of hospitals --------
        top10 = gdf_dist_cnt.sort_values("hospitales", ascending=False).head(10)
        fig = plt.figure(figsize=(8, 9))
        ax = plt.gca()
        gdf_dist_cnt.plot(ax=ax, alpha=0.12)   # base layer faint
        top10.plot(ax=ax, linewidth=1.2)       # overlay top10
        ax.set_title("Map 3 — Top 10 Districts by Number of Hospitals")
        ax.set_axis_off()
        plt.tight_layout()
        st.pyplot(fig)

        # ==============================
        # 9.2 Department bar chart (Top 10)
        # ==============================
        fig = plt.figure(figsize=(7, 6))
        ax = plt.gca()
        (dep_tbl.head(10).sort_values("hospitales", ascending=True)
         .plot(kind="barh", x=dep_text_col, y="hospitales", ax=ax))
        ax.set_title("Hospitals by Department — Top 10 (preview)")
        ax.set_xlabel("Hospitals")
        ax.set_ylabel("Department")
        plt.tight_layout()
        st.pyplot(fig)

# ============================
# TAB 3
# ============================
with tab3:
    st.header("Tab 3: Dynamic Maps")

    # -------------------------
    # 1. Cargar datos
    # -------------------------
    # Hospitales desde Google Sheets
    sheet_id = "1xOkeqlTCWVifWmfcVlvo2geTjDvoTAS8DIvkaCW9u64"
    gid = "287328050"
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
    hospitals_df = pd.read_csv(url)

    # Distritos desde un GeoJSON
    districts_gdf = None
    districts_gjson = None
    geojson_path = "districts.geojson"

    if GEOPANDAS_OK and os.path.exists(geojson_path):
        try:
            districts_gdf = gpd.read_file(geojson_path)
        except Exception as _:
            districts_gdf = None

    if districts_gdf is None:
        # Fallback sin GeoPandas: cargar como JSON (si el archivo existe)
        if os.path.exists(geojson_path):
            with open(geojson_path, "r", encoding="utf-8") as f:
                districts_gjson = json.load(f)
        else:
            st.warning("No se encuentra 'districts.geojson' en el repositorio. "
                       "Sube ese archivo o usa una URL pública para el GeoJSON.")

    # -------------------------
    # 2. Preparar data para choropleth
    # -------------------------
    hospitals_per_district = hospitals_df.groupby("DISTRITO").size().reset_index(name="count")

    # Si tenemos GeoPandas, renombramos columnas como pedías
    if districts_gdf is not None:
        districts = districts_gdf.rename({'NOMBDIST': 'DISTRITO'}, axis=1)
        districts = districts.rename({'NOMBDEP': 'DEPARTAMENTO'}, axis=1)
        districts = districts.merge(hospitals_per_district, on="DISTRITO", how="left")
    else:
        districts = None  # usaremos directamente el GeoJSON en Choropleth

    # -------------------------
    # 3. Crear mapa base
    # -------------------------
    lat_hospital = hospitals_df["LATITUD"].mean()
    long_hospital = hospitals_df["LONGITUD"].mean()

    m = folium.Map(
        location=[lat_hospital, long_hospital],
        tiles="Cartodb Positron",
        zoom_start=10,
        control_scale=True
    )

    # Choropleth
    if districts is not None:
        # Con GeoPandas
        folium.Choropleth(
            geo_data=districts.to_json(),
            data=districts,
            columns=["DISTRITO", "count"],
            key_on="feature.properties.DISTRITO",
            fill_color="YlOrRd",
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name="Número de hospitales por distrito"
        ).add_to(m)
    elif districts_gjson is not None:
        # Sin GeoPandas: usar el GeoJSON directamente y hospitals_per_district
        # Asumimos que el nombre del distrito está en NOMBDIST
        # Creamos un DataFrame con la misma clave que el GeoJSON
        df_choro = hospitals_per_district.rename(columns={"DISTRITO": "NOMBDIST"})
        folium.Choropleth(
            geo_data=districts_gjson,
            data=df_choro,
            columns=["NOMBDIST", "count"],
            key_on="feature.properties.NOMBDIST",
            fill_color="YlOrRd",
            fill_opacity=0.7,
            line_opacity=0.2,
            legend_name="Número de hospitales por distrito"
        ).add_to(m)
    else:
        st.info("Sin capa de distritos: sube 'districts.geojson' al repo para ver el choropleth.")

    # Clúster de hospitales
    marker_cluster = MarkerCluster().add_to(m)
    for _, row in hospitals_df.iterrows():
        if pd.notna(row.get("LATITUD")) and pd.notna(row.get("LONGITUD")):
            folium.Marker(
                location=[row["LATITUD"], row["LONGITUD"]],
                popup=f"Hospital en distrito: {row.get('DISTRITO', 's/d')}"
            ).add_to(marker_cluster)

    # -------------------------
    # 4. Mostrar mapa en Streamlit
    # -------------------------
    st_folium(m, width=1000, height=600)

    # -------------------------
    # TASK 2: Proximidad Lima & Loreto
    # -------------------------
    if GEOPANDAS_OK and (districts is not None):
        # Crear geometría hospitales
        hospitals_gdf = gpd.GeoDataFrame(
            hospitals_df,
            geometry=gpd.points_from_xy(hospitals_df.LONGITUD, hospitals_df.LATITUD),
            crs="EPSG:4326"
        )

        # Reproyectar a métrico
        hospitals_gdf = hospitals_gdf.to_crs(epsg=3857)
        districts = districts.to_crs(epsg=3857)

        # Buffer de 10km y conteo
        districts["buffer_10km"] = districts.buffer(10000)
        hospital_counts = []
        for idx, row in districts.iterrows():
            buffer = row["buffer_10km"]
            count = hospitals_gdf.within(buffer).sum()
            hospital_counts.append(count)
        districts["hospital_density"] = hospital_counts

        # Mapa de proximidad
        m2 = folium.Map(location=[lat_hospital, long_hospital],
                        tiles="Cartodb Positron",
                        zoom_start=5,
                        control_scale=True)

        for dep in ["LIMA", "LORETO"]:
            sub = districts[districts["DEPARTAMENTO"] == dep]
            if not sub.empty:
                # Mayor densidad (verde)
                high = sub.loc[sub["hospital_density"].idxmax()]
                folium.Circle(
                    location=[high.geometry.centroid.y, high.geometry.centroid.x],
                    radius=10000,
                    color="green",
                    fill=True,
                    popup=f"{dep} - Alta densidad: {high['hospital_density']}"
                ).add_to(m2)

                # Menor densidad (rojo)
                low = sub.loc[sub["hospital_density"].idxmin()]
                folium.Circle(
                    location=[low.geometry.centroid.y, low.geometry.centroid.x],
                    radius=10000,
                    color="red",
                    fill=True,
                    popup=f"{dep} - Baja densidad: {low['hospital_density']}"
                ).add_to(m2)

        st.subheader("Task 2: Proximidad Lima & Loreto")
        st_folium(m2, width=1000, height=600)
    else:
        st.subheader("Task 2: Proximidad Lima & Loreto")
        st.info("Esta tarea requiere GeoPandas (buffers y análisis espacial). "
                "En Streamlit Cloud puedes dejarla deshabilitada o precomputar resultados.")
