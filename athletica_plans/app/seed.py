from __future__ import annotations

from typing import Dict, List

from sqlmodel import Session, select

from .db import get_session, rebuild_fts
from .models import Exercise, Routine, RoutineExercise


SECTION_NAMES = ("warmup", "main", "cooldown")

SECTION_TEMPLATES: Dict[str, Dict[str, List[str]]] = {
    "fuerza": {
        "warmup": ["Bike Easy", "Band Pull Apart"],
        "main": [
            "Press militar con barra",
            "Remo con mancuerna",
            "Peso muerto convencional",
            "Goblet squat controlado",
        ],
        "cooldown": ["Respiracion diafragmatica", "Estiramiento posterior suave"],
    },
    "hipertrofia": {
        "warmup": ["Jump Rope Light", "Hip Mobility Flow"],
        "main": [
            "Buenos dias con barra",
            "Press militar con barra",
            "Remo con mancuerna",
            "Sentadilla profunda",
            "Plancha abdominal",
        ],
        "cooldown": ["Respiracion diafragmatica"],
    },
    "resistencia": {
        "warmup": ["Bike Easy"],
        "main": [
            "Jump Rope Light",
            "Snatch tecnica con barra vacia",
            "Band Pull Apart",
            "Plancha abdominal",
        ],
        "cooldown": ["Estiramiento posterior suave"],
    },
    "movilidad": {
        "warmup": ["Hip Mobility Flow"],
        "main": [
            "Band Pull Apart",
            "Plancha abdominal",
            "Estiramiento posterior suave",
        ],
        "cooldown": ["Respiracion diafragmatica"],
    },
    "salud": {
        "warmup": ["Bike Easy", "Hip Mobility Flow"],
        "main": [
            "Goblet squat controlado",
            "Remo con mancuerna",
            "Plancha abdominal",
        ],
        "cooldown": ["Respiracion diafragmatica", "Estiramiento posterior suave"],
    },
}


def seed() -> None:
    with get_session() as session:
        routine_exists = session.exec(select(Routine).limit(1)).first()
        if routine_exists:
            return

        exercises = _create_exercises()
        session.add_all(exercises)
        session.commit()

        exercise_map = _fetch_ids(session, Exercise)

        routines = _create_routines()
        session.add_all(routines)
        session.commit()

        persisted_routines = session.exec(select(Routine)).all()

        routine_links = _create_routine_links(persisted_routines, exercise_map)

        # Deduplicación defensiva por (routine_id, exercise_id, section, order_index)
        seen = set()
        deduped = []
        for link in routine_links:
            key = (link.routine_id, link.exercise_id, link.section, link.order_index)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(link)

        session.add_all(deduped)
        session.commit()

        rebuild_fts(session)


def _fetch_ids(session: Session, model: type) -> Dict[str, int]:
    statement = select(model)
    records = session.exec(statement).all()
    return {record.name: record.id for record in records}


def _create_exercises() -> List[Exercise]:
    return [
        Exercise(
            name="Bike Easy",
            pattern="cardio",
            minutes=10,
            intensity="baja",
            notes="Cardio ligero en bicicleta estatica para elevar la temperatura.",
            contraindications=[],
        ),
        Exercise(
            name="Jump Rope Light",
            pattern="cardio",
            minutes=5,
            intensity="media",
            notes="Saltos suaves con cuerda.",
            contraindications=["rodilla"],
        ),
        Exercise(
            name="Hip Mobility Flow",
            pattern="movilidad",
            minutes=6,
            intensity="baja",
            notes="Secuencia de movilidad de cadera y espalda media.",
            contraindications=[],
        ),
        Exercise(
            name="Band Pull Apart",
            pattern="tiron",
            sets=2,
            reps="15",
            rest="30s",
            intensity="baja",
            notes="Trabajo de activacion escapular con banda ligera.",
            contraindications=[],
        ),
        Exercise(
            name="Press militar con barra",
            pattern="empuje",
            sets=4,
            reps="6-8",
            rest="90s",
            intensity="alta",
            notes="Presionar de pie con enfasis en estabilidad de core.",
            contraindications=["hombro"],
        ),
        Exercise(
            name="Fondos en paralelas",
            pattern="empuje",
            sets=3,
            reps="8-10",
            rest="90s",
            intensity="alta",
            notes="Trabajo de triceps y pecho en paralelas.",
            contraindications=["hombro"],
        ),
        Exercise(
            name="Snatch tecnica con barra vacia",
            pattern="pierna_cadera",
            sets=3,
            reps="5",
            rest="60s",
            intensity="media",
            notes="Secuencia tecnica con barra ligera.",
            contraindications=["hombro"],
        ),
        Exercise(
            name="Peso muerto convencional",
            pattern="pierna_cadera",
            sets=4,
            reps="5",
            rest="120s",
            intensity="alta",
            notes="Mantener la columna neutra durante todo el movimiento.",
            contraindications=["lumbar"],
        ),
        Exercise(
            name="Buenos dias con barra",
            pattern="pierna_cadera",
            sets=3,
            reps="10",
            rest="90s",
            intensity="media",
            notes="Bisagra de cadera con carga moderada.",
            contraindications=["lumbar"],
        ),
        Exercise(
            name="Sentadilla profunda",
            pattern="pierna_rodilla",
            sets=4,
            reps="8",
            rest="90s",
            intensity="alta",
            notes="Profundidad controlada con tecnica estable.",
            contraindications=["rodilla"],
        ),
        Exercise(
            name="Goblet squat controlado",
            pattern="pierna_rodilla",
            sets=3,
            reps="12",
            rest="75s",
            intensity="media",
            notes="Sentadilla con kettlebell manteniendo tronco erguido.",
            contraindications=[],
        ),
        Exercise(
            name="Remo con mancuerna",
            pattern="tiron",
            sets=3,
            reps="10",
            rest="75s",
            intensity="media",
            notes="Apoyo en banco para enfocar en dorsal.",
            contraindications=[],
        ),
        Exercise(
            name="Plancha abdominal",
            pattern="core",
            sets=3,
            reps="40s",
            rest="45s",
            intensity="media",
            notes="Mantener linea recta de pies a cabeza.",
            contraindications=[],
        ),
        Exercise(
            name="Respiracion diafragmatica",
            pattern="movilidad",
            minutes=5,
            intensity="baja",
            notes="Respiracion nasal profunda para bajar pulsaciones.",
            contraindications=[],
        ),
        Exercise(
            name="Estiramiento posterior suave",
            pattern="movilidad",
            minutes=5,
            intensity="baja",
            notes="Estiramientos de cadena posterior sin rebotes.",
            contraindications=[],
        ),
    ]


def _create_routines() -> List[Routine]:
    base: List[Routine] = []
    levels = ["principiante", "medio", "avanzado"]
    simples = [
        ("Fuerza", "fuerza", [40, 50, 60]),
        ("Hipertrofia", "hipertrofia", [40, 45, 60]),
        ("Resistencia", "resistencia", [30, 40, 50]),
        ("Movilidad", "movilidad", [20, 30, 40]),
        ("Salud", "salud", [30, 40, 45]),
    ]
    for title, objective, minutes_options in simples:
        for level, minutes in zip(levels, minutes_options):
            base.append(
                Routine(
                    name=f"{title} {minutes} - {level}",
                    objective=objective,
                    session_minutes=minutes,
                    level=level,
                    tags=[objective],
                )
            )

    combos = [
        ("Fuerza + Hipertrofia", ["fuerza", "hipertrofia"], [50, 60, 70]),
        ("Fuerza + Resistencia", ["fuerza", "resistencia"], [45, 55, 65]),
        ("Hipertrofia + Salud", ["hipertrofia", "salud"], [40, 50, 60]),
    ]
    for title, tags, minutes_options in combos:
        for level, minutes in zip(levels, minutes_options):
            base.append(
                Routine(
                    name=f"{title} {minutes} - {level}",
                    objective="mixto",
                    session_minutes=minutes,
                    level=level,
                    tags=tags,
                )
            )

    mixtos_simples = [
        ("Mixto 45", 45),
        ("Mixto 60", 60),
    ]
    for name, minutes in mixtos_simples:
        base.append(
            Routine(
                name=name,
                objective="mixto",
                session_minutes=minutes,
                level="medio",
                tags=["fuerza", "hipertrofia"],
            )
        )

    return base


def _create_routine_links(
    routines: List[Routine],
    exercise_map: Dict[str, int],
) -> List[RoutineExercise]:
    links: List[RoutineExercise] = []
    for routine in routines:
        if routine.id is None:
            continue
        sections = _sections_for_routine(routine)
        for section in SECTION_NAMES:
            exercises = sections.get(section, [])
            for index, exercise_name in enumerate(exercises, start=1):
                exercise_id = exercise_map.get(exercise_name)
                if exercise_id is None:
                    continue
                links.append(
                    RoutineExercise(
                        routine_id=routine.id,
                        exercise_id=exercise_id,
                        section=section,
                        order_index=index,
                    )
                )
    return links


def _sections_for_routine(routine: Routine) -> Dict[str, List[str]]:
    if routine.objective != "mixto":
        template = SECTION_TEMPLATES.get(routine.objective, SECTION_TEMPLATES["salud"])
        return {
            section: list(template.get(section, []))
            for section in SECTION_NAMES
        }

    combined: Dict[str, List[str]] = {section: [] for section in SECTION_NAMES}
    for tag in routine.tags or []:
        template = SECTION_TEMPLATES.get(tag)
        if not template:
            continue
        for section in SECTION_NAMES:
            for exercise_name in template.get(section, []):
                if exercise_name not in combined[section]:
                    combined[section].append(exercise_name)

    if not combined["warmup"]:
        combined["warmup"] = list(SECTION_TEMPLATES["salud"]["warmup"])
    if not combined["main"]:
        combined["main"] = list(SECTION_TEMPLATES["salud"]["main"])
    if not combined["cooldown"]:
        combined["cooldown"] = list(SECTION_TEMPLATES["salud"]["cooldown"])

    return combined
