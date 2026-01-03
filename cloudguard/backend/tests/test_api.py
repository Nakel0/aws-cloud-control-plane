"""
API Tests for CloudGuard
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestInfoEndpoint:
    """Test info endpoint"""
    
    def test_get_info(self, client):
        response = client.get("/api/v1/info")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "CloudGuard"
        assert "version" in data


class TestRootEndpoint:
    """Test root endpoint"""
    
    def test_root(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "CloudGuard"
        assert data["docs"] == "/docs"


class TestRegionsEndpoint:
    """Test regions endpoint"""
    
    @patch("app.api.routes.AWSClientManager")
    def test_list_regions(self, mock_aws, client):
        mock_aws.get_all_regions.return_value = ["us-east-1", "us-west-2", "eu-west-1"]
        
        response = client.get("/api/v1/regions")
        assert response.status_code == 200
        data = response.json()
        assert "regions" in data
        assert isinstance(data["regions"], list)


class TestScanEndpoint:
    """Test scan endpoints"""
    
    def test_start_scan(self, client):
        response = client.post(
            "/api/v1/scans",
            json={"regions": ["us-east-1"], "categories": ["cost", "security"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "scan_id" in data
        assert data["status"] in ["pending", "running"]
    
    def test_get_scan_status_not_found(self, client):
        response = client.get("/api/v1/scans/nonexistent-scan-id")
        assert response.status_code == 404


class TestFindingsEndpoint:
    """Test findings endpoint"""
    
    @patch("app.api.routes.CostScanner")
    @patch("app.api.routes.SecurityScanner")
    @patch("app.api.routes.ReliabilityScanner")
    def test_list_findings(self, mock_rel, mock_sec, mock_cost, client):
        # Mock scanners to return empty lists
        mock_cost.return_value.scan_all = MagicMock(return_value=[])
        mock_sec.return_value.scan_all = MagicMock(return_value=[])
        mock_rel.return_value.scan_all = MagicMock(return_value=[])
        
        response = client.get("/api/v1/findings")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "findings" in data


class TestRemediationEndpoint:
    """Test remediation endpoint"""
    
    @patch("app.api.routes.RemediationEngine")
    def test_remediate_dry_run(self, mock_engine, client):
        mock_engine.return_value.remediate = MagicMock(
            return_value=MagicMock(
                action_id="action-test",
                status="pending",
                started_at="2024-01-01T00:00:00",
                completed_at=None,
                result_message="[DRY RUN] Would delete resource",
                rollback_available=False,
            )
        )
        
        response = client.post("/api/v1/remediate/test-finding-id?dry_run=true")
        assert response.status_code == 200
