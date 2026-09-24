FROM python:3.11-slim

WORKDIR /srv

COPY requirements-backend.txt .
RUN pip install --no-cache-dir -r requirements-backend.txt

COPY app/ app/
COPY scripts/ scripts/
COPY alembic.ini .

CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
