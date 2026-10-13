from datetime import datetime, date
from app.org_tree import resolve_subtree, users_in_org
from app.seat_calendar import held_days_in_window, licensed_users_in_window

def validate_window(from_date_str, to_date_str):
    try:
        start = datetime.strptime(from_date_str, "%Y-%m-%d").date()
        end = datetime.strptime(to_date_str, "%Y-%m-%d").date()
    except Exception:
        raise ValueError("Invalid date format")

    if start > end:
        raise ValueError("cannot be after to date")
    return start, end

def compute_summary(people, seats, events, org_units, price_list, win_start, win_end, org_unit_id=None):
    if org_unit_id and org_unit_id not in {u["id"] for u in org_units}:
        raise ValueError(f"Org unit {org_unit_id} not found")

    scoped_users = users_in_org(org_units, people, org_unit_id)
    licensed = licensed_users_in_window(seats, people, scoped_users, win_start, win_end)

    active_users = {
        e["user_id"] for e in events
        if e["user_id"] in scoped_users
        and win_start <= e["event_ts"].date() <= win_end
    }

    tool_prices = {p["tool"]: p["monthly_cost"] for p in price_list if p.get("monthly_cost") is not None}
    
    total_spend = 0.0
    idle_spend = 0.0
    days_in_window = (win_end - win_start).days + 1

    used_combinations = {
        (e["user_id"], e["tool"]) for e in events
        if win_start <= e["event_ts"].date() <= win_end
    }

    for s in seats:
        uid = s["user_id"]
        tool = s["tool"]
        if uid not in scoped_users or tool not in tool_prices:
            continue

        days_held = held_days_in_window([s], people, uid, tool, win_start, win_end)
        cost = (days_held / days_in_window) * tool_prices[tool]
        total_spend += cost

        if (uid, tool) not in used_combinations:
            idle_spend += cost

    lic_count = len(licensed)
    act_count = len(active_users)
    engagement_pct = round((act_count / lic_count * 100), 2) if lic_count else 0.0

    return {
        "licensed_users": lic_count,
        "active_users": act_count,
        "engagement_pct": engagement_pct,
        "spend": round(total_spend, 2),
        "idle_spend": round(idle_spend, 2),
    }

def compute_tools(people, seats, events, org_units, price_list, win_start, win_end, org_unit_id=None):
    scoped_users = users_in_org(org_units, people, org_unit_id)
    days_in_window = (win_end - win_start).days + 1
    tool_names = sorted(list({p["tool"] for p in price_list}))

    results = []
    for tool in tool_names:
        price_entry = next((p for p in price_list if p["tool"] == tool), None)
        monthly_cost = price_entry["monthly_cost"] if price_entry else None

        licensed = licensed_users_in_window(seats, people, scoped_users, win_start, win_end, tool=tool)
        active = {
            e["user_id"] for e in events
            if e["user_id"] in scoped_users
            and e["tool"] == tool
            and win_start <= e["event_ts"].date() <= win_end
        }

        lic_count = len(licensed)
        act_count = len(active)
        engagement_pct = round((act_count / lic_count * 100), 2) if lic_count else 0.0

        if monthly_cost is None:
            spend = idle_spend = cost_per_active = None
        else:
            total_spend = 0.0
            idle = 0.0
            for s in seats:
                if s["user_id"] in scoped_users and s["tool"] == tool:
                    days_held = held_days_in_window([s], people, s["user_id"], tool, win_start, win_end)
                    cost = (days_held / days_in_window) * monthly_cost
                    total_spend += cost
                    if s["user_id"] not in active:
                        idle += cost

            spend = round(total_spend, 2)
            idle_spend = round(idle, 2)
            cost_per_active = round(spend / act_count, 2) if act_count else None

        results.append({
            "tool": tool,
            "licensed_users": lic_count,
            "active_users": act_count,
            "engagement_pct": engagement_pct,
            "spend": spend,
            "idle_spend": idle_spend,
            "cost_per_active": cost_per_active,
        })

    return results