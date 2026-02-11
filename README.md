# OpenElevation (Streamlit)
Simple Streamlit app to fetch elevation data from the Open‑Elevation public API using POST.

## Environment
Your `geo` conda environment already has the needed packages (`streamlit`, `pandas`, `requests`).

## Run
```powershell
conda activate geo
cd C:\Users\hdome\Documents\Projects\GISLearning\open_elevation
streamlit run app.py
```

## Inputs
- **GeoJSON**: `FeatureCollection` of `Point` geometries.
- **CSV**: columns can be:
  - `latitude` + `longitude` (or `lat`/`lon`, `long`)
  - `x` + `y`
  - `easting` + `northing`

## Outputs
- Download CSV and GeoJSON in the UI.
- Optional **Save outputs to disk** button writes files to `open_elevation/outputs`.
