from __future__ import annotations

from typing import List, Optional

from sqlalchemy import Column, String
from sqlalchemy.dialects.sqlite import JSON
from sqlmodel import Field, SQLModel


class Exercise(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    pattern: str = Field(
        sa_column=Column(
            String,
            doc="Movement pattern classification (e.g. empuje, tiron, etc.).",
        )
    )
    sets: Optional[int] = Field(default=None)
    reps: Optional[str] = Field(default=None)
    rest: Optional[str] = Field(default=None)
    intensity: Optional[str] = Field(default=None)
    minutes: Optional[int] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    contraindications: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )


class Routine(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    objective: str = Field(
        index=True
    )  # p.ej. fuerza, hipertrofia, resistencia, movilidad, salud, mixto
    session_minutes: int = Field(index=True)
    level: str = Field(default="principiante", index=True)
    tags: List[str] = Field(
        default_factory=list,
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )


class RoutineExercise(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    routine_id: int = Field(foreign_key="routine.id", index=True)
    exercise_id: int = Field(foreign_key="exercise.id", index=True)
    section: str = Field(index=True)
    order_index: int = Field(index=True)
