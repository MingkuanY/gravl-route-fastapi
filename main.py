from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import geopandas as gpd
from shapely.geometry import LineString
from pydantic import BaseModel
from typing import List

app = FastAPI()

app.add_middleware(
  CORSMiddleware,
  allow_origins=["http://localhost:3000", "https://www.gravl.org", "https://api.gravl.org"],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

counties_gdf = gpd.read_file('./data/us_counties/us_counties.shp').to_crs("EPSG:4326")

class PolylineInput(BaseModel):
  polyline: List[List[float]]
  
class PolylineBatchInput(BaseModel):
  polylines: List[List[List[float]]]
  
@app.get("/")
async def root():
    return {"message": "Welcome to Gravl"}

@app.post("/process_polyline/")
async def process_polyline(data: PolylineInput):
  polyline = data.polyline
  
  # Convert polyline to GeoDataFrame through LineString
  decoded_path = [(lat, lng) for lat, lng in polyline]
  line = LineString(decoded_path)
  polyline_gdf = gpd.GeoDataFrame(geometry=[line], crs="EPSG:4326")

  # Load the counties shapefile
  counties_gdf = gpd.read_file('./data/us_counties/us_counties.shp')
  counties_gdf = counties_gdf.to_crs("EPSG:4326")

  # Spatial join to find intersecting counties
  intersected_counties = gpd.sjoin(counties_gdf, polyline_gdf, how="inner", predicate="intersects")

  # Sort counties by intersection order
  intersected_counties["intersection_order"] = intersected_counties.geometry.apply(lambda county: line.project(county.centroid))
  sorted_counties = intersected_counties.sort_values("intersection_order")

  # Extract the FIPS codes
  fips_codes = sorted_counties["FIPS"].tolist()

  return {"fips_codes": fips_codes}

@app.post("/process_polylines_batch/")
async def process_polylines_batch(data: PolylineBatchInput):
  results = []

  def process_single_polyline(polyline):
    # Convert to (lat, lng)
    decoded_path = [(lat, lng) for lat, lng in polyline]
    line = LineString(decoded_path)
    polyline_gdf = gpd.GeoDataFrame(geometry=[line], crs="EPSG:4326")

    intersected_counties = gpd.sjoin(counties_gdf, polyline_gdf, how="inner", predicate="intersects")

    # Sort by intersection order
    intersected_counties["intersection_order"] = intersected_counties.geometry.apply(
        lambda county: line.project(county.centroid)
    )
    sorted_counties = intersected_counties.sort_values("intersection_order")

    return sorted_counties["FIPS"].tolist()

  for polyline in data.polylines:
      results.append(process_single_polyline(polyline))

  return {"results": results}
