import os
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message
from aiogram.filters import Command
from openai import AsyncOpenAI

app = FastAPI()

# ─── CONFIG ───────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("8539004302:AAHUSJZIKFXQbw5o06pKJOcdt-K_ChVJoPo")
MISTRAL_API_KEY = os.getenv("ag_019e13347601769aa641ac339b87fc1a")
MODEL_NAME = os.getenv("MISTRAL_MODEL", "mistral-medium-latest")
MAX_HISTORY = 10  # Пар сообщений (user + assistant)

if not TELEGRAM_TOKEN or not MISTRAL_API_KEY:
    raise ValueError("❌ Missing TELEGRAM_TOKEN or MISTRAL_API_KEY in environment variables.")

bot = Bot(token=TELEGRAM_TOKEN, parse_mode="HTML")
dp = Dispatcher()

client = AsyncOpenAI(
    api_key=MISTRAL_API_KEY,
    base_url="https://api.mistral.ai/v1"
)

# ⚠️ In-memory storage. Сбрасывается при деплое/холодном старте.
# Для продакшена замените на @vercel/kv, Redis или PostgreSQL.
conversations: dict[int, list[dict]] = {}

# ─── HANDLERS ─────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: Message):
    conversations[message.from_user.id] = []
    await message.answer(
        "🤖 <b>Привет!</b> Я бот на базе Mistral AI.\n"
        "Задавай вопросы, проси написать код или просто поболтаем."
    )

@dp.message()
async def handle_message(message: Message):
    uid = message.from_user.id
    if uid not in conversations:
        conversations[uid] = []

    conversations[uid].append({"role": "user", "content": message.text})

    # Обрезаем историю, чтобы не превышать лимиты контекста
    if len(conversations[uid]) > MAX_HISTORY * 2:
        conversations[uid] = conversations[uid][-MAX_HISTORY * 2:]

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=conversations[uid],
            max_tokens=1024,
            temperature=0.7,
            top_p=1.0
        )
        reply = response.choices[0].message.content or ""
        conversations[uid].append({"role": "assistant", "content": reply})

        await send_long_message(message, reply)

    except Exception as e:
        await message.answer(f"⚠️ Ошибка: <code>{str(e)}</code>")

# ─── UTILS ────────────────────────────────────────────────────────
async def send_long_message(message: Message, text: str):
    """Разбивает ответ на части, если он превышает лимит Telegram (4096 символов)"""
    CHUNK_SIZE = 4000
    for i in range(0, len(text), CHUNK_SIZE):
        chunk = text[i:i + CHUNK_SIZE]
        if i == 0:
            await message.answer(chunk)
        else:
            await message.answer(chunk)

# ─── WEBHOOK ENDPOINT ─────────────────────────────────────────────
@app.post("/webhook")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_webhook_update(bot, update)
    except Exception as e:
        print(f"[Webhook Error] {e}")
    # Всегда 200, чтобы Telegram не спамил повторными запросами
    return Response(status_code=200)

@app.get("/health")
async def health_check():
    return {"status": "ok", "model": MODEL_NAME}
