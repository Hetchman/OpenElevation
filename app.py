import json
import os
from datetime import datetime

import pandas as pd
import requests
import streamlit as st


API_DEFAULT = "https://api.open-elevation.com/api/v1/lookup"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


def normalize_columns(cols):
    return {c: c.strip().lower() for c in cols}


def detect_coord_columns(df):
    cols = normalize_columns(df.columns)
    rev = {v: k for k, v in cols.items()}

    lat_keys = ["latitude", "lat", "y", "northing", "northings"]
    lon_keys = ["longitude", "lon", "long", "x", "easting", "eastings"]

    lat_col = next((rev[k] for k in lat_keys if k in rev), None)
    lon_col = next((rev[k] for k in lon_keys if k in rev), None)

    if lat_col and lon_col:
        return lat_col, lon_col, "direct"

    x_col = next((rev[k] for k in ["x"] if k in rev), None)
    y_col = next((rev[k] for k in ["y"] if k in rev), None)
    if x_col and y_col:
        return y_col, x_col, "xy"

    e_col = next((rev[k] for k in ["easting", "eastings"] if k in rev), None)
    n_col = next((rev[k] for k in ["northing", "northings"] if k in rev), None)
    if e_col and n_col:
        return n_col, e_col, "en"

    return None, None, None


def load_geojson_points(file_obj):
    geo = json.load(file_obj)
    features = geo.get("features", [])
    coords = []
    for f in features:
        geom = f.get("geometry", {})
        if geom.get("type") != "Point":
            continue
        lon, lat = geom.get("coordinates", [None, None])
        if lon is None or lat is None:
            continue
        coords.append({"latitude": lat, "longitude": lon})
    return coords


def call_open_elevation(api_url, locations, chunk_size=100):
    results = []
    for i in range(0, len(locations), chunk_size):
        chunk = locations[i : i + chunk_size]
        payload = {"locations": chunk}
        r = requests.post(api_url, json=payload, timeout=60)
        r.raise_for_status()
        data = r.json()
        results.extend(data.get("results", []))
    return results


def results_to_geojson(results):
    features = []
    for r in results:
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "longitude": r["longitude"],
                    "latitude": r["latitude"],
                    "elevation": r["elevation"],
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [r["longitude"], r["latitude"]],
                },
            }
        )
    return {"type": "FeatureCollection", "name": "open_elevation", "features": features}


def results_to_dataframe(results):
    return pd.DataFrame(results)[["longitude", "latitude", "elevation"]]


def save_outputs(df, geojson_obj):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = os.path.join(OUTPUT_DIR, f"open_elevation_{ts}.csv")
    geojson_path = os.path.join(OUTPUT_DIR, f"open_elevation_{ts}.geojson")
    df.to_csv(csv_path, index=False)
    with open(geojson_path, "w", encoding="utf-8") as f:
        json.dump(geojson_obj, f, ensure_ascii=False)
    return csv_path, geojson_path


st.set_page_config(page_title="OpenElevation", layout="wide")
st.title("OpenElevation")
st.write(
    "Upload a GeoJSON or CSV to fetch elevation data from the Open‑Elevation public API "
    "using the POST endpoint."
)

api_url = st.text_input("API URL", API_DEFAULT)

col1, col2 = st.columns(2)
with col1:
    geojson_file = st.file_uploader("GeoJSON file", type=["geojson", "json"])
with col2:
    csv_file = st.file_uploader("CSV file", type=["csv"])

coords = []
source = None

if geojson_file is not None:
    coords = load_geojson_points(geojson_file)
    source = "geojson"

if csv_file is not None:
    df_in = pd.read_csv(csv_file)
    lat_col, lon_col, mode = detect_coord_columns(df_in)
    if not lat_col or not lon_col:
        st.error(
            "Could not detect coordinate columns. Expected: "
            "lat/latitude + lon/longitude (or long), or x/y, or easting/northing."
        )
    else:
        coords = [
            {"latitude": float(row[lat_col]), "longitude": float(row[lon_col])}
            for _, row in df_in.iterrows()
        ]
        source = f"csv ({mode})"

if coords:
    st.success(f"Loaded {len(coords)} points from {source}.")
    if st.button("Fetch elevations"):
        with st.spinner("Calling Open‑Elevation API..."):
            results = call_open_elevation(api_url, coords)
        df_out = results_to_dataframe(results)
        geojson_out = results_to_geojson(results)

        st.subheader("Preview")
        st.dataframe(df_out, use_container_width=True)

        st.subheader("Download")
        st.download_button(
            "Download CSV",
            data=df_out.to_csv(index=False),
            file_name="open_elevation.csv",
            mime="text/csv",
        )
        st.download_button(
            "Download GeoJSON",
            data=json.dumps(geojson_out),
            file_name="open_elevation.geojson",
            mime="application/geo+json",
        )

        if st.button("Save outputs to disk"):
            csv_path, geojson_path = save_outputs(df_out, geojson_out)
            st.success(f"Saved:\n{csv_path}\n{geojson_path}")
else:
    st.info("Upload a GeoJSON or CSV file to begin.")
