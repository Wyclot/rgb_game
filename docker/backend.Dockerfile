FROM python:3.14-slim
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt
COPY backend /app/backend
CMD ["sh", "-c", "python -m alembic -c backend/alembic.ini upgrade head && python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000"]
