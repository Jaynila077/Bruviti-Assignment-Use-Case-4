import pytest
from datetime import date, datetime
import os
import tempfile
import csv
import logging
from app.data_loader import load_seats, load_people, load_prices, load_activity_events, load_org_units

def test_skip_bad_rows_and_log(caplog):
    with tempfile.TemporaryDirectory() as td:
        # Create a mix of good and bad data for seats.csv
        file_path = os.path.join(td, "seats.csv")
        with open(file_path, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "tool", "tier", "granted_on", "revoked_on"])
            writer.writerow(["u1", "tool_a", "pro", "2026-03-01", ""])          # Good
            writer.writerow(["u2", "tool_a", "pro", "", ""])                    # Bad: missing granted_on
            writer.writerow(["", "tool_b", "pro", "2026-03-01", ""])            # Bad: missing user_id
            writer.writerow(["u3", "tool_a", "pro", "03-01-2026", ""])          # Bad: wrong date format
            writer.writerow(["u4", "tool_a", "pro", "2026-03-01", "invalid"])   # Bad: bad revoked_on format
            writer.writerow(["u5", "tool_b", "pro", "2026-05-01", ""])          # Good
            
        with caplog.at_level(logging.WARNING):
            seats = load_seats(td)
            
        # Only 2 rows should have successfully loaded
        assert len(seats) == 2
        assert seats[0].user_id == "u1"
        assert seats[1].user_id == "u5"
        
        # Verify warnings were logged for the skipped rows
        assert "skipping row 3" in caplog.text
        assert "skipping row 4" in caplog.text
        assert "skipping row 5" in caplog.text
        assert "skipping row 6" in caplog.text

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

def test_utf8_sig_bom_handling():
    # If a file is saved with BOM (Byte Order Mark), the first key could become '\ufeffuser_id'
    # without utf-8-sig encoding, failing the loader
    with tempfile.TemporaryDirectory() as td:
        file_path = os.path.join(td, "people.csv")
        with open(file_path, "w", encoding="utf-8-sig", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "name", "org_unit_id", "role", "location"])
            writer.writerow(["u1", "Alice", "org_1", "Dev", "Pune"])
            
        people = load_people(td)
        assert "u1" in people

def test_unparseable_and_blank_prices(caplog):
    with tempfile.TemporaryDirectory() as td:
        file_path = os.path.join(td, "price_list.csv")
        with open(file_path, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["tool", "tier", "monthly_price_usd"])
            writer.writerow(["tool_a", "pro", "10.0"])      # Good
            writer.writerow(["tool_b", "pro", ""])          # Good: Blank price stays None
            writer.writerow(["tool_c", "pro", "invalid"])   # Bad: non-numeric price
            
        with caplog.at_level(logging.WARNING):
            prices = load_prices(td)
            
        assert len(prices) == 2
        assert prices[0].monthly_price_usd == 10.0
        assert prices[1].monthly_price_usd is None
        
        assert "skipping row 4" in caplog.text
        assert "non-numeric price" in caplog.text

def test_unparseable_events(caplog):
    with tempfile.TemporaryDirectory() as td:
        file_path = os.path.join(td, "activity_events.csv")
        with open(file_path, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["user_id", "tool", "event_type", "event_ts"])
            writer.writerow(["u1", "tool_a", "login", "2026-07-15 10:00:00"]) # Good
            writer.writerow(["u2", "tool_a", "login", "invalid_timestamp"])   # Bad
            
        with caplog.at_level(logging.WARNING):
            events = load_activity_events(td)
            
        assert len(events) == 1
        assert "skipping row 3" in caplog.text