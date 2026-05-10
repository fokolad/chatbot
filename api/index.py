import os
import logging
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message
from aiogram.filters import Command
from mistralai.client import Mistral  # 🔑 новый импорт

# Логирование
logger = logging.getLogger("telegram-bot")
logger.setLevel(logging.INFO)

app = FastAPI()

# ─── CONFIG ───────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.getenv("8539004302:AAHUSJZIKFXQbw5o06pKJOcdt-K_ChVJoPo")
MISTRAL_API_KEY = os.getenv("hcmJpcKUgeRjBstIwJ3WHTcAlIwvSDEe")
AGENT_ID = os.getenv("MISTRAL_AGENT_ID", "ag_019e13347601769aa641ac339b87fc1a")

if not TELEGRAM_TOKEN or not MISTRAL_API_KEY:
    raise RuntimeError("❌ Missing env vars")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# 🔑 Клиент Mistral (официальный SDK)
client = Mistral(api_key=MISTRAL_API_KEY)

# ─── HANDLERS ─────────────────────────────────────────────────────
@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("🤖 Бот запущен с агентом Mistral. Задавайте вопросы!")

@dp.message()
async def handle_message(message: Message):
    try:
        # 🔑 Вызов Conversations API с агентом
        response = client.beta.conversations.start(
            agent_id=AGENT_ID,
            agent_version=0,  # или укажите конкретную версию
            inputs=[{"role": "user", "content": message.text}]
        )
        
        # Извлечение ответа (структура зависит от версии API)
        reply = response.outputs[0].message.content if response.outputs else "❓ Нет ответа"
        
        await message.answer(reply)
        logger.info(f"✅ Ответ отправлен: {len(reply)} символов")
        
    except Exception as e:
        logger.error(f"🔴 Mistral error: {type(e).__name__}: {e}", exc_info=True)
        await message.answer(f"⚠️ Ошибка: {str(e)[:200]}")

# ─── WEBHOOK ──────────────────────────────────────────────────────
@app.post("/webhook")
async def telegram_webhook(request: Request):
    logger.info("📥 Webhook received")
    try:
        data = await request.json()
        update = Update.model_validate(data)
        await dp.feed_webhook_update(bot, update, allowed_updates=["message"])
    except Exception as e:
        logger.error(f"🔴 Webhook error: {e}", exc_info=True)
    return Response(status_code=200)

@app.get("/test")
async def health():
    return {
        "status": "ok",
        "agent_id": AGENT_ID[:10] + "...",
        "mistral_key_set": bool(MISTRAL_API_KEY)
    }
