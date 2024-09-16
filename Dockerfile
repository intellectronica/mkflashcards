FROM python:3.12
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ADD . /app
WORKDIR /app
RUN uv sync --frozen
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
