# 🌐 Конфигурация SOCKS5 прокси

## Описание

Бот поддерживает SOCKS5 прокси для подключения через прокси-серверы. Это полезно, когда:
- Прямое подключение к Telegram API заблокировано
- Вы находитесь за корпоративным брандмауэром
- Требуется скрыть IP адрес
- Требуется использовать специальный маршрут для сетевого трафика

## Текущая конфигурация

Бот настроен с SOCKS5 прокси:

```
URL: socks5://oWXsJw:rLcetL@77.83.185.89:8000
IP: 77.83.185.89
Порт: 8000
Логин: oWXsJw
Пароль: rLcetL
```

## Как это работает

### 1. Bot инициализация (main.py)

Бот использует `ProxyConnector` из `aiohttp_socks` для создания SOCKS5 коннектора:

```python
# Создать ProxyConnector для SOCKS5
proxy_connector = ProxyConnector.from_url(PROXY_URL)

# Создать ClientSession с прокси коннектором
session = aiohttp.ClientSession(connector=proxy_connector)

# Создать AiohttpSession с custom session
bot_session = AiohttpSession(client=session)

# Создать Bot с custom session
bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, session=bot_session)
```
    folder_id="b1g3dvgvhoidv5mbdkrp",
    sa_key_path="sa-key.json",
    model=settings.YANDEX_GPT_MODEL,
YandexGPT сервис также использует прокси при подключении к API:

```python
# Создать connector с прокси
connector = ProxyConnector.from_url(self.proxy_url)

async with aiohttp.ClientSession(timeout=self.timeout, connector=connector) as session:
    async with session.post(self.api_url, ...) as response:
        # Обработка ответа
```

## Изменение прокси

### Способ 1: Изменить в коде (не рекомендуется для production)

**main.py:**
```python
PROXY_URL = "socks5://новый_логин:новый_пароль@новый_ip:новый_порт"
```

**handlers/user_handlers.py:**
```python
PROXY_URL = "socks5://новый_логин:новый_пароль@новый_ip:новый_порт"
```

### Способ 2: Использовать переменные окружения (рекомендуется)

Обновите `config.py`:

```python
class Settings(BaseSettings):
    # Существующие переменные...
    
    # Прокси
    PROXY_URL: str = "socks5://oWXsJw:rLcetL@77.83.185.89:8000"
```

Обновите `.env`:
```env
PROXY_URL=socks5://новый_логин:новый_пароль@новый_ip:новый_порт
```

Обновите `main.py`:
```python
from config import settings

PROXY_URL = settings.PROXY_URL
```

Обновите `handlers/user_handlers.py`:
```python
from config import settings

PROXY_URL = settings.PROXY_URL
```

## Формат SOCKS5 URL

```
socks5://[username[:password]@]host:port
```

### Примеры:

**С аутентификацией:**
```
socks5://user:password@proxy.example.com:1080
```

**Без аутентификации:**
```
socks5://proxy.example.com:1080
```

**С альтернативным портом:**
```
socks5://admin:secret123@192.168.1.100:9090
```

## Проверка прокси

### Способ 1: Запустить диагностику

```bash
python diagnose.py
```

Обновленная версия должна проверять также прокси соединение.

### Способ 2: Временно отключить прокси

В `main.py`:
```python
PROXY_URL = None  # Отключить прокси
```

В `handlers/user_handlers.py`:
```python
PROXY_URL = None  # Отключить прокси
```

### Способ 3: Проверить лог сообщений

При запуске бот выведет:
```
✅ Прокси коннектор создан: socks5://oWXsJw:rLcetL@77.83.185.89:8000
✅ Bot инициализирован с SOCKS5 прокси
```

## Требуемые зависимости

```bash
pip install aiohttp-socks==0.8.4
```

Убедитесь, что `requirements.txt` содержит:
```
aiohttp-socks==0.8.4
```

Установите все зависимости:
```bash
pip install -r requirements.txt
```

## Потенциальные проблемы

### Проблема: "Cannot connect to proxy"

**Причины:**
- Прокси сервер недоступен
- Неправильный IP или порт
- Прокси требует аутентификацию, но учетные данные неверны
- Брандмауэр блокирует соединение с прокси

**Решение:**
```bash
# Проверьте доступность прокси
telnet 77.83.185.89 8000

# Или используйте Python
python -c "import socket; s = socket.socket(); s.connect(('77.83.185.89', 8000)); print('OK')"
```

### Проблема: "Auth failed"

**Причины:**
- Неправильный логин или пароль
- Учетные данные истекли

**Решение:**
- Проверьте учетные данные прокси
- Свяжитесь с провайдером прокси

### Проблема: Медленное соединение

Если используется прокси, скорость может быть немного ниже из-за дополнительного маршрутизирования.

**Решение:**
- Увеличьте таймаут в `config.py`:
  ```python
  REQUEST_TIMEOUT: int = 60  # Было: 30
  ```

### Проблема: Прокси временно недоступен

Бот правильно обработает ошибку подключения и выведет:
```
❌ Network error - Cannot connect to YandexGPT API: ...
```

При таких ошибках бот пересылает сообщение пользователю без перезагрузки.

## Отключение прокси

Если нужно отключить прокси:

**main.py:**
```python
PROXY_URL = None  # Или удалите строку создания прокси коннектора
```

**handlers/user_handlers.py:**
```python
PROXY_URL = None
```

Или закомментируйте параметр `proxy_url`:
```python
gpt_service = YandexGPTService(
    folder_id="b1g3dvgvhoidv5mbdkrp",
    sa_key_path="sa-key.json",
    model=settings.YANDEX_GPT_MODEL,
    timeout=settings.REQUEST_TIMEOUT,
    # proxy_url=PROXY_URL  # Отключено
)
```

## Лучшие практики

✅ **Рекомендуется:**
- Хранить учетные данные прокси в переменных окружения (`.env`)
- Регулярно проверять статус прокси
- Использовать более надежный прокси для production
- Иметь fallback прокси на случай отказа основного

❌ **Не рекомендуется:**
- Жестко кодировать пароли в исходном коде
- Коммитить файлы с паролями в Git
- Использовать публичные прокси
- Доверять прокси неизвестного происхождения

## Альтернативные решения

### HTTP прокси (вместо SOCKS5)

Если нужен HTTP прокси, обновите URL:
```python
PROXY_URL = "http://user:password@proxy.example.com:8080"
```

### Без прокси через VPN

Если прокси вызывает проблемы, используйте VPN:
```bash
# Установите и запустите VPN
# Затем запустите бот
python main.py
```

## Документация

- [aiohttp_socks документация](https://github.com/romis2k/aiohttp-socks)
- [SOCKS5 RFC 1928](https://tools.ietf.org/html/rfc1928)
- [aiogram с прокси](https://docs.aiogram.dev/en/latest/api/session/aiohttp/)

---

**Последнее обновление:** 2026-06-16
