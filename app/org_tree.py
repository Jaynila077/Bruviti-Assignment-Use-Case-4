from typing import Dict, List, Set, Optional
from app.data_loader import OrgUnit, Person

class OrgTree:
    def __init__(self, org_units: List[OrgUnit]):
        self.id_to_org: Dict[str, OrgUnit] = {}
        self.parent_to_children: Dict[str, List[str]] = {}
        
        for unit in org_units:
            self.id_to_org[unit.org_unit_id] = unit
            if unit.parent_id not in self.parent_to_children:
                self.parent_to_children[unit.parent_id] = []
            self.parent_to_children[unit.parent_id].append(unit.org_unit_id)

    def org_exists(self, org_unit_id: str) -> bool:
        return org_unit_id in self.id_to_org

    def resolve_subtree(self, org_unit_id: str) -> Set[str]:
        if not self.org_exists(org_unit_id):
            return set()
            
        result = set()
        stack = [org_unit_id]
        
        while stack:
            curr = stack.pop()
            if curr in result:
                raise ValueError(f"Cycle detected in org tree involving org_unit_id: {curr}")
                
            result.add(curr)
            # Add all children of the current node to the stack
            children = self.parent_to_children.get(curr, [])
            stack.extend(children)
            
        return result

    def users_in_org(self, org_unit_id: Optional[str], people: Dict[str, Person]) -> Set[str]:
        if org_unit_id is None:
            return set(people.keys())
            
        subtree_ids = self.resolve_subtree(org_unit_id)
        return {
            uid for uid, person in people.items() 
            if person.org_unit_id in subtree_ids
        }