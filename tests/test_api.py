import pytest
from fastapi.testclient import TestClient

from app.main import app, state
from app.data_loader import Person, OrgUnit, Price
from app.org_tree import OrgTree
from app.seat_calendar import SeatCalendar

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(autouse=True)
def mock_data():
    state.people = {"u1": Person("u1", "Alice", "org_1", "Dev", "Loc")}
    state.org_units = [OrgUnit("org_1", "O1", "", "1")]
    state.org_tree = OrgTree(state.org_units)
    state.seats = []
    
    state.price_list = [
        Price("A", "pro", 10.0),
        Price("B", "pro", 10.0),
        Price("C", "pro", 10.0),
        Price("D", "pro", 10.0),
        Price("E", "pro", 10.0),
    ]
    state.events = []
    state.seat_calendar = SeatCalendar(state.seats, state.people)
    yield

def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'id="filter-form"' in response.text
    assert "O1" in response.text # Checks that the org dropdown was populated

def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_missing_params(client):
    response = client.get("/api/summary?from=2026-07-01")
    assert response.status_code == 422
    
    response = client.get("/api/summary?to=2026-07-01")
    assert response.status_code == 422

def test_malformed_dates(client):
    response = client.get("/api/summary?from=invalid-date&to=2026-07-30")
    assert response.status_code == 400
    
    response = client.get("/api/summary?from=2026-13-40&to=2026-07-30")
    assert response.status_code == 400

def test_from_after_to(client):
    response = client.get("/api/summary?from=2026-07-30&to=2026-07-01")
    assert response.status_code == 400
    assert "cannot be after" in response.json()["detail"].lower()

def test_unknown_org_returns_404(client):
    response = client.get("/api/summary?from=2026-07-01&to=2026-07-30&org=INVALID_ORG")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_valid_summary_request(client):
    response = client.get("/api/summary?from=2026-07-01&to=2026-07-30")
    assert response.status_code == 200
    data = response.json()
    
    expected_keys = {"licensed_users", "active_users", "engagement_pct", "spend", "idle_spend"}
    assert set(data.keys()) == expected_keys
    assert data["licensed_users"] == 0

def test_valid_tools_request_has_5_ordered_elements(client):
    # Overwrite price_list to intentionally omit "E" to test canonical unpriced handling
    state.price_list = [
        Price("A", "pro", 10.0),
        Price("B", "pro", 10.0),
        Price("C", "pro", 10.0),
        Price("D", "pro", 10.0),
    ]
    
    response = client.get("/api/tools?from=2026-07-01&to=2026-07-30")
    assert response.status_code == 200
    data = response.json()
    
    assert isinstance(data, list)
    assert len(data) == 5
    
    tools = [item["tool"] for item in data]
    assert tools == ["A", "B", "C", "D", "E"]
    
    tool_e = next(t for t in data if t["tool"] == "E")
    assert tool_e["spend"] is None
    assert tool_e["idle_spend"] is None
    assert tool_e["cost_per_active"] is None