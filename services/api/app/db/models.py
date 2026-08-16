import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )


class Project(UUIDPrimaryKeyMixin, Base):
    """A tenant. `public_key` is the id embedded in the SDK snippet (data-project="...")."""

    __tablename__ = "projects"

    public_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    goals: Mapped[list["Goal"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    constraints: Mapped[list["MutationConstraint"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Goal(UUIDPrimaryKeyMixin, Base):
    """A conversion event a project wants to optimize for, e.g. MicroTune.goal({name, event})."""

    __tablename__ = "goals"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_goals_project_name"),)

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(255))
    event_name: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="goals")
    experiments: Mapped[list["Experiment"]] = relationship(back_populates="goal")


class ExperimentStatus(str, enum.Enum):
    PROPOSED = "proposed"
    RUNNING = "running"
    PROMOTED = "promoted"
    REVERTED = "reverted"


class Experiment(UUIDPrimaryKeyMixin, Base):
    """A single design variable under test: one selector + one CSS property, with N variants (arms)."""

    __tablename__ = "experiments"

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    goal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("goals.id", ondelete="RESTRICT"), index=True)
    selector: Mapped[str] = mapped_column(String(512))
    css_property: Mapped[str] = mapped_column(String(128))
    control_value: Mapped[str] = mapped_column(String(256))
    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus, values_callable=lambda enum_cls: [member.value for member in enum_cls]),
        default=ExperimentStatus.PROPOSED,
        server_default=ExperimentStatus.PROPOSED.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    project: Mapped[Project] = relationship(back_populates="experiments")
    goal: Mapped[Goal] = relationship(back_populates="experiments")
    # order_by matters: assignment.assign_variant_index() hashes a position in this list,
    # so it must resolve identically on every query. created_at alone can tie (Postgres
    # now() is constant within a transaction), so id breaks ties deterministically.
    variants: Mapped[list["Variant"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan", order_by="Variant.created_at, Variant.id"
    )


class Variant(UUIDPrimaryKeyMixin, Base):
    """One candidate arm for an experiment. impressions/conversions are rollups fed by the optimizer
    from raw ClickHouse events (see ARCHITECTURE.md) — Postgres never stores per-visitor event rows."""

    __tablename__ = "variants"
    __table_args__ = (UniqueConstraint("experiment_id", "value", name="uq_variants_experiment_value"),)

    experiment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("experiments.id", ondelete="CASCADE"), index=True)
    value: Mapped[str] = mapped_column(String(256))
    is_control: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    impressions: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    conversions: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    experiment: Mapped[Experiment] = relationship(back_populates="variants")


class MutationConstraint(UUIDPrimaryKeyMixin, Base):
    """Safe-mutation rule for a (selector, property) pair. `rules` holds the shape-specific bounds
    (e.g. {"min": 40, "max": 60} for fontSize, {"allowed": ["left", "center"]} for alignment)."""

    __tablename__ = "mutation_constraints"
    __table_args__ = (UniqueConstraint("project_id", "selector", "css_property", name="uq_constraints_project_selector_property"),)

    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    selector: Mapped[str] = mapped_column(String(512))
    css_property: Mapped[str] = mapped_column(String(128))
    rules: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    locked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped[Project] = relationship(back_populates="constraints")
