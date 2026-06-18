# ⚡ Быстрый старт

## Шаг 1️⃣: Установка зависимостей

```bash
pip install -r requirements.txt
```

## Шаг 2️⃣: Получение токенов

### Telegram Bot Token
1. Откройте Telegram и найдите **@BotFather**
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте токен вида: `123456789:ABCdef...`

### Yandex Cloud IAM Token и Folder ID
1. Откройте https://console.cloud.yandex.ru/
2. Создайте сервисный аккаунт (если его нет)
3. Создайте IAM токен:
   ```bash
   # Если у вас установлен yc CLI
   yc iam create-token
   ```
   Или получите через консоль Yandex Cloud

4. Найдите свой Folder ID:
   ```bash
   yc config get project-id
   ```
   Или просмотрите в консоли Yandex Cloud

## Шаг 3️⃣: Создание файла .env

Создайте файл `.env` в папке проекта:

```env
TELEGRAM_BOT_TOKEN=123456789:ABCdef_GHIjklMNOpqrst
YANDEX_IAM_TOKEN=t1.9euelZqTlpqOipbOjZiTx5uKkJqWyO3...
YANDEX_FOLDER_ID=ajetma8bv1i397947hj5
```

⚠️ **Важно:**
- Не кладите `.env` в Git (есть `.gitignore`)
- Токены хранятся локально на вашей машине
- Никому не показывайте содержимое `.env`

## Шаг 4️⃣: Запуск бота

```bash
python main.py
```

Вы должны увидеть:
```
✅ Конфигурация загружена успешно
✅ Bot started successfully
   Bot username: @your_bot_name
2026-06-16 14:00:30 - __main__ - INFO - Starting bot polling...
```

## Шаг 5️⃣: Тестирование

1. Найдите вашего бота в Telegram (по username)
2. Отправьте `/start`
3. Отправьте сообщение: "Привет!"
4. Дождитесь ответа от бота

## 🔍 Если что-то не работает

Используйте диагностический скрипт:

```bash
python diagnose.py
```

Он проверит:
- Интернет соединение
- Доступность API

Подробное решение проблем в файле **TROUBLESHOOTING.md**

## 📱 Использование бота

- `/start` - приветствие и справка
- `/help` - справка по командам
- **Любое сообщение** - отправляется в YandexGPT и вы получаете ответ

### Примеры:

```
📝 Что такое машинное обучение?
🤖 Машинное обучение - это раздел искусственного интеллекта...

📝 Напиши стихотворение про программиста
🤖 В мире кода, где строчки живут,
    Программист за клавиатурой сидит...

📝 Помоги решить уравнение: 2x + 5 = 15
🤖 Решим пошагово:
    2x + 5 = 15
    2x = 15 - 5
    2x = 10
    x = 5
```

## 🏗️ Структура проекта

```
aiFAQ/
├── main.py                  # Запуск бота
├── config.py               # Конфигурация
├── diagnose.py             # Диагностика
├── requirements.txt        # Зависимости
├── .env.example            # Пример .env
├── .env                    # Ваши токены (не в Git)
├── .gitignore             # Исключения для Git
├── README.md              # Основная документация
├── TROUBLESHOOTING.md     # Решение проблем
├── handlers/
│   ├── __init__.py
│   └── user_handlers.py   # Обработчики сообщений
└── services/
    ├── __init__.py
    └── yandex_gpt.py      # Интеграция YandexGPT
```

## 🚀 Расширение функциональности

### Добавить новую команду

В файл `handlers/user_handlers.py`:

```python
@router.message(Command("weather"))
async def cmd_weather(message: Message):
    """Команда для получения погоды"""
    await message.answer("🌤️ Скажите, в каком городе?")
```

### Изменить параметры YandexGPT

В файле `services/yandex_gpt.py` в методе `_build_payload`:

```python
"completionOptions": {
    "stream": False,
    "temperature": 0.5,    # Меньше = точнее, больше = креативнее
    "maxTokens": 3000      # Длина ответа
}
```

## ℹ️ Полезные команды

```bash
# Проверить версию Python
python --version

# Обновить pip
python -m pip install --upgrade pip

# Просмотреть установленные пакеты
pip list

# Обновить зависимости
pip install -r requirements.txt --upgrade
```

## 💡 Советы

✅ Регулярно обновляйте IAM токены Yandex Cloud (они действуют 12 часов)
✅ Используйте `.env.example` как шаблон
✅ Проверяйте логи при ошибках (красные `ERROR` строки)
✅ Для production используйте системы мониторинга и логирования
✅ Не коммитьте `.env` в версионную систему

## 🆘 Поддержка

Если нужна помощь:
1. Прочитайте **TROUBLESHOOTING.md**
2. Запустите **diagnose.py**
3. Проверьте логи при запуске
4. Убедитесь, что зависимости установлены: `pip install -r requirements.txt`

---

**Готово! Ваш AI-бот на YandexGPT запущен! 🎉**
