# 🚀 aiFAQ Telegram Bot — Deployment Guide (Ubuntu + Docker)

## 📋 Overview

Этот документ описывает развёртывание aiFAQ Telegram Bot на Ubuntu VPS с использованием Docker.

**Сервер:** Ubuntu (Timeweb Cloud / любой VPS)  
**Сеть:** Прямой доступ к API Telegram (нет необходимости в прокси)  
**Развёртывание:** Docker + Docker Compose

---

## ✅ Требования

- **Сервер:** Ubuntu 20.04+ или совместимый дистрибутив Linux
- **Docker:** 20.10+
- **Docker Compose:** 2.0+
- **Доступ:** SSH доступ на сервер с правами sudo
- **Credentials:**
  - Telegram Bot Token (от @BotFather)
  - Yandex Cloud Folder ID
  - Yandex Cloud Service Account Key (sa-key.json)
  - Admin Chat ID (Telegram группа для операторов)

---

## 🔧 Шаг 1: Подготовка локальной машины

### 1.1 Убедитесь, что все файлы на месте:

```
aiFAQ/
├── main.py
├── config.py
├── requirements.txt
├── Dockerfile                          # ← обновлён для Ubuntu
├── docker-compose.yml                  # ← новый
├── deploy-bot.sh                       # ← скрипт развёртывания
├── tenants/
│   └── test_clinic/
│       ├── config.py
│       ├── .env                        # ← обязателен!
│       └── knowledge.txt
├── handlers/
│   ├── __init__.py
│   └── user_handlers.py
├── services/
│   ├── __init__.py
│   └── yandex_gpt.py
└── sa-key.json                         # ← обязателен!
```

### 1.2 Подготовьте `.env` файл (`tenants/test_clinic/.env`):

```env
# Telegram Bot Token (от @BotFather)
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklmnoPQRstuvWXYZ

# Yandex Cloud Folder ID
YANDEX_FOLDER_ID=b1g3dvgvhoidv5mbdkrp

# Admin Chat ID (Telegram группа для операторов)
ADMIN_CHAT_ID=-1001234567890

# Опционально: Временная зона для логов
# TZ=Europe/Moscow
```

### 1.3 Убедитесь, что `sa-key.json` в корне проекта:

```bash
ls -la sa-key.json
```

---

## 📤 Шаг 2: Загрузка файлов на сервер

### Вариант A: Через Git (рекомендуется)

```bash
# На сервере
ssh root@<server-ip>

cd /root
git clone https://github.com/your-org/aiFAQ.git
cd aiFAQ
```

### Вариант B: Через SCP/SFTP

```bash
# На локальной машине
scp -r ./* root@<server-ip>:/root/aiFAQ/

# На сервере
ssh root@<server-ip>
cd /root/aiFAQ
```

---

## 🐳 Шаг 3: Развёртывание Docker

### 3.1 Автоматическое развёртывание (рекомендуется)

```bash
# На сервере, в /root/aiFAQ

chmod +x deploy-bot.sh
./deploy-bot.sh

# Скрипт выполнит:
# 1. Обновление системы
# 2. Установку Docker + Docker Compose
# 3. Проверку конфигов
# 4. Построение и запуск контейнера
```

### 3.2 Ручное развёртывание

```bash
# На сервере, в /root/aiFAQ

# 1️⃣ Обновление системы
sudo apt-get update
sudo apt-get upgrade -y

# 2️⃣ Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
rm get-docker.sh

# Добавьте текущего пользователя в группу docker (не требует sudo далее)
sudo usermod -aG docker $USER
newgrp docker

# 3️⃣ Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 4️⃣ Создание логов директории
mkdir -p logs

# 5️⃣ Построение образа и запуск контейнера
docker-compose build
docker-compose up -d

# 6️⃣ Проверка статуса
docker-compose ps
docker-compose logs --tail=50
```

---

## 🔍 Проверка после развёртывания

### Логи бота

```bash
# Реальные логи (follow mode)
docker-compose logs -f aifaq-bot

# Последние 50 строк
docker-compose logs --tail=50 aifaq-bot

# Особенно ищите:
# ✅ "Knowledge base loaded from..."
# ✅ "Starting bot polling..."
# ✅ "Bot started successfully"
# ❌ Ошибки подключения к api.telegram.org
```

### Статус контейнера

```bash
# Проверить, жив ли контейнер
docker-compose ps

# Вывод должен показывать:
# STATUS: Up X minutes

# Если контейнер в состоянии "Exited" — проверьте логи
```

### Проверка работы бота

В Telegram отправьте `/start` вашему боту. Вы должны получить приветственное сообщение.

---

## 🛠️ Часто используемые команды

```bash
# Остановить бота
docker-compose down

# Перезапустить бота
docker-compose restart

# Пересобрать образ (если изменился код)
docker-compose up -d --build

# Просмотр используемых ресурсов
docker stats aifaq-bot

# Вход в контейнер (для отладки)
docker-compose exec aifaq-bot /bin/bash

# Удалить образ и контейнер полностью
docker-compose down --rmi all
```

---

## 🔐 Секретность и безопасность

### ✅ Чтобы файлы конфигурации не были скопированы в образ:

- `.env` **не** копируется в образ (монтируется как volume)
- `sa-key.json` **не** копируется в образ (монтируется как volume)
- Используется `.dockerignore` для исключения конфиденциальных файлов

### ✅ Проверка

```bash
# На сервере
docker run --rm aifaq-bot:latest cat /app/.env 2>/dev/null || echo "❌ .env не в образе (хорошо!)"
docker run --rm aifaq-bot:latest cat /app/sa-key.json 2>/dev/null || echo "❌ sa-key.json не в образе (хорошо!)"
```

### ✅ Непривилегированный пользователь

Контейнер запускается под пользователем `appuser` (не root), что повышает безопасность.

---

## 🐛 Troubleshooting

### ❌ Ошибка: "Cannot connect to api.telegram.org"

**Причины:** Блокировка сети, firewall, неверный токен  
**Решение:**
```bash
# Проверьте, есть ли доступ к Telegram
curl -I https://api.telegram.org

# Проверьте токен в .env
cat tenants/test_clinic/.env | grep TELEGRAM_BOT_TOKEN
```

### ❌ Ошибка: "Permission denied"

**Причина:** Недостаточно прав для Docker  
**Решение:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

### ❌ Контейнер постоянно перезагружается

**Причина:** Код имеет ошибки  
**Решение:**
```bash
# Посмотрите логи
docker-compose logs aifaq-bot

# Вход в контейнер для отладки
docker-compose exec aifaq-bot python -c "import handlers.user_handlers; print('OK')"
```

### ❌ Файлы `.env` и `sa-key.json` не найдены

**Решение:**
```bash
# Проверьте наличие
ls -la /root/aiFAQ/tenants/test_clinic/.env
ls -la /root/aiFAQ/sa-key.json

# Если не существуют — загрузите через SCP/Git
```

---

## 📊 Мониторинг

### Логирование Docker Compose

В `docker-compose.yml` настроено:
- **JSON логирование** для сохранения логов на диск
- **max-size: 10m** — максимальный размер лог-файла
- **max-file: 3** — количество сохраняемых лог-файлов

Логи сохраняются в:
```
/var/lib/docker/containers/<container-id>/
```

### Автоматический перезапуск

Установлено `restart: always`, поэтому бот автоматически перезагружается при:
- Падении приложения
- Перезагрузке сервера

---

## 🚀 Обновление кода

Если вы обновили код в Git:

```bash
cd /root/aiFAQ

# Загрузить новый код
git pull

# Пересобрать образ и перезапустить
docker-compose up -d --build

# Проверить логи
docker-compose logs -f
```

---

## 📞 Поддержка

Если возникли проблемы:

1. Проверьте логи: `docker-compose logs -f`
2. Убедитесь, что все файлы конфигурации на месте
3. Проверьте права доступа: `ls -la tenants/test_clinic/.env sa-key.json`
4. Перезагрузитесь: `docker-compose restart`

---

**Версия:** 1.0  
**Дата:** 2026-06-18  
**Сервер:** Ubuntu 20.04+ / Timeweb Cloud
