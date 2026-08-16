from fastapi import FastAPI

from app.routers import config, events, health

app = FastAPI(title="MicroTune API")

app.include_router(health.router)
app.include_router(config.router)
app.include_router(events.router)
