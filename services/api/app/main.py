from dotenv import load_dotenv
from fastapi import FastAPI

load_dotenv()

from app.routers import config, events, health  # noqa: E402 — routers may read env-dependent settings (e.g. DATABASE_URL) at import time

app = FastAPI(title="MicroTune API")

app.include_router(health.router)
app.include_router(config.router)
app.include_router(events.router)
