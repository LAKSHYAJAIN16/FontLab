from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

# The SDK (packages/sdk) sends/expects camelCase JSON — these models mirror
# packages/sdk/src/types.ts field-for-field via alias_generator=to_camel.
_CAMEL_CASE = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AssignedVariant(BaseModel):
    model_config = _CAMEL_CASE

    experiment_id: str
    selector: str
    variant_id: str
    patch: dict[str, str]


class ConfigResponse(BaseModel):
    model_config = _CAMEL_CASE

    project_id: str
    visitor_id: str
    variants: list[AssignedVariant]


class TrackedEvent(BaseModel):
    model_config = _CAMEL_CASE

    project_id: str
    visitor_id: str
    type: Literal["impression", "goal"]
    experiment_id: str | None = None
    variant_id: str | None = None
    goal_name: str | None = None
    timestamp: int
