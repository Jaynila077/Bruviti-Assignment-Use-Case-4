from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, Set

from app.data_loader import Person, Seat, ActivityEvent, Price
from app.org_tree import OrgTree
from app.seat_calendar import SeatCalendar

def validate_window(from_str: str, to_str: str) -> Tuple[date, date]:
    """
    Parses strictly YYYY-MM-DD strings and ensures from_date <= to_date.
    Raises ValueError to be caught by the API layer for 4xx responses.
    """
    try:
        start_date = datetime.strptime(from_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(to_str, "%Y-%m-%d").date()
    except ValueError as e:
        raise ValueError(f"Invalid date format, expected YYYY-MM-DD: {e}")
        
    if start_date > end_date:
        raise ValueError("from date cannot be after to date")
        
    return start_date, end_date

def _get_seat_days(seat: Seat, win_start: date, win_end: date) -> int:
    """
    Computes the exact number of held days for a *specific seat row* inside the window.
    """
    start = max(seat.granted_on, win_start)
    
    if seat.revoked_on:
        from datetime import timedelta
        end_seat = seat.revoked_on - timedelta(days=1)
        # Handle case where it was revoked on/before the day it was granted
        if end_seat < seat.granted_on:
            return 0
    else:
        end_seat = date.max
        
    end = min(end_seat, win_end)
    return max(0, (end - start).days + 1)

def _get_qualifying_events(events: List[ActivityEvent], scope: Set[str], 
                           seat_calendar: SeatCalendar, win_start: date, win_end: date) -> Set[Tuple[str, str]]:
    """
    Returns a set of (user_id, tool) pairs that had at least one valid usage 
    event in the window while actively holding a seat for that tool.
    """
    qualifying = set()
    for event in events:
        if event.user_id in scope:
            event_date = event.event_ts.date()
            if win_start <= event_date <= win_end:
                if seat_calendar.was_held_on(event.user_id, event.tool, event_date):
                    qualifying.add((event.user_id, event.tool))
    return qualifying

def compute_summary(people: Dict[str, Person], seats: List[Seat], events: List[ActivityEvent], 
                    org_tree: OrgTree, price_list: List[Price], 
                    window_start: date, window_end: date, org_unit_id: Optional[str] = None) -> dict:
    
    scope = org_tree.users_in_org(org_unit_id, people)
    seat_calendar = SeatCalendar(seats, people)
    
    licensed_users = len(seat_calendar.licensed_users_in_window(scope, window_start, window_end))
    
    qualifying_events = _get_qualifying_events(events, scope, seat_calendar, window_start, window_end)
    active_users = len({u for u, t in qualifying_events})
    
    engagement_pct = round(active_users / licensed_users * 100, 1) if licensed_users > 0 else 0.0
    
    price_map = {(p.tool, p.tier): p.monthly_price_usd for p in price_list if p.monthly_price_usd is not None}
    
    spend = 0.0
    idle_spend = 0.0
    
    for seat in seats:
        if seat.user_id in scope:
            days = _get_seat_days(seat, window_start, window_end)
            if days > 0:
                price = price_map.get((seat.tool, seat.tier))
                if price is not None:
                    seat_cost = days * (price / 30.0)
                    spend += seat_cost
                    # If this (user, tool) pair had 0 qualifying events across the whole window, 
                    # the entire cost of this seat is idle.
                    if (seat.user_id, seat.tool) not in qualifying_events:
                        idle_spend += seat_cost
                        
    return {
        "licensed_users": licensed_users,
        "active_users": active_users,
        "engagement_pct": engagement_pct,
        "spend": round(spend, 2),
        "idle_spend": round(idle_spend, 2)
    }

def compute_tools(people: Dict[str, Person], seats: List[Seat], events: List[ActivityEvent], 
                  org_tree: OrgTree, price_list: List[Price], 
                  window_start: date, window_end: date, org_unit_id: Optional[str] = None) -> List[dict]:
    
    scope = org_tree.users_in_org(org_unit_id, people)
    seat_calendar = SeatCalendar(seats, people)
    
    qualifying_events = _get_qualifying_events(events, scope, seat_calendar, window_start, window_end)
    
    # Discover all tools and order alphabetically (e.g. A through E)
    all_tools = sorted(list(set([s.tool for s in seats] + [p.tool for p in price_list])))
    price_map = {(p.tool, p.tier): p.monthly_price_usd for p in price_list}
    
    results = []
    for tool in all_tools:
        # A tool is priced if at least one tier for this tool has a non-null price in price_list
        is_tool_priced = any(price is not None for (t, tier), price in price_map.items() if t == tool)
        
        tool_licensed_users = len(seat_calendar.licensed_users_in_window(scope, window_start, window_end, tool=tool))
        tool_active_users = len({u for u, t in qualifying_events if t == tool})
        tool_eng_pct = round(tool_active_users / tool_licensed_users * 100, 1) if tool_licensed_users > 0 else 0.0
        
        if not is_tool_priced:
            results.append({
                "tool": tool,
                "licensed_users": tool_licensed_users,
                "active_users": tool_active_users,
                "engagement_pct": tool_eng_pct,
                "spend": None,
                "idle_spend": None,
                "cost_per_active": None
            })
        else:
            tool_spend = 0.0
            tool_idle = 0.0
            
            for seat in seats:
                if seat.tool == tool and seat.user_id in scope:
                    days = _get_seat_days(seat, window_start, window_end)
                    if days > 0:
                        price = price_map.get((seat.tool, seat.tier))
                        if price is not None:
                            seat_cost = days * (price / 30.0)
                            tool_spend += seat_cost
                            if (seat.user_id, seat.tool) not in qualifying_events:
                                tool_idle += seat_cost
            
            cpa = round(tool_spend / tool_active_users, 2) if tool_active_users > 0 else None
            
            results.append({
                "tool": tool,
                "licensed_users": tool_licensed_users,
                "active_users": tool_active_users,
                "engagement_pct": tool_eng_pct,
                "spend": round(tool_spend, 2),
                "idle_spend": round(tool_idle, 2),
                "cost_per_active": cpa
            })
            
    return results