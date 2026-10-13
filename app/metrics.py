from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict

from app.data_loader import Person, Seat, ActivityEvent, Price, _parse_date
from app.org_tree import OrgTree
from app.seat_calendar import SeatCalendar

CANONICAL_TOOLS = ["A", "B", "C", "D", "E"]

def validate_window(from_str: str, to_str: str) -> Tuple[date, date]:
    """
    Parses strictly YYYY-MM-DD strings and ensures from_date <= to_date.
    Raises ValueError to be caught by the API layer for 4xx responses.
    """
    try:
        start_date = _parse_date(from_str)
        end_date = _parse_date(to_str)
        if not start_date or not end_date:
            raise ValueError("Dates cannot be empty")
    except ValueError as e:
        raise ValueError(f"Invalid date format, expected YYYY-MM-DD: {e}")
        
    if start_date > end_date:
        raise ValueError("from date cannot be after to date")
        
    return start_date, end_date

def _get_qualifying_events(events: List[ActivityEvent], scope: Set[str], 
                           seat_calendar: SeatCalendar, win_start: date, win_end: date) -> Set[Tuple[str, str]]:
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
                    window_start: date, window_end: date, 
                    org_unit_id: Optional[str] = None,
                    seat_calendar: Optional[SeatCalendar] = None) -> dict:
    
    scope = org_tree.users_in_org(org_unit_id, people)
    if seat_calendar is None:
        seat_calendar = SeatCalendar(seats, people)
    
    licensed_users = len(seat_calendar.licensed_users_in_window(scope, window_start, window_end))
    
    qualifying_events = _get_qualifying_events(events, scope, seat_calendar, window_start, window_end)
    active_users = len({u for u, t in qualifying_events})
    
    engagement_pct = round(active_users / licensed_users * 100, 1) if licensed_users > 0 else 0.0
    
    price_map = {(p.tool, p.tier): p.monthly_price_usd for p in price_list if p.monthly_price_usd is not None}
    
    scope_seats = defaultdict(list)
    for seat in seats:
        if seat.user_id in scope:
            scope_seats[(seat.user_id, seat.tool)].append(seat)

    spend = 0.0
    idle_spend = 0.0
    
    for (u, t), seat_list in scope_seats.items():
        intervals = seat_calendar.held_intervals.get((u, t), [])
        for start_date, end_date in intervals:
            i_start = max(window_start, start_date)
            i_end = min(window_end, end_date)
            
            day = i_start
            while day <= i_end:
                day_price = None
                for seat in seat_list:
                    s_end = (seat.revoked_on - timedelta(days=1)) if seat.revoked_on else date.max
                    if seat.granted_on <= day <= s_end:
                        price = price_map.get((seat.tool, seat.tier))
                        if price is not None:
                            if day_price is None or price > day_price:
                                day_price = price
                
                if day_price is not None:
                    cost = day_price / 30.0
                    spend += cost
                    if (u, t) not in qualifying_events:
                        idle_spend += cost
                
                day += timedelta(days=1)
                        
    return {
        "licensed_users": licensed_users,
        "active_users": active_users,
        "engagement_pct": engagement_pct,
        "spend": round(spend, 2),
        "idle_spend": round(idle_spend, 2)
    }

def compute_tools(people: Dict[str, Person], seats: List[Seat], events: List[ActivityEvent], 
                  org_tree: OrgTree, price_list: List[Price], 
                  window_start: date, window_end: date, 
                  org_unit_id: Optional[str] = None,
                  seat_calendar: Optional[SeatCalendar] = None) -> List[dict]:
    
    scope = org_tree.users_in_org(org_unit_id, people)
    if seat_calendar is None:
        seat_calendar = SeatCalendar(seats, people)
    
    qualifying_events = _get_qualifying_events(events, scope, seat_calendar, window_start, window_end)
    price_map = {(p.tool, p.tier): p.monthly_price_usd for p in price_list}
    
    results = []
    for tool in CANONICAL_TOOLS:
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
            
            tool_users_seats = defaultdict(list)
            for seat in seats:
                if seat.tool == tool and seat.user_id in scope:
                    tool_users_seats[seat.user_id].append(seat)
                    
            for u, seat_list in tool_users_seats.items():
                intervals = seat_calendar.held_intervals.get((u, tool), [])
                for start_date, end_date in intervals:
                    i_start = max(window_start, start_date)
                    i_end = min(window_end, end_date)
                    
                    day = i_start
                    while day <= i_end:
                        day_price = None
                        for seat in seat_list:
                            s_end = (seat.revoked_on - timedelta(days=1)) if seat.revoked_on else date.max
                            if seat.granted_on <= day <= s_end:
                                price = price_map.get((tool, seat.tier))
                                if price is not None:
                                    if day_price is None or price > day_price:
                                        day_price = price
                                        
                        if day_price is not None:
                            cost = day_price / 30.0
                            tool_spend += cost
                            if (u, tool) not in qualifying_events:
                                tool_idle += cost
                                
                        day += timedelta(days=1)
            
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