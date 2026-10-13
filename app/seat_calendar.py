from datetime import timedelta

def held_days_in_window(seats, people_dict, user_id, tool, win_start, win_end):
    if user_id not in people_dict:
        return 0

    active_dates = set()
    for s in seats:
        if s["user_id"] != user_id or s["tool"] != tool:
            continue

        start = max(s["granted_on"], win_start)
        end = min(s["revoked_on"] - timedelta(days=1), win_end) if s["revoked_on"] else win_end

        curr = start
        while curr <= end:
            active_dates.add(curr)
            curr += timedelta(days=1)

    return len(active_dates)

def licensed_users_in_window(seats, people_dict, scoped_user_ids, win_start, win_end, tool=None):
    licensed = set()
    for s in seats:
        uid = s["user_id"]
        if uid not in people_dict or uid not in scoped_user_ids:
            continue
        if tool and s["tool"] != tool:
            continue

        effective_revoked = s["revoked_on"] - timedelta(days=1) if s["revoked_on"] else win_end
        if s["granted_on"] <= win_end and effective_revoked >= win_start:
            licensed.add(uid)
    return licensed