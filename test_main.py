import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


class TestGetCountyFromPoint:
    """Test suite for /get_county_from_point/ endpoint"""
    
    def test_point_inside_us_county(self):
        """Test point inside a US county returns valid FIPS code"""
        # San Francisco City Hall coordinates (definitely in SF County)
        response = client.post(
            "/get_county_from_point/",
            json={"lat": 37.7749, "lng": -122.4194}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should return a FIPS code for a valid US location
        assert data["fips_code"] is not None
        assert isinstance(data["fips_code"], str)
        assert len(data["fips_code"]) == 5  # FIPS codes are 5 digits
    
    def test_point_outside_counties(self):
        """Test point in Pacific Ocean returns null values"""
        # Coordinates in Pacific Ocean, far from US
        response = client.post(
            "/get_county_from_point/",
            json={"lat": 0.0, "lng": -170.0}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["fips_code"] is None
        assert data["county_name"] is None
    
    def test_invalid_latitude_high(self):
        """Test latitude above 90 returns 422 validation error"""
        response = client.post(
            "/get_county_from_point/",
            json={"lat": 91.0, "lng": -122.0}
        )
        
        assert response.status_code == 422
        assert "detail" in response.json()
    
    def test_invalid_latitude_low(self):
        """Test latitude below -90 returns 422 validation error"""
        response = client.post(
            "/get_county_from_point/",
            json={"lat": -91.0, "lng": -122.0}
        )
        
        assert response.status_code == 422
    
    def test_invalid_longitude_high(self):
        """Test longitude above 180 returns 422 validation error"""
        response = client.post(
            "/get_county_from_point/",
            json={"lat": 37.0, "lng": 181.0}
        )
        
        assert response.status_code == 422
    
    def test_invalid_longitude_low(self):
        """Test longitude below -180 returns 422 validation error"""
        response = client.post(
            "/get_county_from_point/",
            json={"lat": 37.0, "lng": -181.0}
        )
        
        assert response.status_code == 422
    
    def test_missing_latitude(self):
        """Test missing latitude field returns 422 validation error"""
        response = client.post(
            "/get_county_from_point/",
            json={"lng": -122.0}
        )
        
        assert response.status_code == 422
    
    def test_missing_longitude(self):
        """Test missing longitude field returns 422 validation error"""
        response = client.post(
            "/get_county_from_point/",
            json={"lat": 37.0}
        )
        
        assert response.status_code == 422
    
    def test_cors_preflight(self):
        """Test CORS preflight OPTIONS request"""
        response = client.options("/get_county_from_point/")
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
