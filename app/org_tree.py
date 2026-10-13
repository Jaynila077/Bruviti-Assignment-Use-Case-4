def resolve_subtree(org_units, root_id):
    all_ids = {u["id"] for u in org_units}
    if root_id not in all_ids:
        return set()

    children_map = {}
    for u in org_units:
        pid = u.get("parent_id")
        if pid:
            children_map.setdefault(pid, []).append(u["id"])

    subtree = set()
    queue = [root_id]
    visited = set()

    while queue:
        curr = queue.pop(0)
        if curr in visited:
            raise ValueError("Cycle detected in org tree")
        visited.add(curr)
        subtree.add(curr)
        for child in children_map.get(curr, []):
            queue.append(child)

    return subtree

def users_in_org(org_units, people_dict, org_unit_id=None):
    if not org_unit_id:
        return set(people_dict.keys())
    
    valid_orgs = resolve_subtree(org_units, org_unit_id)
    return {
        uid for uid, person in people_dict.items()
        if person.get("org_unit_id") in valid_orgs
    }