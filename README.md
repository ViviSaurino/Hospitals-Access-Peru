# Hospitals-Access-Peru
Geoanálisis de hospitales en Perú con Streamlit.

> **Estado:** versión inicial lista para desplegar en Streamlit Cloud.  
> **Video:** _pendiente_ → el enlace se colocará en `salida/video_link.txt` cuando esté listo.

---

## Demo (app)
- **URL pública de Streamlit:** [_pendiente_.](https://hospitals-access-peru-group-4-course-python.streamlit.app/)  

---

## Objetivo
Crear un panel reproducible en Python/Streamlit que lea datos públicos desde Google Sheets (CSV export), muestre KPIs, una tabla filtrable, un gráfico simple y un mapa de puntos (cuando existan columnas de coordenadas).

---

## Requisitos
- Python 3.10+ (recomendado 3.11)
- Cuenta de GitHub y (opcional) cuenta en Streamlit Cloud
- La hoja de Google debe estar con permiso **“Cualquier persona con el enlace: Lector”**

**Paquetes clave**
- `streamlit`, `pandas`, `plotly`, `folium`, `streamlit-folium`
- (Opcional) stack geoespacial: `geopandas`, `shapely`, `pyproj`, `fiona`  
  > Si el build en Streamlit Cloud falla por estas dependencias, puedes quitarlas del `requirements.txt`. La app funciona con **Folium** sin **GeoPandas**.

---

## Estructura del repo

```
├─ streamlit_app.py # aplicación principal
├─ requirements.txt # dependencias
├─ .streamlit/
│ └─ config.toml # tema/estilo de Streamlit
├─ assets/ # imágenes/logos (placeholder)
├─ src/ # utilidades/código auxiliar (placeholder)
├─ codigo/
│ └─ .keep # carpeta solicitada por la consigna
├─ salida/
│ ├─ video_link.txt # pegar aquí el enlace YouTube (no listado)
│ └─ .keep
├─ LICENSE # MIT
└─ README.md
```
---

## Fuente de datos
La app lee una hoja de Google Sheets pública mediante **CSV export**.

- **Sheet ID:** `10vy5pyNvLUAb2pCJLye7gaOPHOIhjdmzUTKdiUbF5oI`
- **GID (pestaña):** configurable en `streamlit_app.py` (por defecto `"0"`)

**Formato de URL CSV:**

```
https://docs.google.com/spreadsheets/d/<SHEET_ID>/export?format=csv&gid=<GID>
```

**Permisos de la hoja**  
`Compartir → Cualquier persona con el enlace → Lector`.

**Columnas esperadas (para mapa)**
- `lat` / `lon`  (o `latitud` / `longitud`)
- (Opcionales para filtros/agrupación) `departamento` / `región` y `tipo`
- (Opcional para tooltip) `nombre` / `hospital` / `establecimiento`

> Si la pestaña no tiene `lat/lon`, la app funciona igual (KPI, tabla, gráfico), pero el mapa mostrará una advertencia.

---

## Cómo ejecutar localmente
```bash
# 1) crear/activar entorno (opcional)
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 2) instalar dependencias
pip install -r requirements.txt

# 3) ejecutar la app
streamlit run streamlit_app.py
```


