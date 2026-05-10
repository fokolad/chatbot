import os
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher
from aiogram.types import Update, Message
from openai import AsyncOpenAI

app = FastAPI()
bot = Bot(token=os.getenv("8539004302:AAHUSJZIKFXQbw5o06pKJOcdt-K_ChVJoPo"))
dp = Dispatcher()

client = AsyncOpenAI(
    api_key=os.getenv("hcmJpcKUgeRjBstIwJ3WHTcAlIwvSDEe"),
    base_url="https://api.mistral.ai/v1"
)

@dp.message()
async def handle(message: Message):
    try:
        res = await client.chat.completions.create(
            model="mistral-small-latest",
            messages=[{"role": "user", "content": message.text}],
            max_tokens=512,
            temperature=0.7
        )
        await message.answer(res.choices[0].message.content)
    except Exception as e:
        await message.answer(f"⚠️ {str(e)[:200]}")

@app.post("/webhook")
async def webhook(req: Request):
    update = Update.model_validate(await req.json())
    await dp.feed_webhook_update(bot, update)
    return Response(status_code=200)

@app.get("/")
async def health():
    return {"status": "ok", "model": "mistral-small-latest"}
