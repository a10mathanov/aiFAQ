"""
Универсальные обработчики для высококонверсионной воронки записи.
Полностью отделены от конфигурации бизнеса.
"""

import logging
import re
import asyncio
import time
import difflib
from typing import Any, Dict, List, Optional

from aiogram import Bot, Router
from aiogram.filters import Command, StateFilter
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import settings

logger = logging.getLogger(__name__)

# ============================================================================
# ROUTER & GLOBAL STATE
# ============================================================================

router = Router()

KNOWLEDGE_BASE = ""
chat_histories: Dict[int, List[Dict[str, str]]] = {}
# active_reminders keeps the background reminder tasks per user (see requirements)
active_reminders: Dict[int, asyncio.Task] = {}
# In-memory bridge mappings for Human-in-the-loop (MVP)
user_to_thread: Dict[int, int] = {}
thread_to_user: Dict[int, int] = {}

# Throttling runtime state
_last_message_time: Dict[int, float] = {}
_throttle_warned: Dict[int, bool] = {}


def reset_runtime_state() -> None:
    """Очистить все runtime состояния бота при старте или перезапуске."""
    # Отменяем фоновые напоминания, если они есть.
    for task in list(active_reminders.values()):
        try:
            task.cancel()
        except Exception:
            pass

    chat_histories.clear()
    active_reminders.clear()
    user_to_thread.clear()
    thread_to_user.clear()
    _last_message_time.clear()
    _throttle_warned.clear()

# ============================================================================
# DYNAMIC CONFIG FROM SETTINGS
# ============================================================================

BUSINESS_NAME = settings.BUSINESS_NAME
BUSINESS_TYPE = settings.BUSINESS_TYPE
APPOINTMENT_TARGET = settings.APPOINTMENT_TARGET
LEAD_MAGNET = settings.LEAD_MAGNET
BUSINESS_PHONE = settings.BUSINESS_PHONE
ADMIN_CHAT_ID = settings.ADMIN_CHAT_ID
FSM_CATEGORIES = settings.FSM_CATEGORIES
MAX_CHAT_HISTORY = settings.MAX_CHAT_HISTORY
FSM_TIMEOUT_MINUTES = settings.FSM_TIMEOUT_MINUTES
VISIT_REMINDER_TEXT = settings.VISIT_REMINDER_TEXT

# Optional fallback admin chat
ADMIN_FALLBACK_CHAT_ID = getattr(settings, "ADMIN_FALLBACK_CHAT_ID", 0)

# Localized messages dictionary from config
MESSAGES = getattr(settings, "MESSAGES", {})

# Throttle limit seconds
THROTTLE_LIMIT = getattr(settings, "THROTTLE_LIMIT", 1.5)

# ============================================================================
# FSM STATES (Universal Appointment Flow)
# ============================================================================


class UniversalAppointment(StatesGroup):
    waiting_for_name = State()
    waiting_for_category = State()
    waiting_for_phone = State()
    waiting_for_time = State()
    chatting_with_admin = State()


# ============================================================================
# CONSTANTS & PATTERNS
# ============================================================================

FSM_BACK_CALLBACK = "fsm_back"
FSM_CANCEL_CALLBACK = "fsm_cancel"
CATEGORY_CALLBACK_PREFIX = "category_"

# Phone validation: 10 digits + optional +7/8/7 prefix
PHONE_PATTERN = re.compile(r"^(?:\+7|7|8)?\d{10}$")
REGISTRATION_KEYWORDS = ["запись", "записаться", "прием", "приём", "хочу к врачу", "хочу прийти"]
OPERATOR_KEYWORDS = ["оператор", "человека", "человека", "вызови", "позови", "позвать", "помощь", "связь с оператором", "запросил помощь", "говорить с человеком", "кто-то из администраторов", "созвон"]

# ============================================================================
# KEYBOARDS (Dynamic)
# ============================================================================


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Permanent Reply menu with appointment and operator buttons."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"📅 {APPOINTMENT_TARGET.capitalize()}")],
            [KeyboardButton(text="👤 Связь с оператором")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def build_name_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for name step: only Cancel button."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=FSM_CANCEL_CALLBACK)]
        ]
    )


def build_category_keyboard() -> InlineKeyboardMarkup:
    """Dynamically build category buttons from FSM_CATEGORIES."""
    buttons = []
    for idx, category in enumerate(FSM_CATEGORIES):
        callback_data = f"{CATEGORY_CALLBACK_PREFIX}{idx}"
        buttons.append([InlineKeyboardButton(text=category, callback_data=callback_data)])
    
    buttons.append(
        [
            InlineKeyboardButton(text="⬅️ Назад", callback_data=FSM_BACK_CALLBACK),
            InlineKeyboardButton(text="❌ Отменить", callback_data=FSM_CANCEL_CALLBACK),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_phone_time_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for phone & time steps: Back and Cancel."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=FSM_BACK_CALLBACK),
                InlineKeyboardButton(text="❌ Отменить", callback_data=FSM_CANCEL_CALLBACK),
            ]
        ]
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def normalize_phone(raw: str) -> Optional[str]:
    """Validate and normalize phone number to +7XXXXXXXXXX format."""
    if not raw or not isinstance(raw, str):
        return None

    digits = re.sub(r"[^0-9]", "", raw)
    
    # Normalize length
    if len(digits) == 11:
        if digits.startswith("8"):
            digits = "7" + digits[1:]
        elif not digits.startswith("7"):
            return None
    elif len(digits) == 10:
        digits = "7" + digits
    else:
        return None

    # Final validation
    if not PHONE_PATTERN.match(digits):
        return None

    # Prevent all-same-digit numbers (spam filter)
    if len(set(digits)) == 1:
        return None

    # Format to +7 (XXX) XXX-XX-XX
    if len(digits) == 11:
        core = digits[1:]
    else:
        core = digits[-10:]

    return f"+7 ({core[0:3]}) {core[3:6]}-{core[6:8]}-{core[8:10]}"


def extract_name_and_phone(text: str) -> Dict[str, Optional[str]]:
    """
    Parse text to extract name and phone.
    Returns dict: {'name': str or None, 'phone': str or None}
    """
    # Try to find phone number
    potential_phone_match = re.search(r"(\+?7|8)?[\s\-\(\)]?\d[\d\s\-\(\)]{8,}\d", text)
    
    if not potential_phone_match:
        return {"name": None, "phone": None}
    
    phone_start_pos = potential_phone_match.start()
    phone_end_pos = potential_phone_match.end()
    raw_phone = text[phone_start_pos:phone_end_pos]
    
    normalized_phone = normalize_phone(raw_phone)
    if not normalized_phone:
        return {"name": None, "phone": None}

    # Extract name from remaining text
    name_part = (text[:phone_start_pos] + text[phone_end_pos:]).strip()
    name_part = re.sub(r"\s+", " ", name_part)

    return {
        "name": name_part if name_part and len(name_part) >= 2 else None,
        "phone": normalized_phone,
    }


def is_registration_intent(text: str) -> bool:
    """Detect if user's message shows intent to book appointment."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in REGISTRATION_KEYWORDS)


def is_operator_intent(text: str) -> bool:
    """Detect if user's message requests a human/operator."""
    lowered = text.lower()
    return any(keyword in lowered for keyword in OPERATOR_KEYWORDS)


def append_chat_history(user_id: int, role: str, content: str) -> None:
    """Add message to user's chat history with max history limit."""
    history = chat_histories.setdefault(user_id, [])
    history.append({"role": role, "content": content})
    
    # Keep only last MAX_CHAT_HISTORY messages
    if len(history) > MAX_CHAT_HISTORY:
        del history[:-MAX_CHAT_HISTORY]


async def throttle_check(message: Message) -> bool:
    """Return True if message is allowed, False if throttled.
    Warns the user once when throttled using messages from config.
    """
    user_id = message.from_user.id
    now = time.time()
    last = _last_message_time.get(user_id, 0)
    if now - last < THROTTLE_LIMIT:
        if not _throttle_warned.get(user_id, False):
            try:
                warn = MESSAGES.get("throttle_warning", "Пожалуйста, не спамьте.")
                await message.answer(warn)
            except Exception:
                pass
            _throttle_warned[user_id] = True
        return False

    _last_message_time[user_id] = now
    _throttle_warned[user_id] = False
    return True


def build_llm_messages(user_id: int, user_text: str) -> List[Dict[str, str]]:
    """Build message list for LLM with system prompt and history."""
    history = chat_histories.get(user_id, [])
    
    system_prompt = (
        f"Ты — высококлассный виртуальный администратор компании '{BUSINESS_NAME}' (сфера: {BUSINESS_TYPE}). "
        f"Твоя цель — проявлять максимальную эмпатию, отвечать на вопросы клиента строго по фактам из предоставленной "
        f"базы знаний: {KNOWLEDGE_BASE}. Закрывай страхи клиента и мягко подводи его к записи {APPOINTMENT_TARGET}. "
        f"Если ответ в базе нет, вежливо объясни, что лучше уточнить у человека, и предложи нажать кнопку записи."
    )
    
    messages = [{"role": "system", "text": system_prompt}]
    messages.extend(history[-MAX_CHAT_HISTORY:])
    messages.append({"role": "user", "text": user_text})
    
    return messages


def clear_chat_history(user_id: int) -> None:
    """Clear user's chat history."""
    if user_id in chat_histories:
        del chat_histories[user_id]


def cancel_abandoned_reminder(user_id: int) -> None:
    """Cancel background reminder task for user."""
    task = active_reminders.get(user_id)
    if task and not task.done():
        task.cancel()
    active_reminders.pop(user_id, None)


async def send_fsm_message(message: Message, text: str, keyboard: InlineKeyboardMarkup) -> None:
    """Send message with inline keyboard (FSM step prompt)."""
    await message.answer(text, reply_markup=keyboard)


def normalize_supergroup_chat_id(chat_id: int) -> int:
    """Convert a legacy group chat id to the equivalent supergroup id if needed."""
    text_id = str(chat_id)
    if text_id.startswith("-100"):
        return chat_id
    if text_id.startswith("-"):
        return int(f"-100{abs(chat_id)}")
    return chat_id


async def resolve_admin_chat_id(bot: Bot) -> Optional[int]:
    """Resolve current admin chat id, handling legacy group -> supergroup migration."""
    global ADMIN_CHAT_ID
    normalized_id = normalize_supergroup_chat_id(ADMIN_CHAT_ID)
    if normalized_id != ADMIN_CHAT_ID:
        ADMIN_CHAT_ID = normalized_id
        try:
            setattr(settings, "ADMIN_CHAT_ID", normalized_id)
        except Exception:
            pass
    try:
        chat = await bot.get_chat(ADMIN_CHAT_ID)
        new_id = getattr(chat, "id", None)
        if new_id and new_id != ADMIN_CHAT_ID:
            logger.info(f"Resolved migrated admin chat id: {ADMIN_CHAT_ID} -> {new_id}")
            ADMIN_CHAT_ID = new_id
            try:
                setattr(settings, "ADMIN_CHAT_ID", new_id)
            except Exception:
                pass
        return ADMIN_CHAT_ID
    except Exception as exc:
        logger.error(f"Failed to resolve admin chat id for {ADMIN_CHAT_ID}: {exc}")
        return None


async def get_effective_admin_chat_id(bot: Bot) -> Optional[int]:
    """Return a usable admin chat id, resolving migrated id or falling back when needed."""
    resolved_id = await resolve_admin_chat_id(bot)
    if resolved_id:
        return resolved_id
    if ADMIN_FALLBACK_CHAT_ID:
        logger.warning(f"Using fallback admin chat id {ADMIN_FALLBACK_CHAT_ID} because primary admin chat id {ADMIN_CHAT_ID} is unavailable")
        return ADMIN_FALLBACK_CHAT_ID
    return None


async def send_admin_notification(bot: Bot, text: str) -> bool:
    """Send structured notification to admin chat."""
    if ADMIN_CHAT_ID == 0 and ADMIN_FALLBACK_CHAT_ID == 0:
        logger.warning("No admin chat configured, notification not sent")
        return False

    try:
        await bot.send_message(chat_id=ADMIN_CHAT_ID, text=text, parse_mode="Markdown")
        logger.info(f"Admin notification sent to {ADMIN_CHAT_ID}")
        return True
    except Exception as exc:
        msg = str(exc).lower()
        logger.error(f"Failed to notify admin {ADMIN_CHAT_ID}: {exc}")

        if "upgraded to a supergroup" in msg or "group chat was upgraded" in msg or "chat not found" in msg:
            new_admin_chat_id = await get_effective_admin_chat_id(bot)
            if new_admin_chat_id and new_admin_chat_id != ADMIN_CHAT_ID:
                try:
                    await bot.send_message(chat_id=new_admin_chat_id, text=text, parse_mode="Markdown")
                    logger.info(f"Admin notification sent to migrated/fallback chat {new_admin_chat_id}")
                    return True
                except Exception as exc2:
                    logger.error(f"Retry to migrated/fallback admin chat {new_admin_chat_id} failed: {exc2}")

        if ADMIN_FALLBACK_CHAT_ID and ADMIN_FALLBACK_CHAT_ID != ADMIN_CHAT_ID:
            try:
                await bot.send_message(chat_id=ADMIN_FALLBACK_CHAT_ID, text=text, parse_mode="Markdown")
                logger.info(f"Admin notification sent to fallback admin {ADMIN_FALLBACK_CHAT_ID}")
                return True
            except Exception as exc2:
                logger.error(f"Fallback admin notification failed: {exc2}")

        return False


async def start_admin_topic_for_user(user_id: int, user_name: str, bot: Bot) -> Optional[int]:
    """Create or return existing forum topic for a user in ADMIN_CHAT_ID.
    Returns message_thread_id or None on failure.
    """
    # Reuse existing mapping if present
    existing = user_to_thread.get(user_id)
    if existing:
        return existing

    if ADMIN_CHAT_ID == 0:
        logger.error("ADMIN_CHAT_ID not configured, cannot create admin topic")
        await send_admin_notification(
            bot,
            f"⚠️ Не удалось создать форумную тему для клиента {user_name} (user_id={user_id}). Админ-чат не настроен."
        )
        return None

    try:
        # Create forum topic (requires bot to have appropriate rights)
        topic = await bot.create_forum_topic(chat_id=ADMIN_CHAT_ID, name=f"Пациент: {user_name}")
        # topic may be ForumTopic or dict-like; try common attributes
        thread_id = None
        if hasattr(topic, "message_thread_id"):
            thread_id = getattr(topic, "message_thread_id")
        elif isinstance(topic, dict):
            thread_id = topic.get("message_thread_id")

        if not thread_id:
            fallback_text = (
                f"⚠️ Не удалось получить message_thread_id для клиента {user_name} (user_id={user_id}). "
                "Уведомление отправлено администраторам."
            )
            logger.error(f"Failed to obtain message_thread_id from create_forum_topic response: {topic}")
            await send_admin_notification(bot, fallback_text)
            return None

        user_to_thread[user_id] = thread_id
        thread_to_user[thread_id] = user_id

        # Send starter message into the topic with recent history
        last_history = chat_histories.get(user_id, [])
        history_text = "\n".join([f"[{m['role']}] {m['content']}" for m in last_history[-10:]]) or "(нет истории)"
        start_text = f"Пациент {user_name} подключен. Последняя история диалога с ИИ:\n\n{history_text}"
        await bot.send_message(chat_id=ADMIN_CHAT_ID, message_thread_id=thread_id, text=start_text)

        # Also copy last messages individually for richer context
        for m in last_history[-10:]:
            try:
                # send as plain message into the topic
                await bot.send_message(chat_id=ADMIN_CHAT_ID, message_thread_id=thread_id, text=f"[{m['role']}] {m['content']}")
            except Exception:
                pass

        logger.info(f"Created forum topic {thread_id} for user {user_id}")
        return thread_id
    except Exception as exc:
        msg = str(exc)
        logger.error(f"Failed to create forum topic for user {user_id}: {exc}")

        if "upgraded to a supergroup" in msg or "group chat was upgraded" in msg:
            old_admin_chat_id = ADMIN_CHAT_ID
            new_admin_chat_id = await resolve_admin_chat_id(bot)
            if new_admin_chat_id and new_admin_chat_id != old_admin_chat_id:
                logger.info(f"Retrying topic creation with migrated admin chat id {new_admin_chat_id}")
                try:
                    topic = await bot.create_forum_topic(chat_id=new_admin_chat_id, name=f"Пациент: {user_name}")
                    thread_id = None
                    if hasattr(topic, "message_thread_id"):
                        thread_id = getattr(topic, "message_thread_id")
                    elif isinstance(topic, dict):
                        thread_id = topic.get("message_thread_id")

                    if thread_id:
                        user_to_thread[user_id] = thread_id
                        thread_to_user[thread_id] = user_id
                        try:
                            setattr(settings, "ADMIN_CHAT_ID", new_admin_chat_id)
                        except Exception:
                            pass
                        # send starter messages
                        last_history = chat_histories.get(user_id, [])
                        history_text = "\n".join([f"[{m['role']}] {m['content']}" for m in last_history[-10:]]) or "(нет истории)"
                        start_text = f"Пациент {user_name} подключен. Последняя история диалога с ИИ:\n\n{history_text}"
                        await bot.send_message(chat_id=new_admin_chat_id, message_thread_id=thread_id, text=start_text)
                        for m in last_history[-10:]:
                            try:
                                await bot.send_message(chat_id=new_admin_chat_id, message_thread_id=thread_id, text=f"[{m['role']}] {m['content']}")
                            except Exception:
                                pass
                        logger.info(f"Created forum topic {thread_id} for user {user_id} in migrated chat {new_admin_chat_id}")
                        return thread_id
                except Exception as exc2:
                    logger.error(f"Retry create_forum_topic in migrated chat failed: {exc2}")

        # On any failure to create a topic, send a fallback admin notification.
        fallback_text = (
            f"⚠️ Не удалось создать форумную тему для клиента {user_name} (user_id={user_id}). "
            f"Ошибка: {msg}"
        )
        await send_admin_notification(bot, fallback_text)

        return None


async def send_abandoned_reminder(
    user_id: int,
    state: FSMContext,
    bot: Bot,
    user_name: str = "Клиент",
) -> None:
    """
    Background task: send reminder about abandoned appointment form.
    Checks after FSM_TIMEOUT_MINUTES if user didn't complete registration.
    """
    try:
        await asyncio.sleep(FSM_TIMEOUT_MINUTES * 60)
        
        current_state = await state.get_state()
        # If still in FSM, send reminder
        if current_state and "UniversalAppointment" in current_state:
            try:
                reminder_text = (
                    f"👋 {user_name}, вы начали оформление {APPOINTMENT_TARGET} в '{BUSINESS_NAME}', "
                    f"но не завершили его. Ваш бонус '{LEAD_MAGNET}' сгорит через 2 часа. "
                    f"Нажмите кнопку меню, чтобы завершить бронирование!"
                )
                await bot.send_message(
                    chat_id=user_id,
                    text=reminder_text,
                    reply_markup=get_main_keyboard(),
                )
                logger.info(f"Abandoned reminder sent to user {user_id}")
            except Exception as exc:
                logger.error(f"Failed to send abandoned reminder to {user_id}: {exc}")
        else:
            logger.info(f"User {user_id} completed or cancelled, skipping reminder")
    except asyncio.CancelledError:
        logger.debug(f"Abandoned reminder cancelled for user {user_id}")
    except Exception as exc:
        logger.error(f"Unexpected error in abandoned reminder for user {user_id}: {exc}")


async def start_registration(message: Message, state: FSMContext) -> None:
    """Start the universal appointment FSM flow."""
    await state.clear()
    clear_chat_history(message.from_user.id)
    cancel_abandoned_reminder(message.from_user.id)

    await state.set_state(UniversalAppointment.waiting_for_name)
    prompt = MESSAGES.get("prompt_name", "Отлично! Давайте оформим предварительную заявку. Как к вам обращаться? Введите ваше имя:")
    prompt = prompt.format(APPOINTMENT_TARGET=APPOINTMENT_TARGET)
    await send_fsm_message(message, prompt, build_name_keyboard())

    # Cancel any existing active reminder and start a fresh one
    if message.from_user.id in active_reminders:
        try:
            active_reminders[message.from_user.id].cancel()
        except Exception:
            pass

    task = asyncio.create_task(
        send_abandoned_reminder(message.from_user.id, state, message.bot, "Клиент")
    )
    active_reminders[message.from_user.id] = task
    
    logger.info(f"User {message.from_user.id} started appointment registration")


async def request_operator(message: Message, state: FSMContext) -> None:
    """Handle a natural-language operator request by creating a group topic."""
    await state.clear()
    cancel_abandoned_reminder(message.from_user.id)

    username = message.from_user.username or "не указан"
    thread_id = await start_admin_topic_for_user(message.from_user.id, username, message.bot)
    if thread_id:
        try:
            await state.set_state(UniversalAppointment.chatting_with_admin)
        except Exception:
            pass

        await message.answer(MESSAGES.get("operator_called", "📞 Вызываю оператора. Менеджер подключится в этот чат в течение 5 минут."), reply_markup=get_main_keyboard())
        logger.info(f"User {message.from_user.id} requested operator in natural language and joined thread {thread_id}")
    else:
        operator_text = MESSAGES.get("operator_called", "📞 Вызываю оператора. Менеджер подключится в этот чат в течение 5 минут.")
        operator_text = operator_text.replace("{BUSINESS_PHONE}", BUSINESS_PHONE)
        await message.answer(operator_text, reply_markup=get_main_keyboard())

        admin_text = f"⚠️ **Пользователь @{username} запросил помощь оператора!**"
        await send_admin_notification(message.bot, admin_text)
        logger.info(f"User {message.from_user.id} requested operator via NL intent (fallback notify)")


# ============================================================================
# HANDLERS: MAIN COMMANDS
# ============================================================================


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    """Start command: show welcome with lead magnet."""
    await state.clear()
    clear_chat_history(message.from_user.id)
    cancel_abandoned_reminder(message.from_user.id)

    welcome_text = MESSAGES.get("welcome_text", "🎉 Рады видеть вас!")
    welcome_text = welcome_text.format(LEAD_MAGNET=LEAD_MAGNET)
    await message.answer(welcome_text, reply_markup=get_main_keyboard())
    logger.info(f"User {message.from_user.id} started bot")


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    """Help command."""
    help_text = MESSAGES.get("help_text", "ℹ️ Справка по боту")
    help_text = help_text.format(BUSINESS_NAME=BUSINESS_NAME, APPOINTMENT_TARGET=APPOINTMENT_TARGET)
    help_text = help_text.replace("{BUSINESS_HOURS}", settings.BUSINESS_HOURS).replace("{BUSINESS_PHONE}", BUSINESS_PHONE)
    await message.answer(help_text, reply_markup=get_main_keyboard())
    logger.info(f"User {message.from_user.id} requested help")


# ============================================================================
# HANDLERS: AI CHAT (StateFilter None)
# ============================================================================


@router.message(
    lambda msg: msg.text not in [f"📅 {APPOINTMENT_TARGET.capitalize()}", "👤 Связь с оператором"],
    StateFilter(None),
)
async def handle_ai_chat(message: Message, state: FSMContext) -> None:
    """
    Handle user messages in normal chat (no FSM).
    - Detect registration intent and start FSM
    - Otherwise send to LLM with knowledge base context
    """
    user_id = message.from_user.id
    user_text = message.text.strip() if message.text else ""

    if not user_text:
        await message.answer(MESSAGES.get("empty_message", "Пожалуйста, отправьте непустое сообщение."))
        return

    # Throttle check
    ok = await throttle_check(message)
    if not ok:
        return

    # Check for operator request intent
    if is_operator_intent(user_text):
        await request_operator(message, state)
        return

    # Check for registration intent
    if is_registration_intent(user_text):
        await start_registration(message, state)
        return

    # Check message length
    if len(user_text) > settings.MAX_MESSAGE_LENGTH:
        await message.answer(MESSAGES.get("too_long_message", "Сообщение слишком длинное.").format(MAX_MESSAGE_LENGTH=settings.MAX_MESSAGE_LENGTH))
        logger.warning(f"User {user_id} message too long: {len(user_text)}")
        return

    # Show typing indicator
    try:
        await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    except Exception:
        pass

    # Import LLM service
    from services.yandex_gpt import YandexGPTService
    gpt_service = YandexGPTService(
        folder_id=settings.YANDEX_FOLDER_ID,
        sa_key_path=settings.SA_KEY_PATH,
        model=settings.YANDEX_GPT_MODEL,
        api_url=settings.YANDEX_GPT_API_URL,
        timeout=settings.REQUEST_TIMEOUT,
    )

    messages = build_llm_messages(user_id, user_text)
    logger.info(f"User {user_id} sent message to LLM ({len(messages)} in context)")

    try:
        response = await gpt_service.get_response(messages=messages)
        
        if response:
            append_chat_history(user_id, "user", user_text)
            append_chat_history(user_id, "assistant", response)

            if len(response) > settings.MAX_MESSAGE_LENGTH:
                response = response[: settings.MAX_MESSAGE_LENGTH - 3] + "..."

            await message.answer(response, reply_markup=get_main_keyboard())
            logger.info(f"LLM response sent to user {user_id}")
        else:
            await message.answer(MESSAGES.get("llm_error", "Не удалось получить ответ от LLM."), reply_markup=get_main_keyboard())
            logger.error(f"LLM returned empty response for user {user_id}")
    except Exception as e:
        logger.error(f"LLM error for user {user_id}: {e}")
        await message.answer(MESSAGES.get("llm_error", "Произошла ошибка. Пожалуйста, попробуйте позже."), reply_markup=get_main_keyboard())


# ============================================================================
# HANDLERS: FSM - APPOINTMENT FLOW
# ============================================================================


@router.message(Command("register"))
async def cmd_register(message: Message, state: FSMContext) -> None:
    """Explicit /register command."""
    await start_registration(message, state)


@router.message(lambda msg: msg.text and f"📅 {APPOINTMENT_TARGET.capitalize()}" in msg.text)
async def button_start_appointment(message: Message, state: FSMContext) -> None:
    """Button handler: start appointment from main menu."""
    await start_registration(message, state)


@router.message(UniversalAppointment.waiting_for_name)
async def process_name(message: Message, state: FSMContext) -> None:
    """FSM Step 1: Process name input. Tries to extract phone too."""
    raw_text = message.text.strip() if message.text else ""

    # Clean name: remove non-letter characters and digits, keep spaces and hyphens
    clean = re.sub(r"[^\w\sА-Яа-я\-]", "", raw_text)
    clean = re.sub(r"\d", "", clean).strip().title()

    if not clean or len(clean) < 2:
        await message.answer(MESSAGES.get("invalid_name", "Пожалуйста, введите корректное имя (минимум 2 символа)."))
        return

    if len(clean) > 100:
        await message.answer("Имя слишком длинное. Используйте более короткое имя.")
        return

    # Try to extract both name and phone from input
    extracted = extract_name_and_phone(raw_text)

    if extracted["name"] and extracted["phone"]:
        # User provided both name and phone in one message
        await state.update_data(name=extracted["name"], phone=extracted["phone"])
        await state.set_state(UniversalAppointment.waiting_for_time)
        time_prompt = MESSAGES.get("prompt_time", "Отлично! Теперь выберите удобное время визита.")
        await send_fsm_message(message, time_prompt, build_phone_time_keyboard())
        logger.info(f"User {message.from_user.id} provided name+phone, skipped category & phone steps")
        return

    # Only name provided, move to category selection
    await state.update_data(name=clean)
    await state.set_state(UniversalAppointment.waiting_for_category)
    await send_fsm_message(message, MESSAGES.get("prompt_select_category", "Спасибо! Теперь выберите категорию."), build_category_keyboard())
    logger.info(f"User {message.from_user.id} provided name: {clean}")


@router.message(UniversalAppointment.waiting_for_category)
async def process_category_text(message: Message, state: FSMContext) -> None:
    """Handle free-text category input by fuzzy-matching against available categories."""
    text = (message.text or "").strip()
    if not text:
        await message.answer(MESSAGES.get("prompt_select_category", "Пожалуйста, выберите категорию."))
        return

    # Throttle check for safety
    ok = await throttle_check(message)
    if not ok:
        return

    # Fuzzy match
    choices = FSM_CATEGORIES
    lowered_choices = [c.lower() for c in choices]
    match = difflib.get_close_matches(text.lower(), lowered_choices, n=1, cutoff=0.4)
    if match:
        idx = lowered_choices.index(match[0])
        selected = choices[idx]
        await state.update_data(category=selected)
        await state.set_state(UniversalAppointment.waiting_for_phone)
        await send_fsm_message(message, MESSAGES.get("prompt_phone", "Введите номер телефона."), build_phone_time_keyboard())
        logger.info(f"User {message.from_user.id} matched category by text: {selected}")
        return

    # No good match — ask to use buttons
    await message.answer(MESSAGES.get("prompt_select_category", "Пожалуйста, выберите категорию кнопкой."), reply_markup=build_category_keyboard())


@router.callback_query(lambda query: query.data.startswith(CATEGORY_CALLBACK_PREFIX))
async def callback_select_category(callback_query: CallbackQuery, state: FSMContext) -> None:
    """FSM Step 2: Category selection via inline button."""
    try:
        idx = int(callback_query.data.replace(CATEGORY_CALLBACK_PREFIX, ""))
        if idx < 0 or idx >= len(FSM_CATEGORIES):
            await callback_query.answer("❌ Неверная категория", show_alert=True)
            return

        selected_category = FSM_CATEGORIES[idx]
    except (ValueError, IndexError):
        await callback_query.answer("❌ Ошибка обработки выбора", show_alert=True)
        return

    await state.update_data(category=selected_category)
    await state.set_state(UniversalAppointment.waiting_for_phone)

    try:
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    phone_prompt = MESSAGES.get("prompt_phone", "📞 Пожалуйста, укажите номер телефона для связи (например, +79991234567):")
    await send_fsm_message(callback_query.message, phone_prompt, build_phone_time_keyboard())
    await callback_query.answer()
    logger.info(f"User {callback_query.from_user.id} selected category: {selected_category}")


@router.message(UniversalAppointment.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext) -> None:
    """FSM Step 3: Phone validation."""
    phone_text = message.text.strip() if message.text else ""
    normalized_phone = normalize_phone(phone_text)

    if not normalized_phone:
        await message.answer(MESSAGES.get("invalid_phone", "Номер некорректен. Пожалуйста, введите корректный номер."))
        return

    await state.update_data(phone=normalized_phone)
    await state.set_state(UniversalAppointment.waiting_for_time)
    time_prompt = MESSAGES.get("prompt_time", "И последнее: в какой день и время вам удобно прийти?")
    await send_fsm_message(message, time_prompt, build_phone_time_keyboard())
    logger.info(f"User {message.from_user.id} provided phone: {normalized_phone}")


@router.message(UniversalAppointment.waiting_for_time)
async def process_time(message: Message, state: FSMContext, bot: Bot) -> None:
    """FSM Step 4: Time confirmation and lead submission."""
    time_text = message.text.strip() if message.text else ""

    if not time_text:
        await message.answer("Пожалуйста, укажите удобное время для визита.")
        return

    await state.update_data(time=time_text)
    user_data = await state.get_data()

    # Extract collected data
    name = user_data.get("name", "Не указано")
    category = user_data.get("category", "Не указано")
    phone = user_data.get("phone", "Не указан")
    time_value = user_data.get("time", "Не указано")
    username = message.from_user.username or "не указан"

    # Format lead notification for admin
    admin_text = (
        f"🔥 **Новая заявка из Telegram-бота ({BUSINESS_NAME})**\n\n"
        f"👤 **Клиент:** {name}\n"
        f"🎯 **Категория/Цель:** {category}\n"
        f"📞 **Телефон:** {phone}\n"
        f"⏰ **Удобное время:** {time_value}\n"
        f"🔗 **Аккаунт:** @{username}"
    )
    # Send to admin with fail-safe behavior
    try:
        success = await send_admin_notification(bot, admin_text)
    except Exception as exc:
        logger.error(f"Critical failure sending admin notification: {exc}")
        success = False

    # Cancel reminder task
    cancel_abandoned_reminder(message.from_user.id)

    if success:
        await message.answer(MESSAGES.get("registration_confirmed", "Заявка отправлена."), reply_markup=get_main_keyboard())
        await message.answer(MESSAGES.get("visit_reminder_text", VISIT_REMINDER_TEXT))
        logger.info(f"New lead submitted: name={name}, category={category}, phone={phone}, time={time_value}")
    else:
        logger.error(f"Failed to notify admin for user {message.from_user.id}")
        # Try fallback admin
        if ADMIN_FALLBACK_CHAT_ID:
            try:
                await bot.send_message(chat_id=ADMIN_FALLBACK_CHAT_ID, text=admin_text, parse_mode="Markdown")
                logger.info(f"Lead duplicated to fallback admin {ADMIN_FALLBACK_CHAT_ID}")
                await message.answer(MESSAGES.get("registration_confirmed", "Заявка отправлена."), reply_markup=get_main_keyboard())
                await message.answer(MESSAGES.get("visit_reminder_text", VISIT_REMINDER_TEXT))
            except Exception as exc:
                logger.error(f"Failed to notify fallback admin: {exc}")
                await message.answer(MESSAGES.get("registration_fallback", "Ваша заявка принята, но уведомление администраторам не отправилось.").format(BUSINESS_PHONE=BUSINESS_PHONE), reply_markup=get_main_keyboard())
        else:
            await message.answer(MESSAGES.get("registration_fallback", "Ваша заявка принята, но уведомление администраторам не отправилось.").format(BUSINESS_PHONE=BUSINESS_PHONE), reply_markup=get_main_keyboard())

    await state.clear()


# ============================================================================
# HANDLERS: FSM NAVIGATION
# ============================================================================


@router.callback_query(lambda query: query.data == FSM_CANCEL_CALLBACK)
async def callback_cancel(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Cancel FSM and return to main menu."""
    await state.clear()
    clear_chat_history(callback_query.from_user.id)
    cancel_abandoned_reminder(callback_query.from_user.id)

    try:
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    await callback_query.message.answer(MESSAGES.get("cancelled", "Запись отменена."), reply_markup=get_main_keyboard())
    await callback_query.answer()
    logger.info(f"User {callback_query.from_user.id} cancelled registration")


@router.callback_query(lambda query: query.data == FSM_BACK_CALLBACK)
async def callback_back(callback_query: CallbackQuery, state: FSMContext) -> None:
    """Navigate back to previous FSM step."""
    current_state = await state.get_state()

    try:
        await callback_query.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass

    if current_state == UniversalAppointment.waiting_for_time:
        await state.set_state(UniversalAppointment.waiting_for_phone)
        await send_fsm_message(
            callback_query.message,
            "Вернёмся назад. Введите номер телефона:",
            build_phone_time_keyboard(),
        )
    elif current_state == UniversalAppointment.waiting_for_phone:
        await state.set_state(UniversalAppointment.waiting_for_category)
        await send_fsm_message(
            callback_query.message,
            "Вернёмся назад. Выберите категорию:",
            build_category_keyboard(),
        )
    elif current_state == UniversalAppointment.waiting_for_category:
        await state.set_state(UniversalAppointment.waiting_for_name)
        await send_fsm_message(
            callback_query.message,
            "Вернёмся назад. Введите ваше имя:",
            build_name_keyboard(),
        )
    else:
        await state.clear()
        await callback_query.message.answer(
            "Запись отменена.",
            reply_markup=get_main_keyboard(),
        )

    await callback_query.answer()


# ============================================================================
# HANDLERS: OPERATOR REQUEST
# ============================================================================


@router.message(Command("operator"))
async def cmd_operator(message: Message, state: FSMContext, bot: Bot) -> None:
    """Explicit /operator command."""
    await state.clear()
    cancel_abandoned_reminder(message.from_user.id)

    username = message.from_user.username or "не указан"

    # Try to create or reuse a forum topic and set user state to chatting_with_admin
    thread_id = await start_admin_topic_for_user(message.from_user.id, username, message.bot)
    if thread_id:
        try:
            await state.set_state(UniversalAppointment.chatting_with_admin)
        except Exception:
            pass

        await message.answer(MESSAGES.get("operator_called", "📞 Вызываю оператора. Менеджер подключится в этот чат в течение 5 минут."), reply_markup=get_main_keyboard())
        logger.info(f"User {message.from_user.id} connected to admins in thread {thread_id}")
    else:
        # Fallback: simply notify admins (without a topic)
        operator_text = MESSAGES.get("operator_called", "📞 Вызываю оператора. Менеджер подключится в этот чат в течение 5 минут.")
        operator_text = operator_text.replace("{BUSINESS_PHONE}", BUSINESS_PHONE)
        await message.answer(operator_text, reply_markup=get_main_keyboard())

        admin_text = f"⚠️ **Пользователь @{username} запросил помощь оператора!**"
        await send_admin_notification(bot, admin_text)
        logger.info(f"User {message.from_user.id} requested operator (fallback notify)")


@router.message(lambda msg: msg.text and "👤 Связь с оператором" in msg.text)
async def button_operator(message: Message, state: FSMContext, bot: Bot) -> None:
    """Button handler: request operator from main menu."""
    await state.clear()
    cancel_abandoned_reminder(message.from_user.id)

    username = message.from_user.username or "не указан"

    thread_id = await start_admin_topic_for_user(message.from_user.id, username, message.bot)
    if thread_id:
        try:
            await state.set_state(UniversalAppointment.chatting_with_admin)
        except Exception:
            pass
        await message.answer(MESSAGES.get("operator_called", "📞 Вызываю оператора. Менеджер подключится в этот чат в течение 5 минут."), reply_markup=get_main_keyboard())
        logger.info(f"User {message.from_user.id} connected to admins in thread {thread_id} via button")
    else:
        operator_text = MESSAGES.get("operator_called", "📞 Вызываю оператора. Менеджер подключится в этот чат в течение 5 минут.")
        operator_text = operator_text.replace("{BUSINESS_PHONE}", BUSINESS_PHONE)
        await message.answer(operator_text, reply_markup=get_main_keyboard())
        admin_text = f"⚠️ **Пользователь @{username} запросил помощь оператора!**"
        await send_admin_notification(bot, admin_text)
        logger.info(f"User {message.from_user.id} requested operator via button (fallback notify)")


@router.message(UniversalAppointment.chatting_with_admin)
async def user_message_to_admin(message: Message, state: FSMContext) -> None:
    """Forward any user messages while in chatting_with_admin to the admin forum topic."""
    user_id = message.from_user.id
    thread_id = user_to_thread.get(user_id)
    if not thread_id:
        # Try to create a topic on the fly
        username = message.from_user.username or (message.from_user.first_name or "Клиент")
        thread_id = await start_admin_topic_for_user(user_id, username, message.bot)
        if thread_id:
            try:
                await state.set_state(UniversalAppointment.chatting_with_admin)
            except Exception:
                pass

    if not thread_id:
        await message.answer("❌ Не удалось подключить оператора. Попробуйте позже.")
        return

    try:
        await message.send_copy(chat_id=ADMIN_CHAT_ID, message_thread_id=thread_id)
        logger.info(f"Forwarded user {user_id} message to admin thread {thread_id}")
    except Exception as exc:
        logger.error(f"Failed to forward user message to admin thread: {exc}")
        await message.answer(MESSAGES.get("llm_error", "Произошла ошибка. Пожалуйста, попробуйте позже."))


@router.message(lambda msg: msg.chat.id == ADMIN_CHAT_ID and msg.message_thread_id is not None)
async def admin_topic_message(message: Message, bot: Bot) -> None:
    """Handle messages posted by admins inside forum topics and forward them back to corresponding user."""
    thread_id = message.message_thread_id
    user_id = thread_to_user.get(thread_id)
    if not user_id:
        # Unknown thread — ignore
        return

    text = (message.text or "").strip()
    # Admin command to close dialog
    if text.startswith("/close"):
        # Remove mappings
        user_to_thread.pop(user_id, None)
        thread_to_user.pop(thread_id, None)

        # Try to reset FSM state for the user if dispatcher is available
        try:
            from main import dp
            try:
                await dp.storage.reset_state(chat=user_id, user=user_id)
                await dp.storage.reset_data(chat=user_id, user=user_id)
            except Exception:
                pass
        except Exception:
            pass

        try:
            await bot.send_message(chat_id=user_id, text="Диалог с администратором завершен")
        except Exception:
            pass

        # Close the forum topic (best-effort)
        try:
            await bot.close_forum_topic(chat_id=ADMIN_CHAT_ID, message_thread_id=thread_id)
        except Exception:
            pass

        # Notify admins in the thread
        try:
            await message.reply("Тема закрыта и пользователь уведомлен.")
        except Exception:
            pass

        logger.info(f"Admin closed thread {thread_id} for user {user_id}")
        return

    # Ignore admin bot commands or system messages
    if text.startswith("/"):
        return

    # Forward/copy the admin's message to the user
    try:
        await message.send_copy(chat_id=user_id)
        logger.info(f"Forwarded admin message from thread {thread_id} to user {user_id}")
    except Exception as exc:
        logger.error(f"Failed to forward admin message to user {user_id}: {exc}")
