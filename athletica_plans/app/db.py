from __future__ import annotations

from pathlib import Path
from typing import Iterable

from sqlalchemy.engine import Connection
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, create_engine, select

from .models import Exercise, Routine, RoutineExercise

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "athletica_plans.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)
    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=ON;")
        # Intento de migración idempotente para añadir 'level' si no existe
        try:
            cols = conn.exec_driver_sql("PRAGMA table_info('routine');").fetchall()
            col_names = {str(c[1]).lower() for c in cols}
            if "level" not in col_names:
                conn.exec_driver_sql("ALTER TABLE routine ADD COLUMN level VARCHAR;")
        except Exception:
            pass
        conn.exec_driver_sql(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS routine_content_fts
            USING fts5(
                routine_id UNINDEXED,
                exercise_id UNINDEXED,
                routine_name,
                exercise_name,
                notes,
                pattern,
                tags
            );
            """
        )


def get_session() -> Session:
    return Session(engine)


def _clear_fts(connection: Connection) -> None:
    try:
        connection.exec_driver_sql("DELETE FROM routine_content_fts;")
    except OperationalError:
        # If the virtual table does not yet exist, create it and retry.
        connection.exec_driver_sql(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS routine_content_fts
            USING fts5(
                routine_id UNINDEXED,
                exercise_id UNINDEXED,
                routine_name,
                exercise_name,
                notes,
                pattern,
                tags
            );
            """
        )
        connection.exec_driver_sql("DELETE FROM routine_content_fts;")


def rebuild_fts(session: Session) -> None:
    connection = session.connection()
    _clear_fts(connection)

    routine_stmt = (
        select(RoutineExercise, Routine, Exercise)
        .join(Routine, RoutineExercise.routine_id == Routine.id)
        .join(Exercise, RoutineExercise.exercise_id == Exercise.id)
        .order_by(RoutineExercise.routine_id, RoutineExercise.order_index)
    )
    rows: Iterable[
        tuple[RoutineExercise, Routine, Exercise]
    ] = session.exec(routine_stmt)

    for link, routine, exercise in rows:
        tags_text = " ".join(routine.tags or [])
        notes = exercise.notes or ""
        connection.exec_driver_sql(
            """
            INSERT INTO routine_content_fts (
                routine_id,
                exercise_id,
                routine_name,
                exercise_name,
                notes,
                pattern,
                tags
            ) VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                routine.id,
                exercise.id,
                routine.name,
                exercise.name,
                notes,
                exercise.pattern,
                tags_text,
            ),
        )
