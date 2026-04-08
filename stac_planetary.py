import matplotlib.pyplot as plt
import planetary_computer
import pystac_client
import stackstac
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
# Set INPUT_RASTER_PATH to the path of your reference raster file.
# This raster is used to define the bounding box (area of interest).
# You can also set it via the INPUT_RASTER_PATH environment variable.
INPUT_RASTER_PATH = os.environ.get(
    "INPUT_RASTER_PATH",
    "/path/to/your/reference_raster.tif"  # <-- update this path or set INPUT_RASTER_PATH env var
)

# Output path for the resulting NDVI GeoTIFF
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "/tmp/ndvi.tif")

# Open the reference raster with rioxarray to derive the bounding box
raster = rio.open_rasterio(INPUT_RASTER_PATH)

# Get the bounding box of the raster
bounds = raster.rio.bounds()

# Convert bounds to a polygon geometry
polygon = box(bounds[0], bounds[1], bounds[2], bounds[3])

# Create a GeoDataFrame with the polygon and reproject to EPSG:4326
gdf = gpd.GeoDataFrame({'geometry': [polygon]}, crs=raster.rio.crs)
gdf = gdf.to_crs('4326')

bounds = gdf.total_bounds

# Define the region of interest (ROI) and date range
bbox = list(bounds[0:])
datetime = "2021-01-01/2021-12-30"

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

# Retrieve all matching images
images = list(search.items())

# Sign all STAC items with a token from Planetary Computer.
# Without signing, loading the actual data will fail due to access restrictions.
items = planetary_computer.sign(search)
items[0].properties
len(items)

items = list(items.items())

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
ndvi.rio.to_raster(OUTPUT_PATH)
print(f"NDVI successfully written to {OUTPUT_PATH}")
