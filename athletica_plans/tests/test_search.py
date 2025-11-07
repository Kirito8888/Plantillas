from fastapi.testclient import TestClient

from app.main import app


def test_search_filters_contraindications():
    payload = {
        "objective": "hipertrofia",
        "session_minutes": 45,
        "pathologies": ["lumbar"],
        "q": "press mancuernas",
    }

    with TestClient(app) as client:
        response = client.post("/api/search", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["results"], "Expected at least one routine result"

    first_result = data["results"][0]
    sections = first_result["sections"]
    assert "warmup" in sections
    assert "main" in sections
    assert "cooldown" in sections

    main_names = {item["name"].lower() for item in sections["main"]["items"]}
    assert "buenos dias con barra" not in main_names
    assert "peso muerto convencional" not in main_names

    for section_key in ("warmup", "main", "cooldown"):
        items = sections[section_key]["items"]
        assert items, f"Expected items in section '{section_key}'"


def test_search_combo_objectives_and_level():
    payload = {
        "objectives": ["fuerza", "hipertrofia"],
        "session_minutes": 60,
        "pathologies": ["hombro"],
        "level": "medio",
        "q": "remo mancuernas",
    }
    with TestClient(app) as client:
        response = client.post("/api/search", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["results"]
    first = data["results"][0]
    assert first["level"] == "medio"
    assert "warmup" in first["sections"]
    assert "main" in first["sections"]
    assert "cooldown" in first["sections"]
