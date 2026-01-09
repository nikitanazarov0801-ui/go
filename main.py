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
import base64
from io import BytesIO

# Отключаем лишний лог
logging.getLogger('telebot').setLevel(logging.ERROR)

# =======================
# РЕКОМЕНДУЕТСЯ: хранить в переменных окружения, а не в коде
# Windows CMD:
# set BOT_TOKEN=...
# set CHANNEL_ID=@...
# set YANDEX_FOLDER_ID=...
# set YANDEX_API_KEY=...
# =======================
BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_TELEGRAM_BOT_TOKEN_HERE")
CHANNEL_ID = os.getenv("CHANNEL_ID", "@pro_kosmos_knl")
YANDEX_FOLDER_ID = os.getenv("YANDEX_FOLDER_ID", "PASTE_FOLDER_ID_HERE")
YANDEX_API_KEY = os.getenv("YANDEX_API_KEY", "PASTE_YANDEX_API_KEY_HERE")

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

CAPTION_LIMIT = 1024


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
    """True -> новый пост (хэш сохранён), False -> дубль."""
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
        "Content-Type": "application/json",
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

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
    except Exception as e:
        print(f"❌ YandexGPT сеть/таймаут: {e}")
        return None

    if response.status_code != 200:
        print(f"❌ YandexGPT ошибка: {response.status_code} - {response.text[:200]}")
        return None

    try:
        return response.json()["result"]["alternatives"][0]["message"]["text"]
    except Exception:
        print("❌ YandexGPT: неожиданный формат ответа")
        return None


def _make_image_prompt_from_post(post_text: str, topic: str) -> str:
    text = (post_text or "").replace("\n", " ").strip()
    if len(text) > 500:
        text = text[:500] + "..."

    return (
        f"Иллюстрация к посту Telegram про космос. Тема: {topic}. "
        f"Смысл поста: {text}. "
        "Реалистичная космическая сцена, детально, cinematic lighting, high detail, без текста на изображении."
    )


def _generate_image_bytes(prompt: str,
                          seed: int | None = None,
                          width_ratio: int = 16,
                          height_ratio: int = 9,
                          max_wait_sec: int = 120,
                          poll_interval_sec: int = 5) -> bytes | None:
    headers = {
        "Authorization": f"Api-Key {YANDEX_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "modelUri": f"art://{YANDEX_FOLDER_ID}/yandex-art/latest",
        "generationOptions": {
            "mimeType": "image/jpeg",
            "seed": str(seed or random.randint(1, 10**9)),
            "aspectRatio": {
                "widthRatio": str(width_ratio),
                "heightRatio": str(height_ratio),
            },
        },
        "messages": [{"text": prompt}],
    }

    try:
        r = requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/imageGenerationAsync",
            headers=headers,
            json=payload,
            timeout=30
        )
    except Exception as e:
        print(f"❌ YandexART сеть/таймаут: {e}")
        return None

    if r.status_code != 200:
        print(f"❌ YandexART старт ошибка: {r.status_code} - {r.text[:200]}")
        return None

    try:
        op_id = r.json().get("id")
    except Exception:
        op_id = None

    if not op_id:
        print("❌ YandexART: не вернулся id операции")
        return None

    deadline = time.time() + max_wait_sec
    while time.time() < deadline:
        try:
            rr = requests.get(
                f"https://llm.api.cloud.yandex.net:443/operations/{op_id}",
                headers=headers,
                timeout=30
            )
        except Exception:
            time.sleep(poll_interval_sec)
            continue

        if rr.status_code != 200:
            time.sleep(poll_interval_sec)
            continue

        try:
            data = rr.json()
        except Exception:
            time.sleep(poll_interval_sec)
            continue

        if data.get("done") is True:
            resp = data.get("response") or {}
            b64 = resp.get("image")
            if not b64:
                print(f"❌ YandexART: done без image. Ответ: {str(data)[:250]}")
                return None
            try:
                return base64.b64decode(b64)
            except Exception:
                print("❌ YandexART: не смогли декодировать base64")
                return None

        time.sleep(poll_interval_sec)

    print("⚠️ YandexART: не дождались генерации, отправим текст без картинки")
    return None


def _split_caption_and_text(full_text: str, limit: int = CAPTION_LIMIT) -> tuple[str, str]:
    full_text = (full_text or "").strip()
    if len(full_text) <= limit:
        return full_text, ""

    cut = full_text.rfind("\n", 0, limit)
    if cut < 200:
        cut = full_text.rfind(". ", 0, limit)
    if cut < 200:
        cut = limit

    caption = full_text[:cut].strip()
    rest = full_text[cut:].strip()
    return caption, rest


def _send_photo_with_long_text(chat_id: str, photo_bytes: bytes, full_text: str):
    caption, rest = _split_caption_and_text(full_text, CAPTION_LIMIT)

    bio = BytesIO(photo_bytes)
    bio.name = "space.jpg"

    msg = bot.send_photo(chat_id, photo=bio, caption=caption)

    if rest:
        bot.send_message(chat_id, rest, reply_to_message_id=msg.message_id)


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

            img_prompt = _make_image_prompt_from_post(message, topic)
            img_bytes = _generate_image_bytes(img_prompt)

            if img_bytes:
                _send_photo_with_long_text(CHANNEL_ID, img_bytes, message)
                print(f"✅ Пост (с картинкой) отправлен: {topic}")
            else:
                bot.send_message(CHANNEL_ID, message)
                print(f"✅ Пост (без картинки) отправлен: {topic}")

            return

        except Exception as e:
            print(f"❌ Ошибка постинга: {e}")

    print("❌ Не удалось отправить уникальный пост (все попытки оказались дублями/ошибками).")


# Инициализация антидублей
_load_sent_hashes()

# Расписание: каждые 2 часа с 09:00 до 21:00 по МСК
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
            bot.infinity_polling(
                none_stop=True,
                timeout=20,
                long_polling_timeout=15,
                logger_level=logging.ERROR
            )
        except Exception as e:
            print(f"❌ Polling упал: {e}. Рестарт через 5 сек...")
            time.sleep(5)


if __name__ == "__main__":
    print("Бот стартует! Напишите /post боту для теста.")
    threading.Thread(target=run_scheduler, daemon=True).start()
    run_bot()
