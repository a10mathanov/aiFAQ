# ============================================================================
# Multi-stage build для оптимизации размера образа
# ============================================================================

FROM python:3.12-slim as builder

WORKDIR /build

# Установим зависимости для build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements и устанавливаем зависимости в виртуальное окружение
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# ============================================================================
# Production stage
# ============================================================================

FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Установим runtime зависимости
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создаём непривилегированного пользователя для безопасности
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Копируем установленные пакеты из builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Копируем код приложения (не копируем .env и sa-key.json — монтируйте их в контейнере как volumes)
COPY --chown=appuser:appuser . .

# Устанавливаем PATH для пользователя
ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONPATH=/app

# Переходим на непривилегированного пользователя
USER appuser

# Запускаем приложение
CMD ["python", "main.py"]
