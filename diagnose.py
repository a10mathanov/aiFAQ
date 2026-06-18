"""
Скрипт для диагностики сетевых проблем с Telegram и YandexGPT API
"""

import asyncio
import aiohttp
import socket
from datetime import datetime


async def check_internet_connection():
    """Проверить базовое интернет соединение"""
    print("\n🔍 Проверка интернет соединения...")
    try:
        # Пытаемся разрешить DNS для google.com
        socket.gethostbyname("google.com")
        print("   ✅ DNS работает (может разрешить google.com)")
    except socket.gaierror:
        print("   ❌ DNS не работает - нет подключения к интернету!")
        return False
    
    return True


async def check_telegram_api():
    """Проверить доступность Telegram API"""
    print("\n🔍 Проверка доступности Telegram API (api.telegram.org)...")
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("https://api.telegram.org/bot/getMe", ssl=False) as resp:
                if resp.status == 401:  # Ожидаемая ошибка (нет токена)
                    print("   ✅ Telegram API доступен")
                    return True
                else:
                    print(f"   ⚠️ Telegram API ответил статусом {resp.status}")
                    return True
    except asyncio.TimeoutError:
        print("   ❌ Timeout - Telegram API не отвечает")
        return False
    except aiohttp.ClientConnectorError as e:
        print(f"   ❌ Не могу подключиться к Telegram API: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка при проверке Telegram API: {e}")
        return False


async def check_yandex_gpt_api():
    """Проверить доступность YandexGPT API"""
    print("\n🔍 Проверка доступности YandexGPT API (llm.api.cloud.yandex.net)...")
    try:
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get("https://llm.api.cloud.yandex.net/", ssl=False) as resp:
                if resp.status in [404, 405]:  # Ожидаемые ошибки (путь не существует)
                    print("   ✅ YandexGPT API доступен")
                    return True
                else:
                    print(f"   ⚠️ YandexGPT API ответил статусом {resp.status}")
                    return True
    except asyncio.TimeoutError:
        print("   ❌ Timeout - YandexGPT API не отвечает")
        return False
    except aiohttp.ClientConnectorError as e:
        print(f"   ❌ Не могу подключиться к YandexGPT API: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Ошибка при проверке YandexGPT API: {e}")
        return False


async def check_dns():
    """Проверить разрешение доменов"""
    print("\n🔍 Проверка DNS разрешения...")
    domains = [
        ("api.telegram.org", "Telegram API"),
        ("llm.api.cloud.yandex.net", "YandexGPT API"),
        ("google.com", "Google (проверка интернета)"),
    ]
    
    all_ok = True
    for domain, name in domains:
        try:
            ip = socket.gethostbyname(domain)
            print(f"   ✅ {name}: {domain} -> {ip}")
        except socket.gaierror:
            print(f"   ❌ {name}: Не удалось разрешить {domain}")
            all_ok = False
    
    return all_ok


async def main():
    """Основная функция диагностики"""
    print("=" * 60)
    print("🔧 ДИАГНОСТИКА СЕТЕВОГО СОЕДИНЕНИЯ")
    print("=" * 60)
    print(f"Время запуска: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Выполнить проверки
    internet_ok = await check_internet_connection()
    dns_ok = await check_dns()
    telegram_ok = await check_telegram_api()
    yandex_ok = await check_yandex_gpt_api()
    
    # Вывести результаты
    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ:")
    print("=" * 60)
    print(f"Интернет соединение:     {'✅' if internet_ok else '❌'}")
    print(f"DNS разрешение:          {'✅' if dns_ok else '❌'}")
    print(f"Telegram API:            {'✅' if telegram_ok else '❌'}")
    print(f"YandexGPT API:           {'✅' if yandex_ok else '❌'}")
    
    if all([internet_ok, dns_ok, telegram_ok, yandex_ok]):
        print("\n✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ - БОТ ДОЛЖЕН РАБОТАТЬ")
    else:
        print("\n❌ ОБНАРУЖЕНЫ ПРОБЛЕМЫ - СМОТРИТЕ ОШИБКИ ВЫШЕ")
        print("\nВозможные решения:")
        if not internet_ok:
            print("  • Проверьте подключение к интернету")
            print("  • Перезагрузите маршрутизатор")
        if not dns_ok:
            print("  • Проверьте настройки DNS")
            print("  • Попробуйте DNS 8.8.8.8 или 1.1.1.1")
        if not telegram_ok or not yandex_ok:
            print("  • Проверьте брандмауэр/антивирус")
            print("  • Если используете VPN, попробуйте его отключить")
            print("  • Может быть блокировка со стороны провайдера")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
