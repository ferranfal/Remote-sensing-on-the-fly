
# ERA5-Land Daily — remote on-the-fly access (no local download)
# https://earthdatahub.destine.eu/collections/era5/datasets/era5-land-daily
#
# Requirement: set your Personal Access Token as an environment variable:
#   export EDH_PAT=<your_personal_access_token>
#
# Get your token at: https://earthdatahub.destine.eu/account-settings#my-personal-access-tokens

import os
import numpy as np
import xarray as xr

# ----------------------------
# CREDENTIALS
# ----------------------------
# Set the EDH_PAT environment variable before running this script.
# Example: export EDH_PAT=<your_personal_access_token>
PAT = os.environ.get("EDH_PAT", "")
if not PAT:
    raise EnvironmentError("EDH_PAT environment variable is not set. Export your Earth Data Hub Personal Access Token.")

# ----------------------------
# CONFIGURATION
# ----------------------------
bbox       = [-3.85, 40.30, -3.55, 40.55]   # [min_lon, min_lat, max_lon, max_lat]
start_date = "2026-01-01"
end_date   = "2026-03-14"
variables  = ["t2m", "tp"]   # available: d2m pev ro sp ssr ssrd str swvl1 swvl2 t2m tp u10 v10

# ----------------------------
# OPEN REMOTE DATASET (lazy)
# ----------------------------
# Alternative URL using ~/.netrc for authentication:
# ds = xr.open_dataset(
#      "https://data.earthdatahub.destine.eu/era5/reanalysis-era5-land-no-antartica-v0.zarr",
#     storage_options={"client_kwargs": {"trust_env": True}},
#     chunks={},
#     engine="zarr",
#     zarr_format=3,
# )

ds = xr.open_dataset(
    f"https://edh:{PAT}@data.earthdatahub.destine.eu/era5/reanalysis-era5-land-no-antartica-v0.zarr",
    chunks={},
    engine="zarr",
).astype("float32")

t2m = ds['t2m'].sel(valid_time=slice(start_date, end_date))

# Compute daily mean, max and min for t2m
t2m_daily_mean = t2m.resample(valid_time="1D").mean()
t2m_daily_max  = t2m.resample(valid_time="1D").max()
t2m_daily_min  = t2m.resample(valid_time="1D").min()

print(f"Dataset opened. Dimensions: {dict(ds.sizes)}")
print(f"Variables: {list(ds.data_vars)}")

# ----------------------------
# SPATIAL AND TEMPORAL SUBSET
# ----------------------------
min_lon, min_lat, max_lon, max_lat = bbox

# ERA5 uses longitudes 0–360: convert negative values if needed
if min_lon < 0:
    min_lon = min_lon % 360
if max_lon < 0:
    max_lon = max_lon % 360

subset = ds[variables].sel(
    valid_time=slice(start_date, end_date),
    latitude=slice(max_lat, min_lat),   # ERA5: latitudes are descending (N→S)
    longitude=slice(min_lon, max_lon),
)

# Extract individual variables as DataArrays
t2m = subset['t2m']
tp  = subset['tp']

# Create a new DataArray combining t2m and tp
t2m_tp = xr.DataArray({'t2m': t2m, 'tp': tp})

print(t2m)
print(f"Subset dimensions: {dict(subset.sizes)}")

# ----------------------------
# COMPUTE INTO MEMORY
# ----------------------------
subset = subset.compute()

for var in variables:
    arr   = subset[var].values
    units = subset[var].attrs.get("units", "")
    print(f"\n[{var}] {units}")
    print(f"  Shape : {arr.shape}")
    print(f"  Min   : {np.nanmin(arr):.4f}")
    print(f"  Max   : {np.nanmax(arr):.4f}")
    print(f"  Mean  : {np.nanmean(arr):.4f}")
    mean_ts = subset[var].mean(dim=["latitude", "longitude"])
    print(f"  Time series (spatial mean):")
    for t, v in zip(mean_ts.valid_time.values, mean_ts.values):
        print(f"    {str(t)[:10]}  {v:.4f} {units}")
