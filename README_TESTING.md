# Testing Guide

## Setup

Install test dependencies:

```bash
pip install -r requirements-dev.txt
```

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

The test suite covers:

- Point inside US county (returns FIPS code and county name)
- Point outside US counties (returns null values)
- Invalid latitude (> 90 or < -90)
- Invalid longitude (> 180 or < -180)
- Missing required fields
- CORS preflight OPTIONS request

## Test Structure

- `test_main.py`: Unit tests for the API endpoints
- Mock data is used to avoid loading the actual shapefile during tests
- FastAPI's `TestClient` is used for HTTP testing
