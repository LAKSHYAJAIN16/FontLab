from fastapi import APIRouter

from app.models import ConfigResponse

router = APIRouter(tags=["config"])


@router.get("/config")
def get_config(project: str, visitor: str) -> ConfigResponse:
    # No experiment store wired up yet (see ARCHITECTURE.md: Neon Postgres +
    # Upstash Redis cache) — a project with no active experiments correctly
    # gets an empty variant list, so the SDK applies no mutations.
    return ConfigResponse(project_id=project, visitor_id=visitor, variants=[])
