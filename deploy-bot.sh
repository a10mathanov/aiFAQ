#!/bin/bash
# ============================================================================
# Script: deploy-bot.sh
# Purpose: Развёртывание aiFAQ Telegram Bot на Ubuntu VPS
# ============================================================================

set -e  # Exit on any error

echo "🚀 Начинаем развёртывание aiFAQ Telegram Bot на Ubuntu..."

# ============================================================================
# Step 1: Обновление системы
# ============================================================================

echo "📦 Шаг 1: Обновление системы..."
sudo apt-get update
sudo apt-get upgrade -y

# ============================================================================
# Step 2: Установка Docker и Docker Compose
# ============================================================================

echo "🐳 Шаг 2: Установка Docker и Docker Compose..."

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    echo "   Установка Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    rm get-docker.sh
    
    # Добавляем текущего пользователя в группу docker
    sudo usermod -aG docker $USER
    echo "   ⚠️  Выполните: newgrp docker"
else
    echo "   ✅ Docker уже установлен: $(docker --version)"
fi

# Проверка наличия Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo "   Установка Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    echo "   ✅ Docker Compose уже установлен: $(docker-compose --version)"
fi

# ============================================================================
# Step 3: Переход в папку приложения и подготовка файлов
# ============================================================================

echo "📂 Шаг 3: Создание папки приложения и подготовка..."

# Создаём папку приложения, если её нет
sudo mkdir -p /root/aiFAQ
cd /root/aiFAQ

# Создаём папку для логов
sudo mkdir -p logs

# ============================================================================
# Step 4: Копирование файлов с локальной машины или git
# ============================================================================

echo "📥 Шаг 4: Загрузка кода приложения..."
echo "   Вариант A: Если вы клонируете из Git:"
echo "   git clone <your-repo-url> ."
echo ""
echo "   Вариант B: Если вы загружаете через SCP/SFTP:"
echo "   scp -r ./* root@<server-ip>:/root/aiFAQ/"
echo ""
echo "   ⏸️  Загрузите файлы приложения в /root/aiFAQ, затем нажмите Enter..."
read

# ============================================================================
# Step 5: Проверка наличия .env и sa-key.json
# ============================================================================

echo "🔑 Шаг 5: Проверка конфигурационных файлов..."

if [ ! -f "tenants/test_clinic/.env" ]; then
    echo "❌ ОШИБКА: Файл tenants/test_clinic/.env не найден!"
    echo "   Создайте .env файл с содержимым:"
    echo ""
    echo "   TELEGRAM_BOT_TOKEN=your_token_here"
    echo "   YANDEX_FOLDER_ID=your_folder_id_here"
    echo "   ADMIN_CHAT_ID=-your_admin_group_id_here"
    echo ""
    exit 1
fi

if [ ! -f "sa-key.json" ]; then
    echo "❌ ОШИБКА: Файл sa-key.json не найден!"
    echo "   Загрузите Yandex Cloud service account key в /root/aiFAQ/sa-key.json"
    exit 1
fi

echo "✅ Все необходимые файлы найдены"

# ============================================================================
# Step 6: Постройка и запуск Docker контейнера
# ============================================================================

echo "🔨 Шаг 6: Построение Docker образа и запуск контейнера..."

# Постройка образа
docker-compose build

# Запуск контейнера
docker-compose up -d

# ============================================================================
# Step 7: Проверка статуса
# ============================================================================

echo "✅ Шаг 7: Проверка статуса контейнера..."
sleep 3

if docker-compose ps | grep -q "aifaq-bot"; then
    echo "✅ Контейнер успешно запущен!"
    echo ""
    echo "📊 Текущий статус:"
    docker-compose ps
    echo ""
    echo "📋 Последние логи:"
    docker-compose logs --tail=20
    echo ""
    echo "✅ Развёртывание завершено!"
    echo ""
    echo "💡 Полезные команды:"
    echo "   • Просмотр логов:        docker-compose logs -f"
    echo "   • Остановка бота:        docker-compose down"
    echo "   • Перезапуск бота:       docker-compose restart"
    echo "   • Пересборка образа:     docker-compose up -d --build"
else
    echo "❌ Ошибка: Контейнер не запустился"
    docker-compose logs
    exit 1
fi
