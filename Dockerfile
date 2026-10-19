FROM node:24-bookworm-slim AS frontend
WORKDIR /app/frontend
RUN npm install -g pnpm@11.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home guestguard
COPY backend/ backend/
COPY scripts/ scripts/
COPY --from=frontend /app/frontend/dist/ frontend/dist/
RUN mkdir -p data models && chown -R guestguard:guestguard /app
USER guestguard
ENV GUESTGUARD_BASE_URL=http://127.0.0.1:8000
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
