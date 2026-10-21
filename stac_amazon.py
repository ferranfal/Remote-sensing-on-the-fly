import numpy as np
import pandas as pd
import pystac_client
import xarray as xr
from odc.stac import stac_load


# Small agricultural area near Leoti, Kansas, USA.
# Bounding-box order: [west, south, east, north].
BBOX = [-101.39, 38.46, -101.33, 38.51]

# Search parameters.
DATE_RANGE = "2025-06-01/2025-06-30"
CLOUD_COVER = 20

# Output-grid parameters.
CRS = "EPSG:32614"
RESOLUTION = 10
NODATA = np.nan

# Sentinel-2 L2A assets used by the Triton Amazon loader.
AWS_BANDS = [
    "blue",
    "green",
    "red",
    "rededge1",
    "rededge2",
    "rededge3",
    "nir",
    "nir08",
    "swir16",
    "swir22",
    "aot",
    "wvp",
    "scl",
]

# Open the public Earth Search STAC catalog.
catalog = pystac_client.Client.open(
    "https://earth-search.aws.element84.com/v1"
)

# Search for Sentinel-2 Collection 1 Level-2A acquisitions.
search = catalog.search(
    collections=["sentinel-2-c1-l2a"],
    bbox=BBOX,
    datetime=DATE_RANGE,
    query={
        "eo:cloud_cover": {
            "lte": CLOUD_COVER,
        },
    },
)

# Keep every acquisition and order them chronologically.
items = sorted(
    search.items(),
    key=lambda item: item.datetime,
)

if not items:
    raise ValueError(
        "No Sentinel-2 images were found for the selected criteria."
    )

# Load the raw digital numbers lazily from the remote COGs.
# One temporal entry is preserved for every STAC item.
dataset = stac_load(
    items,
    bands=AWS_BANDS,
    bbox=BBOX,
    crs=CRS,
    resolution=RESOLUTION,
    chunks={},
    groupby="id",
    resampling="nearest",
    nodata=NODATA,
    dtype="float64",
)

# Create one metadata row for every acquisition.
metadata = pd.DataFrame(
    [
        dict(
            item.properties,
            id=item.id,
        )
        for item in items
    ],
    index=dataset.time.to_index(),
)

# Attach the STAC metadata as temporal coordinates.
dataset = dataset.assign_coords(
    metadata.to_xarray()
)

# Select the reflectance bands.
# AOT, WVP and SCL require different processing rules.
reflectance_bands = [
    band
    for band in dataset.data_vars
    if band not in ("aot", "wvp", "scl")
]

# Convert offset-encoded digital numbers to BOA reflectance:
#
# reflectance = DN * 0.0001 - 0.1
#
# DN=0 remains NoData.
reflectance_dn = dataset[reflectance_bands]

reflectance = xr.where(
    (reflectance_dn != 0) & reflectance_dn.notnull(),
    reflectance_dn * 0.0001 - 0.1,
    NODATA,
)

dataset.update(reflectance)

# AOT and WVP use a scale factor of 0.001 without an offset.
auxiliary_bands = [
    band
    for band in ("aot", "wvp")
    if band in dataset
]

auxiliary_dn = dataset[auxiliary_bands]

auxiliary = xr.where(
    (auxiliary_dn != 0) & auxiliary_dn.notnull(),
    auxiliary_dn * 0.001,
    NODATA,
)

dataset.update(auxiliary)

# SCL is categorical and remains unchanged.

# Convert the final dataset to float32.
dataset = dataset.astype("float32")

# Calculate NDVI for every acquisition.
dataset["NDVI"] = (
    (dataset["nir"] - dataset["red"])
    / (dataset["nir"] + dataset["red"])
).clip(min=-1, max=1)

# Read the requested remote COG windows into memory.
# No raster files are saved locally.
ds_s2 = dataset.compute()