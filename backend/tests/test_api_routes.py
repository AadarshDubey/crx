"""
Integration tests for FastAPI API routes.
Uses TestClient with mocked DB and cache dependencies.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a FastAPI TestClient with mocked dependencies."""
    # Patch external connections before importing the app
    with patch("app.database.connection.create_async_engine") as mock_engine, \
         patch("app.services.cache.redis") as mock_redis_module, \
         patch("app.services.scheduler.scraper_scheduler") as mock_scheduler:

        mock_scheduler.start = MagicMock()
        mock_scheduler.stop = MagicMock()
        mock_scheduler.get_job_status = MagicMock(return_value={
            "jobs": [], "running": False
        })

        from app.main import app
        from app.services.cache import cache

        # Mock cache so lifespan doesn't fail
        cache._available = False
        cache.connect = AsyncMock()
        cache.disconnect = AsyncMock()
        cache.health_check = AsyncMock(return_value={
            "status": "disconnected", "error": "mocked"
        })

        with TestClient(app) as c:
            yield c


# ============ Health Endpoints ============

class TestHealthEndpoints:
    def test_root_health_check(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "Crypto Pulse"
        assert "version" in data

    def test_detailed_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "redis" in data
        assert "database" in data


# ============ Scheduler Endpoints ============

class TestSchedulerEndpoints:
    def test_get_scheduler_status(self, client):
        response = client.get("/api/scheduler/status")
        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "running" in data


# ============ CORS ============

class TestCORS:
    def test_cors_headers_present(self, client):
        response = client.options(
            "/",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # CORS should allow the request
        assert response.status_code == 200
