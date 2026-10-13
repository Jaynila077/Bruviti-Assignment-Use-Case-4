from fastapi import FastAPI, HTTPException, Query
from app.data_loader import (
    load_people, load_org_units, load_seats, load_activity_events, load_price_list
)
from app.metrics import validate_window, compute_summary, compute_tools

app = FastAPI()

state = {
    "people": {},
    "org_units": [],
    "seats": [],
    "events": [],
    "price_list": []
}

@app.on_event("startup")
def startup_event():
    data_dir = "data"
    state["people"] = load_people(data_dir)
    state["org_units"] = load_org_units(data_dir)
    state["seats"] = load_seats(data_dir)
    state["events"] = load_activity_events(data_dir)
    state["price_list"] = load_price_list(data_dir)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/api/summary")
def get_summary(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    org: str = None
):
    try:
        start, end = validate_window(from_date, to_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        return compute_summary(
            state["people"], state["seats"], state["events"],
            state["org_units"], state["price_list"],
            start, end, org_unit_id=org
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/tools")
def get_tools(
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    org: str = None
):
    try:
        start, end = validate_window(from_date, to_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        return compute_tools(
            state["people"], state["seats"], state["events"],
            state["org_units"], state["price_list"],
            start, end, org_unit_id=org
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail=str(e))
        raise HTTPException(status_code=400, detail=str(e))