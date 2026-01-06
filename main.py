import telebot
import requests
import json
import schedule
import time
import threading
import random
import logging

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
    
    # Новые темы 🚀
    "SpaceX и Илон Маск",
    "космический туризм 2026",
    "James Webb открытия",
    "квазары и пульсары",
    "экзопланеты и жизнь",
    
    # Миссии и проекты
    "Artemis и Луна",
    "Europa Clipper Юпитер",
    "Dragonfly Титан",
    "китайская космическая станция",
    "Индийский Chandrayaan",
    
    # Фантастика + наука
    "кротовые норы",
    "тёмная материя",
    "парадоксы времени",
    "межзвёздные перелёты",
    "цивилизации космоса",
    
    # Актуальные 2026
    "Starship испытания", 
    "космические лифты",
    "сверхтяжёлые ракеты",
    "космическая энергетика",
    "астрономия 2026"
]

def post_space_fact():
    topic = random.choice(topics)
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
                "text": f"Сгенерируй 4 коротких, интересных и точных факта о '{topic}' на русском языке. Добавь эмодзи. Формат:\n🌌 1. Факт\n🌌 2. Факт\n🌌 3. Факт\n🌌 4. Факт\n\nДелай факты увлекательными для Telegram-канала."
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        if response.status_code == 200:
            result = response.json()['result']['alternatives'][0]['message']['text']
            message = "🚀 Всё о космосе 🌌\n\n" + result + "\n\nПодписывайся! @pro_kosmos_knl"
            bot.send_message(CHANNEL_ID, message)
            print(f"✅ Пост отправлен: {topic}")
        else:
            print(f"❌ YandexGPT ошибка: {response.status_code} - {response.text[:200]}")
    except Exception as e:
        print(f"❌ Ошибка постинга: {e}")

# Расписание
schedule.every().day.at("06:00").do(post_space_fact)
schedule.every().day.at("07:00").do(post_space_fact)
schedule.every().day.at("08:00").do(post_space_fact)
schedule.every().day.at("09:00").do(post_space_fact)
schedule.every().day.at("10:00").do(post_space_fact)
schedule.every().day.at("11:00").do(post_space_fact)
schedule.every().day.at("12:00").do(post_space_fact)
schedule.every().day.at("13:00").do(post_space_fact)
schedule.every().day.at("14:00").do(post_space_fact)
schedule.every().day.at("15:00").do(post_space_fact)
schedule.every().day.at("16:00").do(post_space_fact)
schedule.every().day.at("17:00").do(post_space_fact)
schedule.every().day.at("18:00").do(post_space_fact)
schedule.every().day.at("19:00").do(post_space_fact)
schedule.every().day.at("20:00").do(post_space_fact)
schedule.every().day.at("21:00").do(post_space_fact)
schedule.every().day.at("22:00").do(post_space_fact)

@bot.message_handler(commands=['post'])
def test_post(message):
    post_space_fact()
    bot.reply_to(message, "✅ Тестовый пост отправлен в канал @mem_haos!")

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(60)

def run_bot():
    while True:
        try:
            print("🚀 Запуск polling...")
            bot.infinity_polling(none_stop=True, timeout=20, long_polling_timeout=15, logger_level=logging.ERROR)
        except Exception as e:
            print(f"❌ Polling упал: {e}. Рестарт через 5 сек...")
            time.sleep(5)

# Запуск в потоках
if __name__ == "__main__":
    print("🚀 Бот стартует! Напишите /post боту для теста.")
    threading.Thread(target=run_scheduler, daemon=True).start()
    run_bot()
