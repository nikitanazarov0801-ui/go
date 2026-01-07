import telebot
import requests
import json
import schedule
import time
import threading
import random
import logging
import os
import hashlib

# Отключаем лишний лог
logging.getLogger('telebot').setLevel(logging.ERROR)

BOT_TOKEN = "8223036887:AAEt08TRYU6uukh9Bwdwbc8p0JPsi1qvvwE"
CHANNEL_ID = "@pro_kosmos_knl"
YANDEX_FOLDER_ID = "b1gabf87ldtnplsa4ir2"
YANDEX_API_KEY = "AQVN0hs_MIMpkRvMgyzwb7iwRQpc4NUk-5pC855S"

bot = telebot.TeleBot(BOT_TOKEN)

topics = [
    "Роскосмос и космические запуски",
    "чёрные дыры и звёзды",
    "планеты Солнечной системы",
    "Марс и колонизация",
    "телескопы и открытия",
    "SpaceX и Илон Маск",
    "космический туризм 2026",
    "James Webb открытия",
    "квазары и пульсары",
    "экзопланеты и жизнь",
    "Artemis и Луна",
    "Europa Clipper Юпитер",
    "Dragonfly Титан",
    "китайская космическая станция",
    "Индийский Chandrayaan",
    "кротовые норы",
    "тёмная материя",
    "парадоксы времени",
    "межзвёздные перелёты",
    "цивилизации космоса",
    "Starship испытания",
    "космические лифты",
    "сверхтяжёлые ракеты",
    "космическая энергетика",
    "астрономия 2026"
]

SENT_HASHES_FILE = "sent_hashes.json"
SENT_HASHES_MAX = 300

_sent_hashes_list = []
_sent_hashes_set = set()

def _load_sent_hashes():
    global _sent_hashes_list, _sent_hashes_set
    if not os.path.exists(SENT_HASHES_FILE):
        _sent_hashes_list = []
        _sent_hashes_set = set()
        return
    try:
        with open(SENT_HASHES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = []
        _sent_hashes_list = data[-SENT_HASHES_MAX:]
        _sent_hashes_set = set(_sent_hashes_list)
    except Exception:
        _sent_hashes_list = []
        _sent_hashes_set = set()

def _save_sent_hashes():
    try:
        with open(SENT_HASHES_FILE, "w", encoding="utf-8") as f:
            json.dump(_sent_hashes_list, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def _remember_hash(text: str) -> bool:
    """
    Возвращает True, если это новый пост (и хэш сохранён).
    Возвращает False, если дубль.
    """
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if h in _sent_hashes_set:
        return False

    _sent_hashes_list.append(h)
    _sent_hashes_set.add(h)

    if len(_sent_hashes_list) > SENT_HASHES_MAX:
        old = _sent_hashes_list.pop(0)
        _sent_hashes_set.discard(old)

    _save_sent_hashes()
    return True

def _generate_fact_text(topic: str) -> str | None:
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "x-folder-id": YANDEX_FOLDER_ID,
        "Content-Type": "application/json"
    }
    payload = {
        "modelUri": f"gpt://{YANDEX_FOLDER_ID}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.7,
            "maxTokens": "800"
        },
        "messages": [
            {
                "role": "user",
                "text": (
                    f"Сгенерируй 4 коротких, интересных и точных факта о '{topic}' на русском языке. "
                    "Добавь эмодзи. Формат:\n"
                    "🌌 1. Факт\n🌌 2. Факт\n🌌 3. Факт\n🌌 4. Факт\n\n"
                    "Делай факты увлекательными для Telegram-канала."
                )
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    if response.status_code != 200:
        print(f"❌ YandexGPT ошибка: {response.status_code} - {response.text[:200]}")
        return None

    return response.json()['result']['alternatives'][0]['message']['text']

def post_space_fact():
    # Несколько попыток, чтобы не отправить дубль
    for attempt in range(1, 5):
        topic = random.choice(topics)
        try:
            result = _generate_fact_text(topic)
            if not result:
                continue

            message = "🚀 Всё о космосе 🌌\n\n" + result.strip() + "\n\nПодписывайся! @pro_kosmos_knl"

            if not _remember_hash(message):
                print(f"⚠️ Дубль (попытка {attempt}/4), генерируем заново...")
                continue

            bot.send_message(CHANNEL_ID, message)
            print(f"✅ Пост отправлен: {topic}")
            return

        except Exception as e:
            print(f"❌ Ошибка постинга: {e}")

    print("❌ Не удалось отправить уникальный пост (все попытки оказались дублями/ошибками).")

# Инициализация антидублей
_load_sent_hashes()

# Расписание: каждые 2 часа с 09:00 до 21:00 по МСК
# Важно: требуется `pip install pytz`, т.к. используем timezone в .at()
for hour in range(9, 22, 2):  # 9,11,13,15,17,19,21
    schedule.every().day.at(f"{hour:02d}:00", "Europe/Moscow").do(post_space_fact)

@bot.message_handler(commands=['post'])
def test_post(message):
    post_space_fact()
    bot.reply_to(message, f"✅ Тестовый пост отправлен в канал {CHANNEL_ID}")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(30)

def run_bot():
    while True:
        try:
            print("Запуск polling...")
            bot.infinity_polling(none_stop=True, timeout=20, long_polling_timeout=15, logger_level=logging.ERROR)
        except Exception as e:
            print(f"❌ Polling упал: {e}. Рестарт через 5 сек...")
            time.sleep(5)

if __name__ == "__main__":
    print("Бот стартует! Напишите /post боту для теста.")
    threading.Thread(target=run_scheduler, daemon=True).start()
    run_bot()
