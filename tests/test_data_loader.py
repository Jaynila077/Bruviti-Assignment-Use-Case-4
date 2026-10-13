import pytest
from datetime import date
import os
import tempfile
import csv
from app.data_loader import load_seats, load_people

def test_missing_required_fields():
    with tempfile.TemporaryDirectory() as td:
        file_path = os.path.join(td, "seats.csv")
        with open(file_path, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "tool", "tier", "granted_on", "revoked_on"])
            # Missing granted_on
            writer.writerow(["u1", "tool_a", "pro", "", ""])
            
        with pytest.raises(ValueError, match="missing required 'user_id', 'tool', or 'granted_on'"):
            load_seats(td)

def test_load_handles_blank_revoked_on():
    with tempfile.TemporaryDirectory() as td:
        file_path = os.path.join(td, "seats.csv")
        with open(file_path, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "tool", "tier", "granted_on", "revoked_on"])
            writer.writerow(["u1", "tool_a", "pro", "2026-03-01", ""])
            
        seats = load_seats(td)
        assert len(seats) == 1
        assert seats[0].granted_on == date(2026, 3, 1)
        assert seats[0].revoked_on is None

def test_load_people_dict_keyed_by_id():
    with tempfile.TemporaryDirectory() as td:
        file_path = os.path.join(td, "people.csv")
        with open(file_path, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "name", "org_unit_id", "role", "location"])
            writer.writerow(["u1", "Alice", "org_1", "Dev", "Pune"])
            
        people = load_people(td)
        assert "u1" in people
        assert people["u1"].name == "Alice"