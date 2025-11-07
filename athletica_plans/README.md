# Athletica Plans

Athletica Plans es una aplicacion web creada con FastAPI para buscar rutinas de gimnasio personalizadas. Combina un estilo oscuro con acentos naranja y filtra ejercicios contraindicados segun las patologias seleccionadas por la persona usuaria.

## Requisitos

- Python 3.10 o superior (probado con 3.11)

## Instalacion y ejecucion

### Windows

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

### macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

Una vez iniciado el servidor visita http://127.0.0.1:8000/ para usar la interfaz.

## Test

```bash
pytest
```

## Ejemplo de consulta

```bash
curl -X POST "http://127.0.0.1:8000/api/search" ^
  -H "Content-Type: application/json" ^
  -d "{\"objective\":\"hipertrofia\",\"session_minutes\":45,\"pathologies\":[\"lumbar\"],\"q\":\"press mancuernas\"}"
```

