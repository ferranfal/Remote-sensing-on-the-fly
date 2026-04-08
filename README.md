# 🛰️ satellite-onthefly

Access and process satellite imagery **on the fly** — no full downloads, no local storage. Stream remote datasets directly into memory using STAC catalogs and cloud-optimized formats.

---

## What is this?

This repo contains three Python scripts to work with satellite and climate data **remotely and lazily** — data is only fetched when needed, sliced to your area of interest, and computed in memory.

| Script | Data Source | What it does |
|---|---|---|
| `era5.py` | [Earth Data Hub (EDH)](https://earthdatahub.destine.eu) | Streams ERA5-Land climate reanalysis (temperature, precipitation…) over a bounding box |
| `stac_esa.py` | [Copernicus Data Space (ESA)](https://dataspace.copernicus.eu) | Loads Sentinel-2 L2A imagery via STAC and computes NDVI |
| `stac_planetary.py` | [Microsoft Planetary Computer](https://planetarycomputer.microsoft.com) | Loads Sentinel-2 L2A from Planetary Computer, derives AOI from a reference raster, and computes NDVI |

---

## Requirements

```bash
pip install xarray zarr numpy rioxarray pystac-client odc-stac stackstac geopandas shapely planetary-computer matplotlib
```

> Tested with Python 3.10+

---

## Setup & Credentials

Each script reads credentials from **environment variables**. Never hardcode tokens or keys.

### `era5.py` — Earth Data Hub Personal Access Token

Get your token at: https://earthdatahub.destine.eu/account-settings#my-personal-access-tokens

```bash
export EDH_PAT=your_personal_access_token
```

### `stac_esa.py` — Copernicus Data Space S3 credentials

Generate your S3 keys at: https://eodata-s3keysmanager.dataspace.copernicus.eu/

```bash
export CDSE_S3_ACCESS_KEY=your_access_key
export CDSE_S3_SECRET_KEY=your_secret_key
```

### `stac_planetary.py` — Microsoft Planetary Computer

Planetary Computer uses automatic token signing via the `planetary-computer` package — no manual credentials needed.

---

## Usage

### ERA5-Land climate data

```bash
export EDH_PAT=your_token
python era5.py
```

Edit the configuration block inside the script to change the area of interest, date range, or variables:

```python
bbox       = [-3.85, 40.30, -3.55, 40.55]   # [min_lon, min_lat, max_lon, max_lat]
start_date = "2026-01-01"
end_date   = "2026-03-14"
variables  = ["t2m", "tp"]
```

Available ERA5-Land variables: `d2m`, `pev`, `ro`, `sp`, `ssr`, `ssrd`, `str`, `swvl1`, `swvl2`, `t2m`, `tp`, `u10`, `v10`

---

### Sentinel-2 NDVI via ESA Copernicus

```bash
export CDSE_S3_ACCESS_KEY=your_key
export CDSE_S3_SECRET_KEY=your_secret
export OUTPUT_PATH=/path/to/ndvi.tif   # optional, defaults to /tmp/ndvi.tif
python stac_esa.py
```

---

### Sentinel-2 NDVI via Planetary Computer

```bash
export INPUT_RASTER_PATH=/path/to/reference_raster.tif  # used to derive AOI
export OUTPUT_PATH=/path/to/ndvi.tif                    # optional
python stac_planetary.py
```

The script extracts the bounding box from your reference raster and uses it as the area of interest for the STAC search.

---

## How it works

```
STAC Catalog (ESA / Planetary Computer / EDH)
        │
        ▼
  Search items by bbox + date + cloud cover
        │
        ▼
  Lazy-load COGs or Zarr (only metadata fetched)
        │
        ▼
  Spatial + temporal subset (only AOI pixels downloaded)
        │
        ▼
  Compute in memory → NDVI / stats / export
```

Data is never fully downloaded. Only the pixels within your bounding box and date range are streamed — this makes it fast and storage-efficient even for large archives.

---

## Output

- `era5.py` — prints time series statistics (min, max, mean) per variable to stdout
- `stac_esa.py` — exports a median NDVI GeoTIFF (cloud-reduced composite)
- `stac_planetary.py` — exports a median NDVI GeoTIFF for the full year

---

## License

MIT
