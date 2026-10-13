from datetime import date
from app.seat_calendar import SeatCalendar
from app.data_loader import Seat, Person

def test_seat_held_days_various_windows():
    people = {"u1": Person("u1", "A", "O1", "", "")}
    seats = [
        # Seat 1: Granted 2026-03-01, no revoke
        Seat("u1", "tool_a", "pro", date(2026, 3, 1), None),
        # Seat 2: Granted 2026-07-21, no revoke
        Seat("u1", "tool_b", "pro", date(2026, 7, 21), None),
        # Seat 3: Revoked 2026-07-16
        Seat("u1", "tool_c", "pro", date(2026, 6, 1), date(2026, 7, 16)),
        # Seat 4: Outside window
        Seat("u1", "tool_d", "pro", date(2026, 8, 1), None),
    ]
    
    calendar = SeatCalendar(seats, people)
    win_start = date(2026, 7, 1)
    win_end = date(2026, 7, 30)

    # 1: Covers entire July window -> 30 days
    assert calendar.held_days_in_window("u1", "tool_a", win_start, win_end) == 30
    
    # 2: Granted July 21st -> July 21 to 30 inclusive -> 10 days
    assert calendar.held_days_in_window("u1", "tool_b", win_start, win_end) == 10
    
    # 3: Revoked July 16 (last held July 15) -> July 1 to 15 -> 15 days
    assert calendar.held_days_in_window("u1", "tool_c", win_start, win_end) == 15
    
    # 4: Completely outside
    assert calendar.held_days_in_window("u1", "tool_d", win_start, win_end) == 0

def test_overlapping_seat_rows():
    people = {"u1": Person("u1", "A", "O1", "", "")}
    seats = [
        Seat("u1", "tool_a", "pro", date(2026, 7, 1), date(2026, 7, 15)), # Held 1st-14th (14 days)
        Seat("u1", "tool_a", "std", date(2026, 7, 10), date(2026, 7, 21)), # Held 10th-20th (11 days)
    ]
    
    calendar = SeatCalendar(seats, people)
    # Union should be July 1 through July 20 = 20 days
    assert calendar.held_days_in_window("u1", "tool_a", date(2026, 7, 1), date(2026, 7, 30)) == 20

def test_non_people_filtered_out():
    # Only u1 is a valid employee
    people = {"u1": Person("u1", "A", "O1", "", "")}
    seats = [
        Seat("u1", "tool_a", "pro", date(2026, 7, 1), None),
        Seat("u2", "tool_a", "pro", date(2026, 7, 1), None),
    ]
    
    calendar = SeatCalendar(seats, people)
    assert calendar.held_days_in_window("u1", "tool_a", date(2026, 7, 1), date(2026, 7, 30)) == 30
    assert calendar.held_days_in_window("u2", "tool_a", date(2026, 7, 1), date(2026, 7, 30)) == 0
    assert "u2" not in calendar.licensed_users_in_window({"u1", "u2"}, date(2026, 7, 1), date(2026, 7, 30))