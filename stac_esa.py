#%%

# Based on: https://github.com/eu-cdse/notebook-samples/blob/main/geo/stac_ndvi.ipynb
import os
import numpy as np
import xarray as xr

# ===== COPERNICUS DATA SPACE CREDENTIALS =====
# Set these environment variables before running this script:
#   export CDSE_S3_ACCESS_KEY=<your_access_key>
#   export CDSE_S3_SECRET_KEY=<your_secret_key>
#
# Get your S3 credentials at: https://eodata-s3keysmanager.dataspace.copernicus.eu/
_access_key = os.environ.get("CDSE_S3_ACCESS_KEY", "")
_secret_key = os.environ.get("CDSE_S3_SECRET_KEY", "")

if not _access_key or not _secret_key:
    raise EnvironmentError(
        "CDSE_S3_ACCESS_KEY and CDSE_S3_SECRET_KEY environment variables must be set. "
        "Generate your credentials at https://eodata-s3keysmanager.dataspace.copernicus.eu/"
    )

os.environ["CDSE_S3_ACCESS_KEY"] = _access_key
os.environ["CDSE_S3_SECRET_KEY"] = _secret_key

# Configure GDAL/AWS environment
os.environ["GDAL_HTTP_TCP_KEEPALIVE"] = "YES"
os.environ["AWS_S3_ENDPOINT"] = "eodata.dataspace.copernicus.eu"
os.environ["AWS_ACCESS_KEY_ID"] = os.environ["CDSE_S3_ACCESS_KEY"]
os.environ["AWS_SECRET_ACCESS_KEY"] = os.environ["CDSE_S3_SECRET_KEY"]
os.environ["AWS_HTTPS"] = "YES"
os.environ["AWS_VIRTUAL_HOSTING"] = "FALSE"
os.environ["GDAL_HTTP_UNSAFESSL"] = "YES"

import pystac_client
from odc.stac import load as stac_load
import rioxarray as rio
import warnings
warnings.filterwarnings('ignore')


# ----------------------------
# CONFIGURATION
# ----------------------------
bbox = [-3.85, 40.30, -3.55, 40.55]  # [min_lon, min_lat, max_lon, max_lat] - Madrid area (wider)
search_start = "2024-01-01"
time_end = "2024-01-31"
cloud_cover = 20

# Output path for the resulting NDVI GeoTIFF
# Set OUTPUT_PATH environment variable or update the path below
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/tmp/ndvi.tif")

# ===== STAC CONFIGURATION =====
stac_url = "https://stac.dataspace.copernicus.eu/v1"
catalog = pystac_client.Client.open(stac_url)

# Search for Sentinel-2 L2A images
search = catalog.search(
    collections=["sentinel-2-l2a"],
    bbox=bbox,
    datetime=f"{search_start}/{time_end}",
    query={"eo:cloud_cover": {"lt": cloud_cover}},
)

items = list(search.items())
if not items:
    raise ValueError("Images not found in the specified date range or area of interest.")

print(f"Found {len(items)} images with < {cloud_cover}% cloud cover")

# Get band names
band_names = items[0].assets.keys()
print("Available bands in the first item:", list(band_names)[:5], "...")

# Load data using odc.stac (simpler, direct approach)
print("\nLoading Sentinel-2 bands from S3...")
print("This will download data from S3 (may take a few moments)...")

dsx = stac_load(
    items,
    bands=["B04_10m", "B08_10m"],  # Red and NIR bands
    bbox=bbox,
    crs="EPSG:4326",
    resolution=0.0001,  # ~10m resolution
    chunks={"time": 1, "x": 256, "y": 256},
    groupby="solar_day",
    fail_on_error=False,
)

print(f"\nDataset loaded:")
print(f"  Variables: {list(dsx.data_vars)}")
print(f"  Shape: {dsx.sizes}")
print(f"  Coords: {list(dsx.coords)}")

# Extract Red and NIR bands
print("\nProcessing bands...")
red = dsx['B04_10m'] / 10000.0  # Scale to reflectance
nir = dsx['B08_10m'] / 10000.0

print(f"  Red band shape: {red.shape}")
print(f"  NIR band shape: {nir.shape}")

# Calculate NDVI
print("\nCalculating NDVI...")
denominator = nir + red
ndvi = xr.where(denominator > 0, (nir - red) / denominator, np.nan)
ndvi = ndvi.clip(-1, 1)  # NDVI range [-1, 1]

# Take median across time to reduce cloud effects
print("Computing median NDVI across all dates (downloading from S3)...")
ndvi_median = ndvi.median(dim="time", skipna=True)
ndvi_computed = ndvi_median.compute()

print(f"\nNDVI statistics:")
print(f"  Shape: {ndvi_computed.shape}")
print(f"  Min: {float(np.nanmin(ndvi_computed)):.4f}")
print(f"  Max: {float(np.nanmax(ndvi_computed)):.4f}")
print(f"  Mean: {float(np.nanmean(ndvi_computed)):.4f}")

valid_pixels = np.sum(~np.isnan(ndvi_computed))
total_pixels = ndvi_computed.size
print(f"  Valid pixels: {valid_pixels}/{total_pixels} ({100*valid_pixels/total_pixels:.1f}%)")

if valid_pixels < total_pixels * 0.01:
    print("\nWARNING: Less than 1% valid data!")
else:
    print("\nGood data coverage!")

# Write result to GeoTIFF
print(f"\nWriting NDVI to {OUTPUT_PATH} ...")
ndvi_computed.rio.write_crs("EPSG:4326", inplace=True)
ndvi_computed.rio.to_raster(
    OUTPUT_PATH,
    dtype="float32",
    compress="deflate",
)

print(f"NDVI successfully written to {OUTPUT_PATH}")

# %%
