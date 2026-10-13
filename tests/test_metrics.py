import pytest
from datetime import date, datetime

from app.data_loader import Person, Seat, ActivityEvent, Price, OrgUnit
from app.org_tree import OrgTree
from app.seat_calendar import SeatCalendar
from app.metrics import compute_summary, compute_tools, validate_window

@pytest.fixture
def people():
    return {
        "P1": Person("P1", "Alice", "org_l1", "Dev", "Loc"),
        "P2": Person("P2", "Bob", "org_l2", "Dev", "Loc")
    }

@pytest.fixture
def org_tree():
    units = [
        OrgUnit("org_l1", "Root", "", "1"),
        OrgUnit("org_l2", "Subtree", "org_l1", "2")
    ]
    return OrgTree(units)

@pytest.fixture
def seats():
    return [
        Seat("P1", "A", "pro", date(2026, 3, 1), None),
        Seat("P1", "C", "pro", date(2026, 7, 21), None),
        Seat("P2", "A", "pro", date(2026, 1, 1), date(2026, 7, 16))
    ]

@pytest.fixture
def events():
    return [
        ActivityEvent("P1", "A", "login", datetime(2026, 7, 15, 10, 0)),
        ActivityEvent("P1", "C", "login", datetime(2026, 8, 5, 10, 0))
    ]

@pytest.fixture
def price_list():
    return [
        Price("A", "pro", 19.0),
        Price("C", "pro", 30.0),
        Price("E", "pro", None) # E is unpriced
    ]

@pytest.fixture
def seat_calendar(seats, people):
    return SeatCalendar(seats, people)

def test_validate_window():
    start, end = validate_window("2026-07-01", "2026-07-30")
    assert start == date(2026, 7, 1)
    assert end == date(2026, 7, 30)

    with pytest.raises(ValueError, match="cannot be after to date"):
        validate_window("2026-07-30", "2026-07-01")
        
    with pytest.raises(ValueError, match="Invalid date format"):
        validate_window("07-01-2026", "2026-07-30")
        
    with pytest.raises(ValueError, match="Invalid date format"):
        validate_window("2026-07-01", "") # Test empty string rejection via strict parsing

def test_summary_worked_example(people, seats, events, org_tree, price_list, seat_calendar):
    summary = compute_summary(people, seats, events, org_tree, price_list, 
                              date(2026, 7, 1), date(2026, 7, 30), seat_calendar=seat_calendar)
    assert summary == {
        "licensed_users": 2,     
        "active_users": 1,       
        "engagement_pct": 50.0,
        "spend": 38.5,           
        "idle_spend": 19.5       
    }

def test_tools_worked_example(people, seats, events, org_tree, price_list, seat_calendar):
    tools_result = compute_tools(people, seats, events, org_tree, price_list, 
                                 date(2026, 7, 1), date(2026, 7, 30), seat_calendar=seat_calendar)
    
    tool_a = next(t for t in tools_result if t["tool"] == "A")
    assert tool_a["licensed_users"] == 2
    assert tool_a["active_users"] == 1
    assert tool_a["spend"] == 28.5       
    assert tool_a["idle_spend"] == 9.5
    assert tool_a["cost_per_active"] == 28.5 

def test_zero_licensed_users_and_empty_scope(people, seats, events, org_tree, price_list, seat_calendar):
    summary = compute_summary(people, seats, events, org_tree, price_list, 
                              date(2022, 1, 1), date(2022, 1, 31), seat_calendar=seat_calendar)
    assert summary == {
        "licensed_users": 0,
        "active_users": 0,
        "engagement_pct": 0.0,
        "spend": 0.0,
        "idle_spend": 0.0
    }

def test_org_filter_narrows_scope(people, seats, events, org_tree, price_list, seat_calendar):
    summary = compute_summary(people, seats, events, org_tree, price_list, 
                              date(2026, 7, 1), date(2026, 7, 30), org_unit_id="org_l2", seat_calendar=seat_calendar)
    assert summary == {
        "licensed_users": 1,     
        "active_users": 0,
        "engagement_pct": 0.0,
        "spend": 9.5,            
        "idle_spend": 9.5
    }

def test_unpriced_tool(people, seats, events, org_tree, price_list):
    # Give someone a seat for the explicitly unpriced tool 'E'
    seats.append(Seat("P1", "E", "pro", date(2026, 7, 1), None))
    sc = SeatCalendar(seats, people)
    
    tools_result = compute_tools(people, seats, events, org_tree, price_list, 
                                 date(2026, 7, 1), date(2026, 7, 30), seat_calendar=sc)
    
    tool_e = next(t for t in tools_result if t["tool"] == "E")
    assert tool_e["licensed_users"] == 1
    assert tool_e["active_users"] == 0
    assert tool_e["engagement_pct"] == 0.0
    assert tool_e["spend"] is None
    assert tool_e["idle_spend"] is None
    assert tool_e["cost_per_active"] is None

def test_overlapping_seats_spend(people, org_tree):
    # Tests that days are distinct-charged (unioned) and accurately day-priced, not row-summed
    overlap_seats = [
        Seat("P1", "A", "pro", date(2026, 1, 1), date(2026, 1, 16)), # Jan 1 to Jan 15 inclusive (15 days)
        Seat("P1", "A", "std", date(2026, 1, 10), date(2026, 1, 21)) # Jan 10 to Jan 20 inclusive (11 days)
    ]
    overlap_prices = [
        Price("A", "pro", 30.0), # 1.0 per day
        Price("A", "std", 15.0)  # 0.5 per day
    ]
    
    sc = SeatCalendar(overlap_seats, people)
    
    summary = compute_summary(people, overlap_seats, [], org_tree, overlap_prices, 
                              date(2026, 1, 1), date(2026, 1, 31), seat_calendar=sc)
    
    assert summary["spend"] == 17.5
    assert summary["idle_spend"] == 17.5