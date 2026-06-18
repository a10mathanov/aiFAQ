#!/bin/bash
# ============================================================================
# QUICK REFERENCE: Terminal Commands for Ubuntu Deployment
# Скопируй и вставляй эти команды в терминал Ubuntu по очереди
# ============================================================================

# ============================================================================
# 🚀 БЫСТРЫЙ СТАРТ: 3 команды
# ============================================================================

# КОМАНДА 1️⃣: Загрузить проект с локальной машины
scp -r /path/to/local/aiFAQ/* root@<server-ip>:/root/aiFAQ/

# КОМАНДА 2️⃣: SSH на сервер
ssh root@<server-ip>

# КОМАНДА 3️⃣: Запустить автоматическое развёртывание
cd /root/aiFAQ && chmod +x deploy-bot.sh && ./deploy-bot.sh

# ============================================================================
# 🔧 ИЛИ РУЧНОЕ РАЗВЁРТЫВАНИЕ (если deploy-bot.sh не подходит)
# ============================================================================

# ОБНОВИТЬ СИСТЕМУ
sudo apt-get update
sudo apt-get upgrade -y

# УСТАНОВИТЬ DOCKER
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# ДОБАВИТЬ ПОЛЬЗОВАТЕЛЯ В DOCKER GROUP
sudo usermod -aG docker $USER
newgrp docker

# УСТАНОВИТЬ DOCKER COMPOSE
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# ПЕРЕЙТИ В ПАПКУ ПРИЛОЖЕНИЯ
cd /root/aiFAQ

# СОЗДАТЬ ПАПКУ ДЛЯ ЛОГОВ
mkdir -p logs

# ПРОВЕРИТЬ, ЧТО ВСЕ ФАЙЛЫ НА МЕСТЕ
ls -la tenants/test_clinic/.env
ls -la sa-key.json

# ЗАПУСТИТЬ КОНТЕЙНЕР
docker-compose up -d

# ПРОВЕРИТЬ СТАТУС
docker-compose ps
docker-compose logs --tail=50

# ============================================================================
# 📊 МОНИТОРИНГ И УПРАВЛЕНИЕ
# ============================================================================

# РЕАЛЬНЫЕ ЛОГИ (с прокруткой)
docker-compose logs -f aifaq-bot

# ОСТАНОВИТЬ БОТ
docker-compose down

# ПЕРЕЗАПУСТИТЬ БОТ
docker-compose restart

# ПЕРЕСОБРАТЬ ОБРАЗ И ЗАПУСТИТЬ (если изменился код)
docker-compose up -d --build

# ПРОВЕРИТЬ ИСПОЛЬЗОВАНИЕ РЕСУРСОВ
docker stats aifaq-bot

# ВХОД В КОНТЕЙНЕР (для отладки)
docker-compose exec aifaq-bot /bin/bash

# УДАЛИТЬ КОНТЕЙНЕР И ОБРАЗ
docker-compose down --rmi all

# ============================================================================
# 🔍 TROUBLESHOOTING
# ============================================================================

# ПРОВЕРИТЬ ДОСТУП К TELEGRAM API
curl -I https://api.telegram.org

# ПРОВЕРИТЬ ТОКЕН БОТА
grep TELEGRAM_BOT_TOKEN tenants/test_clinic/.env

# ПРОВЕРИТЬ, ЧТО sa-key.json НЕ В ОБРАЗЕ
docker run --rm aifaq-bot:latest cat /app/sa-key.json 2>/dev/null || echo "✅ sa-key.json не в образе (хорошо!)"

# ВЫВЕСТИ ВСЕ КОНТЕЙНЕРЫ
docker ps -a

# ВЫВЕСТИ ВСЕ ОБРАЗЫ
docker images

# УДАЛИТЬ НЕИСПОЛЬЗУЕМЫЕ ОБРАЗЫ
docker image prune -a --force

# ============================================================================
# 💡 ПОЛЕЗНЫЕ ОДНОНОЧЕРЫ
# ============================================================================

# СКОПИРОВАТЬ ФАЙЛЫ С СЕРВЕРА НА ЛОКАЛЬНУЮ МАШИНУ
scp -r root@<server-ip>:/root/aiFAQ/logs/* ./logs/

# ОТПРАВИТЬ ФАЙЛ НА СЕРВЕР
scp ./tenants/test_clinic/.env root@<server-ip>:/root/aiFAQ/tenants/test_clinic/.env

# ПРОВЕРИТЬ РАЗМЕР ОБРАЗА
docker images aifaq-bot

# ПОЛУЧИТЬ IP КОНТЕЙНЕРА
docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' aifaq-bot

# ПРОВЕРИТЬ, КАКОЙ ПРОЦЕСС СЛУШАЕТ ПОРТСОК
netstat -tlnp | grep 9999

# ============================================================================
# 🔐 БЕЗОПАСНОСТЬ
# ============================================================================

# ПРОВЕРИТЬ ПРАВА НА ВАЖНЫЕ ФАЙЛЫ
ls -la tenants/test_clinic/.env
ls -la sa-key.json

# УСТАНОВИТЬ ПРАВИЛЬНЫЕ ПРАВА (только владелец может читать)
chmod 600 tenants/test_clinic/.env
chmod 600 sa-key.json

# ПРОВЕРИТЬ ПЕРЕМЕННЫЕ В КОНТЕЙНЕРЕ
docker-compose exec aifaq-bot env | grep -i telegram

# ============================================================================
# 📝 ПЕРЕМЕННЫЕ ДЛЯ ЗАМЕНЫ
# ============================================================================

# Замени:
# <server-ip>        → IP адрес твоего Ubuntu сервера (например: 123.45.67.89)
# /path/to/local/aiFAQ → полный путь к папке проекта на локальной машине

# Примеры:
# scp -r /Users/user/projects/aiFAQ/* root@123.45.67.89:/root/aiFAQ/
# ssh root@123.45.67.89

# ============================================================================
# ✅ ЧЕКЛИСТ ПОСЛЕ РАЗВЁРТЫВАНИЯ
# ============================================================================

# 1. [ ] Контейнер запущен: docker-compose ps → STATUS: Up
# 2. [ ] Логи не содержат ошибок: docker-compose logs | grep ERROR
# 3. [ ] Бот отвечает в Telegram: отправить /start
# 4. [ ] Логи сохраняются: ls logs/
# 5. [ ] Автоперезапуск работает: docker-compose restart && sleep 3 && docker-compose ps
# 6. [ ] sa-key.json защищен: ls -la sa-key.json → -rw------- (600)
# 7. [ ] .env защищен: ls -la tenants/test_clinic/.env → -rw------- (600)

# ============================================================================
