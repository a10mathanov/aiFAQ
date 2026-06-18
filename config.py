"""
Модуль конфигурации приложения.
Загружает переменные окружения из файла .env
"""

import os
import re
import sys
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Класс для управления переменными окружения"""

    @field_validator("TELEGRAM_BOT_TOKEN", "YANDEX_FOLDER_ID", mode="before")
    def strip_string_fields(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value
    @field_validator("YANDEX_FOLDER_ID")
    def validate_folder_id(cls, value: str) -> str:
        if not isinstance(value, str) or not value:
            raise ValueError("YANDEX_FOLDER_ID должен быть непустой строкой")
        if not re.fullmatch(r"[a-z0-9]+", value):
            raise ValueError(
                "YANDEX_FOLDER_ID должен содержать только строчные латинские буквы и цифры"
            )
        return value
    
    # ================== TELEGRAM & PROXY ==================
    TELEGRAM_BOT_TOKEN: str = ""
    # By default no proxy. Configure `SOCKS5_PROXY_URL` in tenant .env if needed.
    SOCKS5_PROXY_URL: str = ""
    
    # ================== YANDEX CLOUD (LLM) ==================
    YANDEX_FOLDER_ID: str = ""
    YANDEX_GPT_API_URL: str = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    YANDEX_GPT_MODEL: str = "yandexgpt/latest"
    
    # ================== ADMIN NOTIFICATIONS ==================
    ADMIN_CHAT_ID: int = -1003903822434
    
    # ================== UNIVERSAL BUSINESS CONFIG ==================
    BUSINESS_NAME: str = "Дерма-Про"
    BUSINESS_TYPE: str = "клиника"
    APPOINTMENT_TARGET: str = "на прием"
    LEAD_MAGNET: str = "Дарим вам купон на 500 рублей на любой первичный прием!"
    BUSINESS_PHONE: str = "+7 (495) 777-22-33"
    BUSINESS_HOURS: str = "Пн-Пт: 9:00-21:00, Сб: 10:00-18:00, Вс: выходной"
    VISIT_REMINDER_TEXT: str = (
        "💡 **Важная памятка перед визитом:**\n\n"
        "1. За 3 часа до приема не наносите на кожу лечебные кремы, мази и макияж.\n"
        "2. Возьмите с собой результаты прошлых анализов, если они есть.\n"
        "3. Приезжайте за 10 минут до начала – оформим бесплатную парковку!"
    )
    
    # ================== FSM CATEGORIES (Dynamic Inline Buttons) ==================
    FSM_CATEGORIES: list = [
        "🔴 Лечение акне / высыпаний",
        "🟤 Удаление родинок / папиллом",
        "🟢 Косметология и уход (чистка, пилинг)",
        "⚪ Другой вопрос",
    ]
    
    # ================== SYSTEM SETTINGS ==================
    MAX_MESSAGE_LENGTH: int = 4096
    REQUEST_TIMEOUT: int = 30
    FSM_TIMEOUT_MINUTES: int = 15
    MAX_CHAT_HISTORY: int = 6

    # ================== SECRETS / SHARED KEYS ==================
    # Path where the shared service account key is mounted (Docker secret or bind-mount).
    # Defaults to project root for local dev, use /run/secrets or mount point in Docker.
    SA_KEY_PATH: str = str(Path(__file__).resolve().parent / "sa-key.json")

    # Throttling (seconds)
    THROTTLE_LIMIT: float = 1.5

    # Fallback admin chat (optional)
    ADMIN_FALLBACK_CHAT_ID: int = 0

    # Localized messages and templates (all UI texts centralized here)
    MESSAGES: dict = {
        "welcome_text": "🎉 Рады видеть вас! {LEAD_MAGNET} 🎁\n\nБонус закрепился за вашим номером. Чтобы воспользоваться, нажмите кнопку меню.",
        "help_text": "ℹ️ Справка по боту {BUSINESS_NAME}:\n\n• Отправьте сообщение — я отвечу по базе знаний.\n• Нажмите '📅 {APPOINTMENT_TARGET}' для оформления заявки.\n• Нажмите '👤 Связь с оператором' — поговорите с менеджером.",
        "empty_message": "❌ Пожалуйста, отправьте непустое сообщение.",
        "too_long_message": "❌ Сообщение слишком длинное. Максимум {MAX_MESSAGE_LENGTH} символов.",
        "prompt_name": "Отлично! Давайте оформим предварительную заявку {APPOINTMENT_TARGET}. Как к вам обращаться? Введите ваше имя:",
        "prompt_select_category": "Спасибо! 🎯\n\nТеперь расскажите, что вас беспокоит. Выберите один вариант:",
        "prompt_phone": "📞 Пожалуйста, укажите номер телефона для связи (например, +79991234567):",
        "prompt_time": "И последнее: в какой день и время вам удобно прийти? (Например: вторник вечер или суббота 10:00-12:00)",
        "throttle_warning": "⏳ Пожалуйста, не отправляйте сообщения так быстро — подождите секунду.",
        "cancelled": "Запись отменена. Вы можете продолжить общение с ассистентом.",
        "operator_called": "📞 Вызываю оператора. Менеджер подключится в этот чат в течение 5 минут.",
        "llm_error": "❌ Не удалось получить ответ от LLM. Пожалуйста, попробуйте позже.",
        "registration_confirmed": "✅ Благодарим вас! Заявка успешно отправлена администраторам. Мы свяжемся с вами в течение 15 минут.",
        "registration_fallback": "⚠️ Ваша заявка принята локально, но уведомление администраторам не отправилось. Пожалуйста, позвоните нам напрямую: {BUSINESS_PHONE}",
        "invalid_phone": "❌ Номер некорректен. Пожалуйста, введите действительный номер телефона (например, +79991234567).",
        "invalid_name": "Пожалуйста, введите корректное имя (минимум 2 символа).",
        "visit_reminder_text": "{VISIT_REMINDER_TEXT}",
    }

    class Config:
        # Load .env from tenant directory (works both on Windows and Linux)
        env_file = str(Path(__file__).resolve().parent / "tenants" / "test_clinic" / ".env")
        env_file_encoding = 'utf-8'
        case_sensitive = False


# Проверка наличия файла .env в tenant-папке (tenants/test_clinic/.env)
env_path = Path(__file__).resolve().parent / "tenants" / "test_clinic" / ".env"
if not env_path.exists():
    print("❌ ОШИБКА: Файл .env не найден в папке tenants/test_clinic/!")
    print(f"   Создайте файл .env на основе .env.example и поместите его в: {env_path.absolute()}")
    sys.exit(1)

# Инициализация настроек
try:
    settings = Settings()
except Exception as e:
    print(f"❌ ОШИБКА при загрузке конфигурации: {e}")
    sys.exit(1)

# Проверка наличия обязательных параметров
required_settings = [
    ("TELEGRAM_BOT_TOKEN", settings.TELEGRAM_BOT_TOKEN),
    ("YANDEX_FOLDER_ID", settings.YANDEX_FOLDER_ID),
]

for setting_name, setting_value in required_settings:
    if not setting_value or setting_value.strip() == "":
        print(f"❌ ОШИБКА: Переменная окружения '{setting_name}' не установлена или пуста!")
        print(f"   Проверьте файл .env в папке: {env_path.absolute()}")
        sys.exit(1)

# Валидация формата Telegram токена (должен быть в формате: цифры:буквы-символы)
if ":" not in settings.TELEGRAM_BOT_TOKEN:
    print("❌ ОШИБКА: TELEGRAM_BOT_TOKEN имеет неправильный формат!")
    print("   Формат должен быть: цифры:символы (например, 123456789:ABCdef...)")
    sys.exit(1)

ADMIN_CHAT_ID = settings.ADMIN_CHAT_ID

print("✅ Конфигурация загружена успешно")

# Проверка наличия service account ключа (SA_KEY_PATH), с fallback на корневой sa-key.json
sa_key_path = Path(settings.SA_KEY_PATH)
root_sa = Path(__file__).resolve().parent / "sa-key.json"
if not sa_key_path.exists():
    if root_sa.exists():
        print(f"⚠️ SA key not found at {sa_key_path}, using local {root_sa}")
        # переопределяем путь в рантайме
        try:
            settings.SA_KEY_PATH = str(root_sa)
        except Exception:
            pass
    else:
        print(f"❌ ОШИБКА: service account key not found at {sa_key_path} and no {root_sa} present.")
        print("   Поместите sa-key.json в указанный путь или смонтируйте его как Docker secret в /run/secrets/sa-key.json")
        sys.exit(1)
