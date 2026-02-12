# Testing Guide

## Setup

### 1. Create and Activate Virtual Environment

**Create venv:**
```bash
python -m venv venv
```

**Activate venv:**

On macOS/Linux:
```bash
source venv/bin/activate
```

On Windows:
```bash
venv\Scripts\activate
```

### 2. Install Test Dependencies

With venv activated, install dependencies:

```bash
pip install -r requirements-dev.txt
```

**Note:** Always activate the venv before running tests or installing packages to avoid polluting your global Python environment.

## Running Tests

Run all tests:

```bash
pytest
```

Run with verbose output:

```bash
pytest -v
```

Run specific test file:

```bash
pytest test_main.py
```

Run specific test:

```bash
pytest test_main.py::TestGetCountyFromPoint::test_point_inside_county
```

## Test Coverage

### Point-to-County Lookup (`/get_county_from_point/`)

- ✅ Point inside US county (returns FIPS code and county name)
- ✅ Point outside US counties (returns null values)
- ✅ Invalid latitude (> 90 or < -90)
- ✅ Invalid longitude (> 180 or < -180)
- ✅ Missing required fields
- ✅ CORS preflight OPTIONS request

### Image Conversion (`/convert_images/`)

- ✅ Single image conversion (JPEG)
- ✅ Multiple images conversion (mixed formats)
- ✅ Too many files (> 10 files returns 400)
- ✅ Invalid file handling (returns null for failed conversions)
- ✅ Image resizing to thumbnail (400x400 max)
- ✅ CORS headers present
- ✅ CORS preflight OPTIONS request

## Test Structure

- `test_main.py`: Unit tests for the API endpoints
- Real shapefile data is used for geo lookups
- Synthetic test images are generated for image conversion tests
- FastAPI's `TestClient` is used for HTTP testing
