import csv
from datetime import datetime, date
import os

def load_people(data_dir):
    people = {}
    path = os.path.join(data_dir, "people.csv")
    if not os.path.exists(path):
        return people
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            uid = row["user_id"].strip()
            if uid:
                people[uid] = {
                    "user_id": uid,
                    "name": row.get("name", "").strip(),
                    "org_unit_id": row.get("org_unit_id", "").strip(),
                    "role": row.get("role", "").strip(),
                    "location": row.get("location", "").strip(),
                }
    return people

def load_org_units(data_dir):
    units = []
    path = os.path.join(data_dir, "org_units.csv")
    if not os.path.exists(path):
        return units
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            units.append({
                "id": row["id"].strip(),
                "name": row.get("name", "").strip(),
                "parent_id": row.get("parent_id", "").strip() or None,
                "level": row.get("level", "").strip(),
            })
    return units

def load_seats(data_dir):
    seats = []
    path = os.path.join(data_dir, "seats.csv")
    if not os.path.exists(path):
        return seats
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            uid = row.get("user_id", "").strip()
            tool = row.get("tool", "").strip()
            granted_str = row.get("granted_on", "").strip()
            if not uid or not tool or not granted_str:
                raise ValueError("missing required 'user_id', 'tool', or 'granted_on'")
            
            granted_on = datetime.strptime(granted_str, "%Y-%m-%d").date()
            revoked_str = row.get("revoked_on", "").strip()
            revoked_on = datetime.strptime(revoked_str, "%Y-%m-%d").date() if revoked_str else None
            
            seats.append({
                "user_id": uid,
                "tool": tool,
                "tier": row.get("tier", "").strip(),
                "granted_on": granted_on,
                "revoked_on": revoked_on,
            })
    return seats

def load_activity_events(data_dir):
    events = []
    path = os.path.join(data_dir, "activity_events.csv")
    if not os.path.exists(path):
        return events
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            events.append({
                "user_id": row["user_id"].strip(),
                "tool": row["tool"].strip(),
                "event_type": row.get("event_type", "").strip(),
                "event_ts": datetime.strptime(row["event_ts"].strip(), "%Y-%m-%d %H:%M:%S"),
            })
    return events

def load_price_list(data_dir):
    prices = []
    path = os.path.join(data_dir, "price_list.csv")
    if not os.path.exists(path):
        return prices
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            cost_str = row.get("monthly_cost", "").strip()
            prices.append({
                "tool": row["tool"].strip(),
                "tier": row.get("tier", "").strip(),
                "monthly_cost": float(cost_str) if cost_str else None,
            })
    return prices