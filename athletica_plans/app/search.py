from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
from math import floor
from typing import Any, Dict, Iterable, List, Optional, Tuple

from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from .db import get_session
from .models import Exercise, Routine, RoutineExercise

SectionPayload = Dict[str, Any]

FALLBACK_WARMUP_ITEM: Dict[str, Any] = {
    "exercise_id": None,
    "name": "Cardio suave general",
    "pattern": "cardio",
    "sets": None,
    "reps": None,
    "rest": None,
    "intensity": "baja",
    "minutes": 12,
    "notes": "10-12 minutos de cardio ligero en cinta, bicicleta o remo.",
    "is_fallback": True,
}

FALLBACK_COOLDOWN_ITEM: Dict[str, Any] = {
    "exercise_id": None,
    "name": "Respiracion y estiramientos suaves",
    "pattern": "movilidad",
    "sets": None,
    "reps": None,
    "rest": None,
    "intensity": "baja",
    "minutes": 6,
    "notes": "Respiracion diafragmatica y estiramientos controlados.",
    "is_fallback": True,
}

SECTION_ORDER = ("warmup", "main", "cooldown")


def build_results(
    objectives: List[str],
    session_minutes: Optional[int] = None,
    pathologies: Optional[List[str]] = None,
    level: str = "medio",
    q: Optional[str] = None,
) -> Dict[str, Any]:
    pathologies_set = {p.lower() for p in (pathologies or [])}
    objective_set = {obj for obj in objectives if obj}
    multi_objective = len(objective_set) > 1
    with get_session() as session:
        routines = _load_candidate_routines(session, objectives, session_minutes)
        fts_scores = _load_fts_scores(session, q) if q else {}
        results: List[Dict[str, Any]] = []

        for routine in routines:
            section_payloads = _build_sections_for_routine(
                session=session,
                routine=routine,
                pathologies=pathologies_set,
                level=level,
            )
            results.append(
                {
                    "routine_id": routine.id,
                    "name": routine.name,
                    "objective": routine.objective,
                    "level": level,  # el nivel solicitado por el usuario
                    "minutes_target": routine.session_minutes,
                    "sections": section_payloads,
                    "score": fts_scores.get(routine.id, 0),
                }
            )

        # Orden: FTS desc, proximidad de minutos, nombre asc
        results.sort(
            key=lambda item: (
                -item["score"],
                _minute_difference(session_minutes, item["minutes_target"])
                if session_minutes is not None else 0,
                item["name"],
            )
        )

        if multi_objective and not any(r.get("objective") == "mixto" for r in results):
            composed = _compose_mixed_plan(
                session=session,
                objectives=objectives,
                session_minutes=session_minutes,
                pathologies=pathologies_set,
                level=level,
            )
            if composed:
                results.insert(0, composed)

        for item in results:
            item.pop("score", None)

        return {"ok": True, "results": results}


def _minute_difference(target: Optional[int], actual: int) -> int:
    if target is None:
        return 0
    return abs(actual - target)


def _load_candidate_routines(
    session: Session,
    objectives: List[str],
    session_minutes: Optional[int],
) -> List[Routine]:
    candidate_objs = [obj for obj in objectives if obj]
    if not candidate_objs:
        return []

    candidate_set = set(candidate_objs)
    include_mixto = len(candidate_set) > 1

    base_stmt = select(Routine).where(Routine.objective.in_(candidate_set))
    routines = session.exec(base_stmt).all()

    if include_mixto:
        mixto_stmt = select(Routine).where(Routine.objective == "mixto")
        routines += session.exec(mixto_stmt).all()

    if session_minutes is not None:
        lower, upper = max(0, session_minutes - 5), session_minutes + 5
        in_window = [
            routine
            for routine in routines
            if lower <= routine.session_minutes <= upper
        ]
        if in_window:
            routines = in_window

    if not routines:
        fallback_set = candidate_set | {"mixto"} if include_mixto else candidate_set
        routines = session.exec(
            select(Routine).where(Routine.objective.in_(fallback_set))
        ).all()

    dedup: Dict[int, Routine] = {}
    for routine in routines:
        if routine.id is None:
            continue
        dedup[routine.id] = routine

    return list(dedup.values())


def _compose_mixed_plan(
    session: Session,
    objectives: List[str],
    session_minutes: Optional[int],
    pathologies: Iterable[str],
    level: str,
) -> Optional[Dict[str, Any]]:
    unique_objectives: List[str] = []
    seen = set()
    for obj in objectives:
        if not obj or obj == "mixto" or obj in seen:
            continue
        seen.add(obj)
        unique_objectives.append(obj)

    def best_for(obj: str) -> Optional[Routine]:
        stmt = select(Routine).where(Routine.objective == obj).order_by(Routine.name)
        candidates = session.exec(stmt).all()
        if not candidates:
            return None

        ordered = candidates
        if session_minutes is not None:
            lower, upper = max(0, session_minutes - 5), session_minutes + 5
            window = [
                routine
                for routine in candidates
                if lower <= routine.session_minutes <= upper
            ]
            if window:
                ordered = window
        ordered = sorted(
            ordered,
            key=lambda routine: (
                _minute_difference(session_minutes, routine.session_minutes)
                if session_minutes is not None
                else 0,
                routine.name,
            ),
        )
        return ordered[0]

    picks = [best_for(obj) for obj in unique_objectives]
    picks = [pick for pick in picks if pick is not None]
    if len(picks) < 2:
        return None

    first, second = picks[0], picks[1]
    sections_a = _build_sections_for_routine(session, first, pathologies, level)
    sections_b = _build_sections_for_routine(session, second, pathologies, level)

    warmup_section = deepcopy(sections_a.get("warmup"))
    if warmup_section is None:
        warmup_section = deepcopy(sections_b.get("warmup"))
    if warmup_section is None:
        warmup_section = {
            "minutes": FALLBACK_WARMUP_ITEM["minutes"],
            "items": [deepcopy(FALLBACK_WARMUP_ITEM)],
        }

    cooldown_section = deepcopy(sections_b.get("cooldown"))
    if cooldown_section is None:
        cooldown_section = deepcopy(sections_a.get("cooldown"))
    if cooldown_section is None:
        cooldown_section = {
            "minutes": FALLBACK_COOLDOWN_ITEM["minutes"],
            "items": [deepcopy(FALLBACK_COOLDOWN_ITEM)],
        }

    def take_first_items(section: SectionPayload, amount: int) -> List[Dict[str, Any]]:
        items = (section or {}).get("items") or []
        return deepcopy(items[:amount])

    main_items = take_first_items(sections_a.get("main"), 2)
    main_items += take_first_items(sections_b.get("main"), 2)
    if not main_items:
        fallback_main = sections_a.get("main") or sections_b.get("main")
        main_items = deepcopy((fallback_main or {}).get("items", []))

    main_minutes = _estimate_minutes("main", main_items)

    minutes_target: int
    if session_minutes is not None:
        minutes_target = session_minutes
    else:
        avg_minutes = (first.session_minutes + second.session_minutes) / 2
        minutes_target = int(
            5 * floor((avg_minutes / 5.0) + 0.5)
        )
        if minutes_target == 0:
            minutes_target = max(first.session_minutes, second.session_minutes)

    result_sections = {
        "warmup": warmup_section,
        "main": {"minutes": main_minutes, "items": main_items},
        "cooldown": cooldown_section,
    }

    return {
        "routine_id": None,
        "name": "Mixto (compuesto)",
        "objective": "mixto",
        "level": level,
        "minutes_target": minutes_target,
        "sections": result_sections,
        "score": 999.0,
    }


def _load_fts_scores(session: Session, query: str) -> Dict[int, float]:
    connection = session.connection()
    try:
        rows = connection.exec_driver_sql(
            """
            SELECT routine_id, SUM(1) AS hits
            FROM routine_content_fts
            WHERE routine_content_fts MATCH ?
            GROUP BY routine_id;
            """,
            (query,),
        )
    except OperationalError:
        return {}

    return {int(row[0]): float(row[1]) for row in rows}


def _build_sections_for_routine(
    session: Session,
    routine: Routine,
    pathologies: Iterable[str],
    level: str,
) -> Dict[str, SectionPayload]:
    section_items: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    link_stmt = (
        select(RoutineExercise, Exercise)
        .join(Exercise, RoutineExercise.exercise_id == Exercise.id)
        .where(RoutineExercise.routine_id == routine.id)
        .order_by(RoutineExercise.section, RoutineExercise.order_index)
    )

    rows: Iterable[Tuple[RoutineExercise, Exercise]] = session.exec(link_stmt)

    for link, exercise in rows:
        if _is_exercise_excluded(exercise, pathologies):
            continue
        payload = _exercise_to_payload(exercise)

        # Escalar series por nivel (si hay sets)
        payload["sets"] = _scale_sets_by_level(payload.get("sets"), level)

        section_items[link.section].append(payload)

    # Asegurar secciones presentes
    for section in SECTION_ORDER:
        section_items.setdefault(section, [])

    # Fallbacks de warmup/cooldown
    if not section_items["warmup"]:
        section_items["warmup"].append(FALLBACK_WARMUP_ITEM.copy())
    if not section_items["cooldown"]:
        section_items["cooldown"].append(FALLBACK_COOLDOWN_ITEM.copy())

    sections: Dict[str, SectionPayload] = {}
    for section in SECTION_ORDER:
        items = section_items[section]
        sections[section] = {
            "minutes": _estimate_minutes(section, items),
            "items": items,
        }

    return sections


def _scale_sets_by_level(base_sets: Optional[int], level: str) -> Optional[int]:
    if base_sets is None:
        return None
    bump = 0
    if level == "medio":
        bump = 1
    elif level == "avanzado":
        bump = 2
    return max(1, base_sets + bump)


def _is_exercise_excluded(exercise: Exercise, pathologies: Iterable[str]) -> bool:
    pathology_set = set(pathologies)
    if not pathology_set:
        return False
    exercise_contras = {value.lower() for value in (exercise.contraindications or [])}
    return bool(pathology_set & exercise_contras)


def _exercise_to_payload(exercise: Exercise) -> Dict[str, Any]:
    return {
        "exercise_id": exercise.id,
        "name": exercise.name,
        "pattern": exercise.pattern,
        "sets": exercise.sets,
        "reps": exercise.reps,
        "rest": exercise.rest,
        "intensity": exercise.intensity,
        "minutes": exercise.minutes,
        "notes": exercise.notes,
        "contraindications": exercise.contraindications,
    }


def _estimate_minutes(section: str, items: List[Dict[str, Any]]) -> int:
    total = sum(item.get("minutes") or 0 for item in items)
    if total == 0:
        if section == "warmup":
            return FALLBACK_WARMUP_ITEM["minutes"]
        if section == "cooldown":
            return FALLBACK_COOLDOWN_ITEM["minutes"]
    return total
