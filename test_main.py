import pytest
from fastapi.testclient import TestClient
from PIL import Image
import io
import base64

from main import app

client = TestClient(app)


def create_test_image(format='JPEG', size=(800, 600), color='red'):
    """Helper function to create test images"""
    img = Image.new('RGB', size, color=color)
    buffer = io.BytesIO()
    img.save(buffer, format=format)
    buffer.seek(0)
    return buffer


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


class TestConvertImages:
    """Test suite for /convert_images/ endpoint"""
    
    def test_single_image_conversion(self):
        """Test converting a single JPEG image"""
        test_image = create_test_image(format='JPEG')
        
        response = client.post(
            "/convert_images/",
            files={"files": ("test.jpg", test_image, "image/jpeg")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "images" in data
        assert len(data["images"]) == 1
        assert data["images"][0] is not None
        assert isinstance(data["images"][0], str)
        # Verify it's valid base64
        try:
            base64.b64decode(data["images"][0])
        except Exception:
            pytest.fail("Response is not valid base64")
    
    def test_multiple_images_conversion(self):
        """Test converting multiple images"""
        files = [
            ("files", ("test1.jpg", create_test_image(format='JPEG', color='red'), "image/jpeg")),
            ("files", ("test2.jpg", create_test_image(format='JPEG', color='blue'), "image/jpeg")),
            ("files", ("test3.png", create_test_image(format='PNG', color='green'), "image/png")),
        ]
        
        response = client.post("/convert_images/", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["images"]) == 3
        # All should be successfully converted
        for img in data["images"]:
            assert img is not None
            assert isinstance(img, str)
    
    def test_too_many_files(self):
        """Test that uploading more than MAX_FILES returns 400 error"""
        # Create 11 files (max is 10)
        files = [
            ("files", (f"test{i}.jpg", create_test_image(format='JPEG'), "image/jpeg"))
            for i in range(11)
        ]
        
        response = client.post("/convert_images/", files=files)
        
        assert response.status_code == 400
        assert "Too many files" in response.json()["detail"]
        assert "max 10 per batch" in response.json()["detail"]
    
    def test_invalid_file_returns_null(self):
        """Test that invalid files return null in the results array"""
        # Create a non-image file
        invalid_file = io.BytesIO(b"This is not an image file content")
        
        files = [
            ("files", ("valid.jpg", create_test_image(format='JPEG'), "image/jpeg")),
            ("files", ("invalid.txt", invalid_file, "text/plain")),
        ]
        
        response = client.post("/convert_images/", files=files)
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["images"]) == 2
        assert data["images"][0] is not None  # Valid image
        assert data["images"][1] is None  # Invalid file
    
    def test_image_resized_to_thumbnail(self):
        """Test that images are resized to thumbnail size"""
        # Create a large image
        large_image = create_test_image(format='JPEG', size=(2000, 1500))
        
        response = client.post(
            "/convert_images/",
            files={"files": ("large.jpg", large_image, "image/jpeg")}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Decode and verify the result is smaller
        result_data = base64.b64decode(data["images"][0])
        result_img = Image.open(io.BytesIO(result_data))
        
        # Should be resized (max 400x400 with aspect ratio maintained)
        assert result_img.width <= 400
        assert result_img.height <= 400
    
    def test_cors_headers(self):
        """Test that CORS headers are present"""
        test_image = create_test_image(format='JPEG')
        
        response = client.post(
            "/convert_images/",
            files={"files": ("test.jpg", test_image, "image/jpeg")}
        )
        
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
    
    def test_cors_preflight(self):
        """Test CORS preflight OPTIONS request"""
        response = client.options("/convert_images/")
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers
