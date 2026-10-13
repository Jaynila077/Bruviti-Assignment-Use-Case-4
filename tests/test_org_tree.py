import pytest
from app.org_tree import OrgTree
from app.data_loader import OrgUnit, Person

@pytest.fixture
def org_data():
    return [
        OrgUnit("L1", "Root", "", "1"),
        OrgUnit("L2_A", "Dept A", "L1", "2"),
        OrgUnit("L2_B", "Dept B", "L1", "2"),
        OrgUnit("L3_A1", "Team A1", "L2_A", "3"),
        OrgUnit("L3_B1", "Team B1", "L2_B", "3"),
    ]

@pytest.fixture
def people_data():
    return {
        "u1": Person("u1", "A", "L1", "", ""),
        "u2": Person("u2", "B", "L3_A1", "", ""),
        "u3": Person("u3", "C", "L2_B", "", ""),
    }

def test_resolve_subtree(org_data):
    tree = OrgTree(org_data)
    # Root covers all
    assert tree.resolve_subtree("L1") == {"L1", "L2_A", "L2_B", "L3_A1", "L3_B1"}
    # Sub branch
    assert tree.resolve_subtree("L2_A") == {"L2_A", "L3_A1"}
    # Leaf returns itself
    assert tree.resolve_subtree("L3_A1") == {"L3_A1"}
    # Missing returns empty
    assert tree.resolve_subtree("MISSING") == set()

def test_cycle_detection(org_data):
    org_data.append(OrgUnit("CYCLE_A", "A", "CYCLE_B", "1"))
    org_data.append(OrgUnit("CYCLE_B", "B", "CYCLE_A", "2"))
    tree = OrgTree(org_data)
    
    with pytest.raises(ValueError, match="Cycle detected"):
        tree.resolve_subtree("CYCLE_A")

def test_users_in_org(org_data, people_data):
    tree = OrgTree(org_data)
    # L1 should have everyone
    assert tree.users_in_org("L1", people_data) == {"u1", "u2", "u3"}
    # L2_A branch should only have u2
    assert tree.users_in_org("L2_A", people_data) == {"u2"}
    # None should return everyone
    assert tree.users_in_org(None, people_data) == {"u1", "u2", "u3"}