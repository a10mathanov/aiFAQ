# Решение проблем (Troubleshooting)

## Ошибка: "Cannot connect to host api.telegram.org:443"

Это означает, что бот не может подключиться к Telegram API.

### Причины и решения

#### 1. 🌐 Проблема с интернет соединением

**Признаки:** Другие приложения тоже не имеют интернета

**Решение:**
```bash
# Проверьте подключение
ping google.com

# Перезагрузите маршрутизатор
# Проверьте кабель/WiFi соединение
```

#### 2. 🔥 Брандмауэр или антивирус блокирует соединение

**Признаки:** Интернет работает, но на порт 443 нет доступа

**Решение:**
- Проверьте Windows Defender Firewall
  - Откройте: Параметры > Приватность и безопасность > Брандмауэр Windows
  - Нажмите "Разрешить приложению через брандмауэр"
  - Убедитесь, что Python разрешен для входящих и исходящих подключений

- Проверьте антивирус (если установлен)
  - Временно отключите или добавьте Python в исключения

#### 3. VPN или прокси

**Признаки:** Есть VPN или прокси, настроенный в системе

**Решение:**
```bash
# Попробуйте отключить VPN
# Или настройте прокси в коде (смотрите документацию aiogram)
```

#### 4. DNS не разрешает доменное имя

**Признаки:** Другие сайты работают, но api.telegram.org нет

**Решение:**
```bash
# Попробуйте другой DNS:
# Откройте: Параметры > Сеть и интернет > Дополнительные параметры сети > DNS

# Используйте:
# Google DNS: 8.8.8.8, 8.8.4.4
# Cloudflare DNS: 1.1.1.1, 1.0.0.1
```

#### 5. Telegram API временно недоступен (редко)

**Признаки:** Все остальное работает, но Telegram не отвечает

**Решение:**
```bash
# Подождите несколько минут и попробуйте снова
# Проверьте статус: https://core.telegram.org/bots/api#recent-changes
```

### 🔧 Диагностика

Используйте встроенный скрипт диагностики:

```bash
python diagnose.py
```

Он проверит:
- ✅ Интернет соединение
- ✅ DNS разрешение
- ✅ Доступность Telegram API
- ✅ Доступность YandexGPT API

## Ошибка: "Token is invalid!" или "Invalid token format"

**Причины:**
1. Токен скопирован неправильно (пробелы, переносы строк)
2. Токен еще не активирован
3. Токен истек

**Решение:**
1. Удалите файл `.env`
2. Скопируйте токен снова у @BotFather (без пробелов)
3. Создайте новый `.env` файл вручную

```env
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН_БЕЗ_ПРОБЕЛОВ
YANDEX_IAM_TOKEN=ВАШ_IAM_ТОКЕН
YANDEX_FOLDER_ID=ВАШ_FOLDER_ID
```

## Ошибка: YandexGPT API возвращает 401 или 403

**401 - Unauthorized:** IAM токен невалидный или истекший

**403 - Forbidden:** Неправильный Folder ID или недостаточно прав

**Решение:**
1. Получите новый IAM токен:
   ```bash
   yc iam create-token
   ```
   или через консоль Yandex Cloud

2. Проверьте Folder ID:
   - Откройте консоль Yandex Cloud
   - Найдите вашу папку (Folder) и скопируйте её ID
   - Убедитесь, что это именно Folder ID, а не Project ID

3. Убедитесь, что сервисный аккаунт имеет роль `ai.languageModels.user`

## Ошибка: "Max retries exceeded"

**Причина:** Бот не смог подключиться 5 раз подряд

**Решение:**
1. Проверьте сетевое соединение (используйте `diagnose.py`)
2. Убедитесь, что интернет стабилен
3. Перезагрузитесь и попробуйте снова

## Бот запустился, но не отвечает на сообщения

**Возможные причины:**

1. **Неправильный Folder ID для YandexGPT**
   - Проверьте в консоли Yandex Cloud
   - Убедитесь, что в этой папке включен доступ к YandexGPT

2. **IAM токен истек**
   - IAM токены действуют 12 часов
   - Получите новый токен:
     ```bash
     yc iam create-token
     ```

3. **Не установлены зависимости**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ошибки в логах**
   - Смотрите консоль при запуске
   - Логи начинаются с `ERROR`

## Как включить подробное логирование

Откройте `main.py` и измените:

```python
logging.basicConfig(
    level=logging.DEBUG,  # Было: logging.INFO
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Также в config.py раскомментируйте:
```python
logging.getLogger("aiogram").setLevel(logging.DEBUG)
logging.getLogger("aiohttp").setLevel(logging.DEBUG)
```

Это выведет намного больше информации для диагностики.

## Если ничего не помогает

1. **Создайте новый бот:**
   - Напишите @BotFather в Telegram
   - Создайте нового бота `/newbot`
   - Попробуйте с новым токеном

2. **Проверьте Python:**
   ```bash
   python --version  # Должна быть версия 3.10+
   ```

3. **Переустановите зависимости:**
   ```bash
   pip uninstall -r requirements.txt -y
   pip install -r requirements.txt
   ```

4. **Создайте чистую виртуальную среду:**
   ```bash
   python -m venv venv_new
   venv_new\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

## Полезные ссылки

- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Yandex Cloud Documentation](https://cloud.yandex.ru/docs/)
- [YandexGPT API](https://cloud.yandex.ru/docs/foundation-models/yandexgpt/)
- [Aiogram Documentation](https://docs.aiogram.dev/)
