import logging

from fastapi import APIRouter, status

from app.models import TrackedEvent

router = APIRouter(tags=["events"])
logger = logging.getLogger("microtune.events")


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
def ingest_event(event: TrackedEvent) -> dict[str, str]:
    # No Cloudflare Queue / ClickHouse sink wired up yet (see ARCHITECTURE.md)
    # — log for now so the ingestion contract is exercised end-to-end.
    logger.info("event received: %s", event.model_dump(by_alias=True))
    return {"status": "accepted"}
