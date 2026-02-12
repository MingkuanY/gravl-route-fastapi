from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import geopandas as gpd
from shapely.geometry import LineString, Point
from pydantic import BaseModel, Field
from typing import List
from PIL import Image
from pillow_heif import register_heif_opener
import io
import base64

register_heif_opener()  # Enable HEIC support in Pillow

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

class PointRequest(BaseModel):
  lat: float = Field(..., ge=-90, le=90, description="Latitude")
  lng: float = Field(..., ge=-180, le=180, description="Longitude")
  
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

@app.post("/get_county_from_point/")
async def get_county_from_point(request: PointRequest):
  """
  Perform point-in-polygon lookup to find the US county FIPS code
  for a single geographic coordinate.
  """
  try:
    point = Point(request.lng, request.lat)
    
    matches = counties_gdf[counties_gdf.geometry.contains(point)]
    
    if len(matches) == 0:
      return {
        "fips_code": None,
        "county_name": None
      }
    
    match = matches.iloc[0]
    fips_code = str(match["FIPS"]).zfill(5)  # Ensure 5 digits
    
    county_name = None
    if "NAME" in match.index:
      county_name = match["NAME"]
    elif "COUNTYNAME" in match.index:
      county_name = match["COUNTYNAME"]
    elif "County_Nam" in match.index:
      county_name = match["County_Nam"]
    
    return {
      "fips_code": fips_code,
      "county_name": county_name
    }
    
  except Exception as e:
    raise HTTPException(
      status_code=500,
      detail=f"Error performing spatial lookup: {str(e)}"
    )

@app.options("/get_county_from_point/")
async def get_county_from_point_options():
  """Handle CORS preflight requests"""
  return JSONResponse(
    content={},
    headers={
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    }
  )

# Image conversion constants
MAX_FILES = 20
MAX_SIZE_MB = 10
THUMBNAIL_SIZE = (400, 400)
JPEG_QUALITY = 60

@app.post("/convert_images/")
async def convert_images(files: List[UploadFile]):
  """
  Convert and resize images to JPEG thumbnails.
  Returns base64-encoded JPEG strings.
  """
  if len(files) > MAX_FILES:
    raise HTTPException(status_code=400, detail=f"Too many files (max {MAX_FILES})")
  
  results = []
  
  for file in files:
    try:
      # Read file content
      content = await file.read()
      
      if len(content) > MAX_SIZE_MB * 1024 * 1024:
        results.append(None)
        continue
      
      # Open image (supports HEIC via pillow-heif)
      img = Image.open(io.BytesIO(content))
      
      # Convert to RGB (HEIC might be in different color space)
      if img.mode != 'RGB':
        img = img.convert('RGB')
      
      # Resize to thumbnail (maintains aspect ratio)
      img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)
      
      # Convert to JPEG in memory
      output = io.BytesIO()
      img.save(output, format='JPEG', quality=JPEG_QUALITY, optimize=True)
      jpeg_data = output.getvalue()
      
      # Encode as base64
      base64_str = base64.b64encode(jpeg_data).decode('utf-8')
      results.append(base64_str)
      
    except Exception as e:
      print(f"Error converting {file.filename}: {e}")
      results.append(None)
  
  return JSONResponse(
    content={"images": results},
    headers={
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    }
  )

@app.options("/convert_images/")
async def convert_images_options():
  """Handle CORS preflight"""
  return JSONResponse(
    content={},
    headers={
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
    }
  )
