from typing import List, Optional, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..search import build_results

router = APIRouter()

ALLOWED_PATHOLOGIES = {"hombro", "lumbar", "rodilla"}
ALLOWED_OBJECTIVES = {"fuerza", "hipertrofia", "resistencia", "movilidad", "salud"}
ALLOWED_LEVELS = {"principiante", "medio", "avanzado"}


class SearchRequest(BaseModel):
    # Compatibilidad: se puede enviar 'objective' (str) o 'objectives' (list[str])
    objective: Optional[str] = Field(default=None)
    objectives: Optional[List[str]] = Field(default=None)

    session_minutes: Optional[int] = Field(default=None, ge=10, le=180)
    pathologies: List[str] = Field(default_factory=list)
    q: Optional[str] = Field(default=None, max_length=120)

    level: Literal["principiante", "medio", "avanzado"] = "medio"


@router.post("/search")
def search(payload: SearchRequest) -> dict:
    # Normalizar objetivos a lista (lower, sin vacíos)
    objectives: List[str] = []
    if payload.objectives and isinstance(payload.objectives, list):
        objectives = [str(x).strip().lower() for x in payload.objectives if str(x).strip()]
    elif payload.objective:
        objectives = [payload.objective.strip().lower()]

    if not objectives:
        raise HTTPException(status_code=400, detail="Debes indicar 'objective' o 'objectives'.")

    # Validar objetivos
    for obj in objectives:
        if obj not in ALLOWED_OBJECTIVES:
            raise HTTPException(status_code=400, detail=f"Unsupported objective '{obj}'.")

    # Validar patologías
    normalized_pathologies = [v.strip().lower() for v in payload.pathologies if v.strip()]
    for v in normalized_pathologies:
        if v not in ALLOWED_PATHOLOGIES:
            raise HTTPException(status_code=400, detail=f"Unsupported pathology '{v}'.")

    # Validar nivel
    level = str(payload.level).strip().lower()
    if level not in ALLOWED_LEVELS:
        raise HTTPException(status_code=400, detail=f"Unsupported level '{level}'.")

    return build_results(
        objectives=objectives,
        session_minutes=payload.session_minutes,
        pathologies=normalized_pathologies,
        level=level,
        q=payload.q.strip() if payload.q else None,
    )
