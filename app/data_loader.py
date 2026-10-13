import csv
import os
from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional

@dataclass
class Person:
    user_id: str
    name: str
    org_unit_id: str
    role: str
    location: str

@dataclass
class OrgUnit:
    org_unit_id: str
    name: str
    parent_id: str
    level: str

@dataclass
class Seat:
    user_id: str
    tool: str
    tier: str
    granted_on: date
    revoked_on: Optional[date]

@dataclass
class Price:
    tool: str
    tier: str
    monthly_price_usd: Optional[float]

@dataclass
class ActivityEvent:
    user_id: str
    tool: str
    event_type: str
    event_ts: datetime

def _parse_date(val: str) -> Optional[date]:
    if not val or not val.strip():
        return None
    return datetime.strptime(val.strip(), "%Y-%m-%d").date()

def _parse_datetime(val: str) -> Optional[datetime]:
    if not val or not val.strip():
        return None
    # Assuming standard ISO/SQL format output from systems
    return datetime.fromisoformat(val.strip().replace('Z', '+00:00'))

def _get_data_dir(data_dir: Optional[str]) -> str:
    if data_dir is not None:
        return data_dir
    return os.environ.get("DATA_DIR", "data/")

def _read_csv(filename: str, data_dir: Optional[str]) -> List[Dict[str, str]]:
    filepath = os.path.join(_get_data_dir(data_dir), filename)
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r', newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)

def load_people(data_dir: Optional[str] = None) -> Dict[str, Person]:
    rows = _read_csv("people.csv", data_dir)
    people = {}
    for row in rows:
        user_id = row.get("user_id", "").strip()
        if not user_id:
            raise ValueError("people.csv row missing required 'user_id'")
        people[user_id] = Person(
            user_id=user_id,
            name=row.get("name", "").strip(),
            org_unit_id=row.get("org_unit_id", "").strip(),
            role=row.get("role", "").strip(),
            location=row.get("location", "").strip()
        )
    return people

def load_org_units(data_dir: Optional[str] = None) -> List[OrgUnit]:
    rows = _read_csv("org_units.csv", data_dir)
    units = []
    for row in rows:
        org_id = row.get("org_unit_id", "").strip()
        if not org_id:
            raise ValueError("org_units.csv row missing required 'org_unit_id'")
        units.append(OrgUnit(
            org_unit_id=org_id,
            name=row.get("name", "").strip(),
            parent_id=row.get("parent_id", "").strip(),
            level=row.get("level", "").strip()
        ))
    return units

def load_seats(data_dir: Optional[str] = None) -> List[Seat]:
    rows = _read_csv("seats.csv", data_dir)
    seats = []
    for row in rows:
        user_id = row.get("user_id", "").strip()
        tool = row.get("tool", "").strip()
        granted_on_raw = row.get("granted_on", "").strip()
        
        if not user_id or not tool or not granted_on_raw:
            raise ValueError("seats.csv row missing required 'user_id', 'tool', or 'granted_on'")
            
        seats.append(Seat(
            user_id=user_id,
            tool=tool,
            tier=row.get("tier", "").strip(),
            granted_on=_parse_date(granted_on_raw),
            revoked_on=_parse_date(row.get("revoked_on", ""))
        ))
    return seats

def load_prices(data_dir: Optional[str] = None) -> List[Price]:
    rows = _read_csv("price_list.csv", data_dir)
    prices = []
    for row in rows:
        tool = row.get("tool", "").strip()
        tier = row.get("tier", "").strip()
        price_raw = row.get("monthly_price_usd", "").strip()
        
        if not tool or not tier:
            raise ValueError("price_list.csv row missing required 'tool' or 'tier'")
            
        monthly_price = float(price_raw) if price_raw else None
        prices.append(Price(
            tool=tool,
            tier=tier,
            monthly_price_usd=monthly_price
        ))
    return prices

def load_activity_events(data_dir: Optional[str] = None) -> List[ActivityEvent]:
    rows = _read_csv("activity_events.csv", data_dir)
    events = []
    for row in rows:
        user_id = row.get("user_id", "").strip()
        tool = row.get("tool", "").strip()
        ts_raw = row.get("event_ts", "").strip()
        
        if not user_id or not tool or not ts_raw:
            raise ValueError("activity_events.csv row missing required 'user_id', 'tool', or 'event_ts'")
            
        events.append(ActivityEvent(
            user_id=user_id,
            tool=tool,
            event_type=row.get("event_type", "").strip(),
            event_ts=_parse_datetime(ts_raw)
        ))
    return events