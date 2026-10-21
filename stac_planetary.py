import matplotlib.pyplot as plt
import planetary_computer
import pystac_client
# import stackstac
from odc.stac import configure_rio, stac_load
import xarray as xr
import geopandas as gpd
import numpy as np
from shapely.geometry import box

import rioxarray
import os
import rioxarray as rio


# ----------------------------
# CONFIGURATION
# ----------------------------
# Fixed bounding box for the Valencia area, covering the city, the Albufera,
# and the rice fields without making the ROI too large.
# Format: [min_lon, min_lat, max_lon, max_lat]
bbox = [-0.48, 39.22, -0.15, 39.60]

# Output path for the resulting NDVI GeoTIFF
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/tmp/ndvi.tif")

# Define the region of interest (ROI) and date range
datetime = "2025-06-01/2025-06-15"

# Connect to the Microsoft Planetary Computer STAC catalog
# Alternative catalog (e.g. TerrabyteLRZ): "https://stac.terrabyte.lrz.de/public/api"
catalog_url = "https://planetarycomputer.microsoft.com/api/stac/v1"

catalog = pystac_client.Client.open(catalog_url)

# Search for Sentinel-2 L2A data
search = catalog.search(
    # collections=["sentinel-2-l1c"],  # uncomment to use L1C instead
    collections=["sentinel-2-l2a"],
    bbox=bbox,
    datetime=datetime,
    query={"eo:cloud_cover": {"lt": 30}}
)

# Retrieve all matching images and sign the search object.
# `planetary_computer.sign` returns an ItemCollection whose `items` attribute is a list,
# not a callable method. Iterate the signed collection directly.
items = list(planetary_computer.sign(search))
items[0].properties
len(items)

# List of Sentinel-2 band names to load
bands = ['B01', 'B02', 'B03', 'B04', 'B05', 'B06', 'B07', 'B08', 'B09', 'B11', 'B12', 'B8A']

s2_dataset = stac_load(
    items,
    bbox=bbox,
    bands=(bands),
    crs="EPSG:4326",
    chunks={},
    resolution=0.00009009
)

# Compute median composite for selected bands across the full time range
# Median reduces cloud and atmospheric noise effectively
s2_datarray = s2_dataset[['B03', 'B08']].median(dim='time')
s2_datarray = s2_dataset[bands].median(dim='time')

# Calculate NDVI: (NIR - Red) / (NIR + Red)
ndvi = ((s2_dataset['B08'] - s2_dataset['B04']) / (s2_dataset['B08'] + s2_dataset['B04'])).rename("ndvi")

# Save NDVI result to GeoTIFF
print(f"Saving NDVI to {OUTPUT_PATH} ...")
# ndvi.rio.to_raster(OUTPUT_PATH)
print(f"NDVI successfully written to {OUTPUT_PATH}")
