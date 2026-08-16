from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.assignment import assign_variant_index
from app.db.models import Experiment, ExperimentStatus, Project
from app.db.session import get_session
from app.schemas import AssignedVariant, ConfigResponse

router = APIRouter(tags=["config"])


@router.get("/config")
async def get_config(
    project: str, visitor: str, session: AsyncSession = Depends(get_session)
) -> ConfigResponse:
    result = await session.execute(select(Project).where(Project.public_key == project))
    project_row = result.scalar_one_or_none()
    if project_row is None:
        raise HTTPException(status_code=404, detail="unknown project")

    result = await session.execute(
        select(Experiment)
        .where(Experiment.project_id == project_row.id, Experiment.status == ExperimentStatus.RUNNING)
        .options(selectinload(Experiment.variants))
    )
    experiments = result.scalars().all()

    assigned: list[AssignedVariant] = []
    for experiment in experiments:
        if not experiment.variants:
            continue
        chosen = experiment.variants[assign_variant_index(visitor, experiment.id, len(experiment.variants))]
        assigned.append(
            AssignedVariant(
                experiment_id=str(experiment.id),
                selector=experiment.selector,
                variant_id=str(chosen.id),
                patch={experiment.css_property: chosen.value},
            )
        )

    return ConfigResponse(project_id=project, visitor_id=visitor, variants=assigned)
