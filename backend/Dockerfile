FROM python:3.12.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY backend/requirements.lock /tmp/requirements.lock
RUN pip install --no-cache-dir -r /tmp/requirements.lock \
    && addgroup --system medikristal \
    && adduser --system --ingroup medikristal --no-create-home medikristal
COPY backend /app/backend
COPY contracts /app/contracts
COPY frontend /app/frontend
ENV PYTHONPATH=/app/backend MEDIKRISTAL_CONTRACT_DIR=/app/contracts MEDIKRISTAL_FRONTEND_DIR=/app/frontend
USER medikristal
CMD ["uvicorn","medikristal.app:app","--host","0.0.0.0","--port","8000"]
