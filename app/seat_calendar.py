from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Set, Tuple, Optional
from app.data_loader import Seat, Person

class SeatCalendar:
    def __init__(self, seats: List[Seat], people: Dict[str, Person]):
        # Store as: dict[(user_id, tool)] -> list[(start_date, end_date)]
        # Where end_date is the last inclusive day the seat is held.
        # If the seat has no revoked_on, end_date is date.max.
        self.held_intervals: Dict[Tuple[str, str], List[Tuple[date, date]]] = defaultdict(list)
        
        raw_intervals = defaultdict(list)
        for seat in seats:
            if seat.user_id not in people:
                continue
                
            # revoked_on is the FIRST day without the seat.
            if seat.revoked_on:
                end_date = seat.revoked_on - timedelta(days=1)
                # If it was revoked on the exact day it was granted or earlier, skip tracking it
                if end_date < seat.granted_on:
                    continue
            else:
                end_date = date.max
                
            raw_intervals[(seat.user_id, seat.tool)].append((seat.granted_on, end_date))
            
        # Merge overlapping/adjacent ranges per (user, tool)
        for key, intervals in raw_intervals.items():
            intervals.sort(key=lambda x: x[0])
            merged = []
            
            for current_start, current_end in intervals:
                if not merged:
                    merged.append((current_start, current_end))
                else:
                    prev_start, prev_end = merged[-1]
                    # If intervals overlap or are perfectly adjacent (next day)
                    if current_start <= (prev_end + timedelta(days=1) if prev_end != date.max else date.max):
                        merged[-1] = (prev_start, max(prev_end, current_end))
                    else:
                        merged.append((current_start, current_end))
                        
            self.held_intervals[key] = merged

    def held_days_in_window(self, user_id: str, tool: str, window_start: date, window_end: date) -> int:
        intervals = self.held_intervals.get((user_id, tool), [])
        total_days = 0
        
        for start, end in intervals:
            intersection_start = max(window_start, start)
            intersection_end = min(window_end, end)
            
            if intersection_start <= intersection_end:
                total_days += (intersection_end - intersection_start).days + 1
                
        return total_days

    def was_held_on(self, user_id: str, tool: str, day: date) -> bool:
        intervals = self.held_intervals.get((user_id, tool), [])
        for start, end in intervals:
            if start <= day <= end:
                return True
        return False

    def tools_held_in_window(self, user_id: str, window_start: date, window_end: date) -> Set[str]:
        held_tools = set()
        for (u_id, tool), intervals in self.held_intervals.items():
            if u_id != user_id:
                continue
            for start, end in intervals:
                if max(window_start, start) <= min(window_end, end):
                    held_tools.add(tool)
                    break
        return held_tools

    def licensed_users_in_window(self, user_ids: Set[str], window_start: date, window_end: date, tool: Optional[str] = None) -> Set[str]:
        licensed = set()
        for u_id in user_ids:
            # Short-circuit check if they hold ANY tool or the SPECIFIC tool
            for (i_user_id, i_tool), intervals in self.held_intervals.items():
                if i_user_id != u_id:
                    continue
                if tool is not None and i_tool != tool:
                    continue
                    
                has_overlap = False
                for start, end in intervals:
                    if max(window_start, start) <= min(window_end, end):
                        has_overlap = True
                        break
                        
                if has_overlap:
                    licensed.add(u_id)
                    break 
        return licensed