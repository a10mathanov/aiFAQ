# 📦 Обновление и установка SOCKS5 прокси поддержки

## Быстрое обновление

Если у вас уже установлен бот версии 1.0.0, обновите зависимости:

```bash
pip install -r requirements.txt --upgrade
```

## Что нового в v1.1.0

✨ **Поддержка SOCKS5 прокси** для подключения к Telegram и YandexGPT через прокси-сервер

## Текущая конфигурация прокси

Бот уже настроен с SOCKS5 прокси:

```
socks5://oWXsJw:rLcetL@77.83.185.89:8000
```

## Как использовать

### Запуск с прокси (текущая конфигурация)

```bash
python main.py
```

При запуске вы должны увидеть:
```
✅ Конфигурация загружена успешно
✅ Прокси коннектор создан: socks5://oWXsJw:rLcetL@77.83.185.89:8000
✅ Bot инициализирован с SOCKS5 прокси
```

### Изменение прокси

**Вариант 1: В коде**

Отредактируйте `main.py`:
```python
PROXY_URL = "socks5://ваш_логин:ваш_пароль@ваш_ip:ваш_порт"
```

Отредактируйте `handlers/user_handlers.py`:
```python
PROXY_URL = "socks5://ваш_логин:ваш_пароль@ваш_ip:ваш_порт"
```

**Вариант 2: Через переменные окружения (рекомендуется)**

Добавьте в `.env`:
```env
PROXY_URL=socks5://ваш_логин:ваш_пароль@ваш_ip:ваш_порт
```

Обновите `config.py`:
```python
PROXY_URL: str = ""  # из .env
```

### Отключение прокси

**Способ 1: В `main.py`**
```python
PROXY_URL = None  # Отключить прокси
```

**Способ 2: В `handlers/user_handlers.py`**
```python
gpt_service = YandexGPTService(
    folder_id="b1g3dvgvhoidv5mbdkrp",
    sa_key_path="sa-key.json",
    model=settings.YANDEX_GPT_MODEL,
    timeout=settings.REQUEST_TIMEOUT,
    # proxy_url=PROXY_URL  # Закомментируйте эту строку
)
```

## Возможные проблемы

### "Cannot connect to proxy"

Убедитесь, что:
1. Прокси IP и порт верны
2. Прокси сервер доступен
3. Учетные данные (логин/пароль) верны

Проверка:
```powershell
telnet 77.83.185.89 8000
```

### Медленное соединение

Это нормально для прокси соединений. Увеличьте таймаут в `config.py`:
```python
REQUEST_TIMEOUT: int = 60  # Было: 30
```

### Прокси временно недоступен

Бот автоматически выведет ошибку и продолжит работу (пользователь получит сообщение об ошибке).

## Документация

📖 Подробная информация в [PROXY_SETUP.md](PROXY_SETUP.md)

🔧 История изменений в [CHANGELOG.md](CHANGELOG.md)

❓ Решение проблем в [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

🚀 Быстрый старт в [QUICKSTART.md](QUICKSTART.md)

## Проверка установки

```bash
# Проверить зависимости
pip list | grep aiohttp

# Должен вывести:
# aiohttp                 3.9.1
# aiohttp-socks          0.8.4  ← Новая зависимость
```

## Запуск диагностики

```bash
python diagnose.py
```

Проверит:
- Интернет соединение
- DNS разрешение
- Доступность API
- (В будущем: проверка прокси)

---

✅ Готово! Бот готов к работе с SOCKS5 прокси

Для подробной информации смотрите [PROXY_SETUP.md](PROXY_SETUP.md)
