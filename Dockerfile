FROM python:3.12-slim AS builder

WORKDIR /app

# Прописываем только requirements и ставим пакеты в префикс /install
# Используем только бинарные колёса, чтобы избежать локальной компиляции
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip \
 && python -m pip install --no-cache-dir --prefix=/install --only-binary=:all: -r /app/requirements.txt

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

# Копируем установленные в builder пакеты в /usr/local (Python их найдёт автоматически)
COPY --from=builder /install /usr/local

# Копируем код приложения
COPY . /app

# Убедимся, что бинарники из /usr/local/bin доступны в PATH
ENV PATH="/usr/local/bin:${PATH}"

# Команда запуска
CMD ["python", "main.py"]
