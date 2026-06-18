# YandexGPT Telegram Bot

Telegram-бот на Python с использованием aiogram 3.x и YandexGPT API.

## Возможности

✨ Интеграция с YandexGPT для генерации ответов  
🚀 Асинхронная обработка сообщений  
🔐 Безопасное хранение токенов в переменных окружения  
📝 Чистая модульная структура кода  
⚡ Обработка ошибок и таймауты  
📊 Логирование всех операций  
🌐 **Поддержка SOCKS5 прокси** для обхода ограничений сети

## Требования

- Python 3.10+
- Telegram Bot Token (от @BotFather)
- Yandex Cloud IAM Token
- Yandex Cloud Folder ID

## Установка

### 1. Клонируйте репозиторий и установите зависимости

```bash
# Создайте виртуальное окружение (рекомендуется)
python -m venv venv

# Активируйте окружение
# На Windows:
venv\Scripts\activate
# На macOS/Linux:
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

### 2. Получите необходимые токены

#### Telegram Bot Token:
1. Откройте Telegram и найдите @BotFather
2. Отправьте команду `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

#### Yandex Cloud IAM Token:
1. Создайте аккаунт на [Yandex Cloud](https://cloud.yandex.ru/)
2. Создайте сервисный аккаунт в консоли Yandex Cloud
3. Создайте IAM токен для сервисного аккаунта
4. Скопируйте токен (действует 12 часов)

#### Yandex Cloud Folder ID:
1. В консоли Yandex Cloud найдите ID вашей папки
2. Скопируйте его

### 3. Создайте файл .env

```bash
cp .env.example .env
```

Отредактируйте файл `.env` и добавьте ваши токены:

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
YANDEX_IAM_TOKEN=your_iam_token_here
YANDEX_FOLDER_ID=your_folder_id_here
```

## Запуск

```bash
python main.py
```

Бот начнет работать и будет готов к обработке сообщений.

## Структура проекта

```
aiFAQ/
├── main.py                 # Точка входа приложения
├── config.py              # Конфигурация и переменные окружения
├── requirements.txt       # Зависимости проекта
├── .env.example          # Пример файла переменных окружения
├── .env                  # Переменные окружения (не версионировать!)
├── handlers/
│   ├── __init__.py
│   └── user_handlers.py  # Обработчики команд и сообщений
└── services/
    ├── __init__.py
    └── yandex_gpt.py    # Сервис для работы с YandexGPT API
```

## Использование

### Команды бота

- `/start` - Начать работу с ботом
- `/help` - Показать справку
- Отправьте любой текст - бот ответит используя YandexGPT

### Примеры использования

```
Пользователь: Что такое машинное обучение?
Бот: Машинное обучение - это раздел искусственного интеллекта...

Пользователь: Напиши стихотворение про программиста
Бот: В мире кода, где строчки живут...
```

## Обработка ошибок

Бот обрабатывает следующие ошибки:
- Пустые сообщения
- Сообщения, превышающие максимальную длину (4096 символов)
- Ошибки сети и таймауты при обращении к API
- Некорректные ответы от API

При возникновении ошибки пользователю отправляется понятное сообщение.

## Логирование

Все события логируются в консоль с указанием времени и уровня серьезности:
- INFO: основные события (запуск, получение ответа)
- WARNING: предупреждения (длинные сообщения)
- ERROR: ошибки при выполнении операций

## Важные замечания

⚠️ **Безопасность:**
- Никогда не коммитьте файл `.env` в репозиторий
- Используйте `.gitignore` для исключения `.env`
- Регулярно обновляйте IAM токены Yandex Cloud

⏰ **IAM токены Yandex Cloud:**
- Действуют 12 часов
- После истечения需要 получить новый токен
- Рассмотрите использование refresh токенов для автоматического обновления

⚡ **Ограничения:**
- Максимум 4096 символов в сообщении
- Таймаут запроса к API: 30 секунд
- Рассмотрите добавление rate limiting для защиты от DDoS

## Расширение функциональности

### Добавление новых команд

Отредактируйте файл [handlers/user_handlers.py](handlers/user_handlers.py):

```python
@router.command(Command("mycommand"))
async def cmd_mycommand(message: Message):
    await message.answer("Мой ответ")
```

### Изменение параметров YandexGPT

В файле [config.py](config.py) измените параметры:
- `YANDEX_GPT_MODEL` - используемая модель
- `temperature` - креативность ответов (0.0-1.0)
- `maxTokens` - максимальная длина ответа

### Добавление состояний (FSM)

Для более сложной логики используйте FSM (Finite State Machine) из aiogram:

```python
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

class Form(StatesGroup):
    waiting_for_name = State()
```

## Требования к API

- Yandex Cloud должен иметь включенный API для YandexGPT
- Сервисный аккаунт должен иметь роль `ai.languageModels.user`
- Папка должна быть активной и иметь платежный аккаунт

## Документация

- [Aiogram 3 Documentation](https://docs.aiogram.dev/)
- [Yandex Cloud YandexGPT API](https://cloud.yandex.ru/docs/foundation-models/yandexgpt/)
- [Yandex Cloud IAM](https://cloud.yandex.ru/docs/iam/)

## 🌐 Поддержка SOCKS5 Прокси

Бот поддерживает SOCKS5 прокси для подключения через прокси-серверы:

**Текущая конфигурация:**
```
IP: 77.83.185.89
Порт: 8000
Логин: oWXsJw
Пароль: rLcetL
URL: socks5://oWXsJw:rLcetL@77.83.185.89:8000
```

**Как это работает:**
1. Bot использует `ProxyConnector` из `aiohttp_socks`
2. YandexGPT API также соединяется через прокси
3. Все соединения маршрутизируются через прокси-сервер

**Изменение прокси:**
Отредактируйте переменные `PROXY_URL` в:
- [main.py](main.py#L28)
- [handlers/user_handlers.py](handlers/user_handlers.py#L18)

**Подробнее:** см. [PROXY_SETUP.md](PROXY_SETUP.md)

## Лицензия

MIT

## Автор

Создано как пример интеграции YandexGPT с Telegram ботом.
