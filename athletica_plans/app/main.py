from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import init_db
from .seed import seed
from .routers import health, search

app = FastAPI(title="Athletica Plans")

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app.include_router(health.router, prefix="/api", tags=["system"])
app.include_router(search.router, prefix="/api", tags=["search"])

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    seed()


@app.get("/", response_class=HTMLResponse)
def read_index(request: Request) -> Any:
    return templates.TemplateResponse("index.html", {"request": request})

