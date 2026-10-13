import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.data_loader import load_people, load_org_units, load_seats, load_prices, load_activity_events
from app.org_tree import OrgTree
from app.metrics import compute_summary, compute_tools, validate_window

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AppState:
    """In-memory data store for the application."""
    people = {}
    org_units = []
    seats = []
    price_list = []
    events = []
    org_tree = None

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager: Loads CSVs into memory once at startup."""
    try:
        state.people = load_people()
        state.org_units = load_org_units()
        state.seats = load_seats()
        state.price_list = load_prices()
        state.events = load_activity_events()
        
        # Precompute the OrgTree 
        state.org_tree = OrgTree(state.org_units)

        logger.info(f"Startup complete. Loaded {len(state.people)} people.")
        logger.info(f"Loaded {len(state.org_units)} org units.")
        logger.info(f"Loaded {len(state.seats)} seats.")
        logger.info(f"Loaded {len(state.price_list)} prices.")
        logger.info(f"Loaded {len(state.events)} events.")
    except Exception as e:
        logger.error(f"Failed to load data on startup: {e}")
        raise
        
    yield 

app = FastAPI(lifespan=lifespan)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return JSON instead of generic text tracebacks."""
    # Pass through standard HTTP errors and validation errors correctly
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    if isinstance(exc, RequestValidationError):
        return JSONResponse(status_code=422, content={"detail": str(exc)})
        
    logger.error(f"Unhandled internal error: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})

def _validate_request(from_: str, to: str, org: Optional[str]):
    """Shared validation logic for metrics endpoints."""
    try:
        start_date, end_date = validate_window(from_, to)
    except ValueError as e:
        # Map date parsing/logical errors to 400 Bad Request
        raise HTTPException(status_code=400, detail=str(e))
        
    if org is not None and not state.org_tree.org_exists(org):
        # Explicit 404 for unknown org ID
        raise HTTPException(status_code=404, detail=f"Org unit '{org}' not found.")
        
    return start_date, end_date


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/summary")
def get_summary(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    org: Optional[str] = None
):
    start_date, end_date = _validate_request(from_, to, org)
    
    return compute_summary(
        state.people, 
        state.seats, 
        state.events, 
        state.org_tree, 
        state.price_list, 
        start_date, 
        end_date, 
        org
    )


@app.get("/api/tools")
def get_tools(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    org: Optional[str] = None
):
    start_date, end_date = _validate_request(from_, to, org)
    
    return compute_tools(
        state.people, 
        state.seats, 
        state.events, 
        state.org_tree, 
        state.price_list, 
        start_date, 
        end_date, 
        org
    )