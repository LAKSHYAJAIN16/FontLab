import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.assignment import assign_variant_index
from app.db.models import Experiment, ExperimentStatus, Goal, Project, Variant
from app.db.session import get_session
from app.schemas import TrackedEvent

router = APIRouter(tags=["events"])


async def _get_project(session: AsyncSession, public_key: str) -> Project:
    result = await session.execute(select(Project).where(Project.public_key == public_key))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="unknown project")
    return project


async def _record_impression(session: AsyncSession, project: Project, event: TrackedEvent) -> None:
    if event.variant_id is None:
        return
    try:
        variant_id = uuid.UUID(event.variant_id)
    except ValueError:
        return

    # Scope the update to variants that belong to this project so one tenant's
    # forged variantId can't inflate another tenant's stats.
    await session.execute(
        update(Variant)
        .where(Variant.id == variant_id)
        .where(Variant.experiment_id.in_(select(Experiment.id).where(Experiment.project_id == project.id)))
        .values(impressions=Variant.impressions + 1)
    )


async def _record_goal(session: AsyncSession, project: Project, event: TrackedEvent) -> None:
    if event.goal_name is None:
        return

    result = await session.execute(select(Goal).where(Goal.project_id == project.id, Goal.name == event.goal_name))
    goal = result.scalar_one_or_none()
    if goal is None:
        return

    result = await session.execute(
        select(Experiment)
        .where(Experiment.goal_id == goal.id, Experiment.status == ExperimentStatus.RUNNING)
        .options(selectinload(Experiment.variants))
    )
    experiments = result.scalars().all()

    # No per-visitor assignment is stored, so re-derive the same arm this visitor
    # would have been given at /config time (see app/assignment.py) to attribute
    # the conversion to it.
    for experiment in experiments:
        if not experiment.variants:
            continue
        index = assign_variant_index(event.visitor_id, experiment.id, len(experiment.variants))
        experiment.variants[index].conversions += 1


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_event(event: TrackedEvent, session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    project = await _get_project(session, event.project_id)

    if event.type == "impression":
        await _record_impression(session, project, event)
    elif event.type == "goal":
        await _record_goal(session, project, event)

    await session.commit()
    return {"status": "accepted"}
